"""Point-in-Time RCEE Cache — eliminates lookahead bias in strategy_regime_performance.

Problem:
  The static strategy_regime_performance table is computed with full 2022-2026 history.
  During replay, a day in 2022 would use IC evidence from 2022-2026 — future data.

Fix:
  For each trading day T, compute RCEE using only ranking runs where
  as_of_date <= T - 30 days (OOS cutoff). This guarantees point-in-time correctness.

Implementation:
  1. Fetch all daily IC values from DB in one query (ranking_results + market_data).
  2. Cache: dict[(strategy_name, regime_label, as_of_date)] → EdgeState
  3. For each replay day T, filter daily ICs to cutoff, aggregate, classify EdgeState.
  4. ReplayDayProcessor uses this cache instead of the static table.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.recommendation.regime_edge_engine import EdgeState, RCEEConfig

logger = logging.getLogger(__name__)

# OOS cutoff lag — same as production refresh_from_market_data
_OOS_LAG_DAYS = 30
# Minimum ranked stocks per day to include that day's IC
_MIN_STOCKS = 100


@dataclass(frozen=True)
class PointInTimeRegimeFit:
    """Lightweight RCEE result for replay — no full RegimeFit overhead."""
    strategy_name: str
    regime_label: str
    avg_ic: float | None
    ic_lower_95: float | None
    hit_rate: float | None
    sample_days: int
    edge_state: EdgeState
    computed_as_of: date  # the replay day this was computed for


@dataclass
class _DailyIC:
    """IC for a single ranking run day."""
    run_id: str
    as_of_date: date
    strategy_name: str
    regime_label: str
    ic: float          # CORR(composite_score, fwd_return_20d)
    ic_positive: bool  # IC > 0 for this day


class PointInTimeRCEECache:
    """Pre-computes point-in-time RCEE for all replay days in one pass.

    Usage:
        cache = PointInTimeRCEECache.build(db, trading_days, strategies, rcee_config)
        edge_state = cache.get_edge_state(as_of_date, strategy_name, regime_label)
    """

    def __init__(
        self,
        daily_ics: list[_DailyIC],
        config: RCEEConfig,
    ) -> None:
        self._daily_ics = daily_ics
        self._config = config
        # Cache: (replay_date, strategy, regime) → PointInTimeRegimeFit
        self._cache: dict[tuple[date, str, str], PointInTimeRegimeFit] = {}

    @classmethod
    def build(
        cls,
        db: Session,
        trading_days: list[date],
        strategies: list[str],
        start_date: date,
        end_date: date,
        rcee_config: RCEEConfig | None = None,
    ) -> "PointInTimeRCEECache":
        """Fetch all daily ICs from DB and build the cache."""
        if rcee_config is None:
            rcee_config = RCEEConfig()

        logger.info(
            "Building point-in-time RCEE cache for %d trading days...", len(trading_days)
        )

        # One SQL: compute IC per ranking run using market_data forward returns
        # Only include runs where forward price is available (as_of_date + 28 days)
        # No cutoff here — we fetch ALL historical ICs and apply cutoff per replay day
        daily_ics = cls._fetch_all_daily_ics(db, strategies, end_date)

        logger.info(
            "Fetched %d daily IC observations for PIT-RCEE cache", len(daily_ics)
        )

        cache = cls(daily_ics, rcee_config)
        cache._precompute_for_days(trading_days)

        logger.info("PIT-RCEE cache ready: %d entries", len(cache._cache))
        return cache

    def get_edge_state(
        self,
        as_of_date: date,
        strategy_name: str,
        regime_label: str,
    ) -> EdgeState:
        """Get point-in-time edge state for a replay day."""
        key = (as_of_date, strategy_name, regime_label)
        fit = self._cache.get(key)
        if fit is None:
            return EdgeState.UNKNOWN
        return fit.edge_state

    def get_fit(
        self,
        as_of_date: date,
        strategy_name: str,
        regime_label: str,
    ) -> PointInTimeRegimeFit | None:
        """Get full point-in-time fit for diagnostics."""
        return self._cache.get((as_of_date, strategy_name, regime_label))

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    @staticmethod
    def _fetch_all_daily_ics(
        db: Session,
        strategies: list[str],
        cutoff_ceiling: date,
    ) -> list[_DailyIC]:
        """Fetch per-run IC from ranking_results + market_data.

        Returns one row per ranking run where:
          - the run has ranking results with valid forward prices
          - forward return window = as_of_date + 28 calendar days
          - minimum _MIN_STOCKS stocks with valid returns per day

        Uses CORR(composite_score, fwd_return) as IC direction convention:
          positive IC = higher-scored stocks outperform (same as production).
        """
        sql = text("""
            WITH fwd AS (
                -- One row per (run, stock) with 20d forward return
                SELECT
                    rr.id           AS run_id,
                    rr.as_of_date,
                    rr.strategy_name,
                    rr.regime_label,
                    res.score       AS composite_score,
                    CASE WHEN md_entry.close > 0
                         THEN (md_exit.close - md_entry.close) / md_entry.close
                         ELSE NULL
                    END             AS fwd_return
                FROM ranking_runs rr
                JOIN ranking_results res ON res.ranking_run_id = rr.id
                -- Deduplicate to one run per (strategy, as_of_date) — pick highest ranked_stock_count
                JOIN (
                    SELECT DISTINCT ON (strategy_name, as_of_date)
                        id, strategy_name, as_of_date
                    FROM ranking_runs
                    WHERE strategy_name = ANY(:strategies)
                      AND status = 'completed'
                      AND regime_label IS NOT NULL
                    ORDER BY strategy_name, as_of_date,
                             ranked_stock_count DESC NULLS LAST, id DESC
                ) canon ON canon.id = rr.id
                LEFT JOIN LATERAL (
                    SELECT close FROM market_data
                    WHERE stock_id = res.stock_id AND date >= rr.as_of_date
                    ORDER BY date ASC LIMIT 1
                ) md_entry ON true
                LEFT JOIN LATERAL (
                    SELECT close FROM market_data
                    WHERE stock_id = res.stock_id
                      AND date >= rr.as_of_date + INTERVAL '28 days'
                    ORDER BY date ASC LIMIT 1
                ) md_exit ON true
                WHERE rr.as_of_date <= :cutoff_ceiling
            )
            SELECT
                run_id::text,
                as_of_date,
                strategy_name,
                regime_label,
                CORR(composite_score::float, fwd_return::float) AS ic
            FROM fwd
            WHERE fwd_return IS NOT NULL
            GROUP BY run_id, as_of_date, strategy_name, regime_label
            HAVING COUNT(*) >= :min_stocks
               AND CORR(composite_score::float, fwd_return::float) IS NOT NULL
            ORDER BY as_of_date
        """)

        rows = db.execute(
            sql,
            {
                "strategies": strategies,
                "cutoff_ceiling": cutoff_ceiling,
                "min_stocks": _MIN_STOCKS,
            },
        ).fetchall()

        return [
            _DailyIC(
                run_id=str(row.run_id),
                as_of_date=row.as_of_date,
                strategy_name=row.strategy_name,
                regime_label=row.regime_label,
                ic=float(row.ic),
                ic_positive=float(row.ic) > 0,
            )
            for row in rows
        ]

    def _precompute_for_days(self, trading_days: list[date]) -> None:
        """Build cache for every (replay_day, strategy, regime) combination.

        For each replay day T:
          cutoff = T - OOS_LAG_DAYS
          eligible_ics = [ic for ic in daily_ics if ic.as_of_date <= cutoff]
          aggregate by (strategy, regime) → RegimeFit → EdgeState
        """
        # Group daily ICs by (strategy, regime) sorted by date for fast slicing
        by_strategy_regime: dict[tuple[str, str], list[_DailyIC]] = defaultdict(list)
        for dic in sorted(self._daily_ics, key=lambda x: x.as_of_date):
            by_strategy_regime[(dic.strategy_name, dic.regime_label)].append(dic)

        for replay_day in trading_days:
            cutoff = replay_day - timedelta(days=_OOS_LAG_DAYS)

            for (strategy, regime), ics in by_strategy_regime.items():
                # Only use ICs where the ranking run's as_of_date <= cutoff
                eligible = [x for x in ics if x.as_of_date <= cutoff]
                fit = self._aggregate(strategy, regime, eligible, replay_day)
                self._cache[(replay_day, strategy, regime)] = fit

    def _aggregate(
        self,
        strategy_name: str,
        regime_label: str,
        ics: list[_DailyIC],
        as_of_date: date,
    ) -> PointInTimeRegimeFit:
        """Aggregate daily ICs into a PointInTimeRegimeFit with edge classification."""
        n = len(ics)

        if n == 0:
            return PointInTimeRegimeFit(
                strategy_name=strategy_name,
                regime_label=regime_label,
                avg_ic=None,
                ic_lower_95=None,
                hit_rate=None,
                sample_days=0,
                edge_state=EdgeState.UNKNOWN,
                computed_as_of=as_of_date,
            )

        ic_values = [x.ic for x in ics]
        avg_ic = sum(ic_values) / n
        variance = sum((v - avg_ic) ** 2 for v in ic_values) / max(n - 1, 1)
        std_ic = math.sqrt(variance) if variance > 0 else 0.0
        hit_rate = sum(1 for x in ics if x.ic_positive) / n

        # 95% CI lower bound: avg - 1.645 * std / sqrt(n)
        ic_lower_95 = avg_ic - 1.645 * std_ic / math.sqrt(n) if n > 1 else avg_ic - 0.1

        edge_state = self._classify(ic_lower_95, hit_rate, n)

        return PointInTimeRegimeFit(
            strategy_name=strategy_name,
            regime_label=regime_label,
            avg_ic=avg_ic,
            ic_lower_95=ic_lower_95,
            hit_rate=hit_rate,
            sample_days=n,
            edge_state=edge_state,
            computed_as_of=as_of_date,
        )

    def _classify(
        self, ic_lower_95: float, hit_rate: float, n: int
    ) -> EdgeState:
        """Apply RCEE threshold gates — mirrors production evaluate() logic."""
        cfg = self._config

        # EDGE_PRESENT: all three gates must pass
        gate_ic_p = ic_lower_95 >= cfg.edge_present_ic_lower_95
        gate_hr_p = hit_rate >= cfg.edge_present_hit_rate
        gate_n_p = n >= cfg.edge_present_sample_days
        if gate_ic_p and gate_hr_p and gate_n_p:
            return EdgeState.EDGE_PRESENT

        # EDGE_WEAK
        gate_ic_w = ic_lower_95 >= cfg.edge_weak_ic_lower_95
        gate_hr_w = hit_rate >= cfg.edge_weak_hit_rate
        gate_n_w = n >= cfg.edge_weak_sample_days
        if gate_ic_w and gate_hr_w and gate_n_w:
            return EdgeState.EDGE_WEAK

        return EdgeState.NO_EDGE
