"""Walk-Forward Out-of-Sample (OOS) Evaluation Framework.

Design:
  1. Compute IS (in-sample) RCEE using only training window data.
  2. Run replay on OOS window using IS-derived edge states (frozen thresholds).
  3. Compute OOS IC independently from actual price returns.
  4. Compare IS vs OOS: IC, CAGR, Sharpe, profit factor.

No lookahead: OOS evaluation uses ONLY information available at end of IS window.

Split:
  Training (IS): 2022-01-01 → train_end
  Test (OOS):    train_end+1 → eval_end

Usage:
  engine = WalkForwardEngine(train_end=date(2023, 12, 31))
  result = engine.run(strategies=["breakout_v1", "reversal_v1"])
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.recommendation.regime_edge_engine import EdgeState, RCEEConfig
from app.replay.config.experiment_config import (
    CapitalConfig,
    ExecutionConfig,
    OutputConfig,
    PortfolioConfig,
    RecommendationConfig,
    ReplayExperimentConfig,
)
from app.replay.engine import ReplayEngine, ReplayResult
from app.replay.pitm_rcee import PointInTimeRCEECache, _DailyIC

logger = logging.getLogger(__name__)

_MIN_STOCKS = 100
_OOS_LAG_DAYS = 30


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class RegimeEdgeSnapshot:
    """IS-derived edge for a (strategy, regime) pair — frozen at train_end."""
    strategy_name: str
    regime_label: str
    is_avg_ic: float | None
    is_ic_lower_95: float | None
    is_hit_rate: float | None
    is_sample_days: int
    is_edge_state: EdgeState
    oos_avg_ic: float | None = None
    oos_ic_lower_95: float | None = None
    oos_hit_rate: float | None = None
    oos_sample_days: int = 0
    ic_decay_pct: float | None = None      # (oos_ic - is_ic) / abs(is_ic)
    edge_persists: bool | None = None      # OOS ic_lower_95 >= threshold


@dataclass
class WalkForwardResult:
    train_start: date
    train_end: date
    oos_start: date
    oos_end: date
    strategies: list[str]
    edge_snapshots: list[RegimeEdgeSnapshot]
    is_replay: ReplayResult
    oos_replay: ReplayResult

    def summary_table(self) -> str:
        lines = [
            "=" * 70,
            f"WALK-FORWARD OOS EVALUATION",
            f"IS:  {self.train_start} → {self.train_end}",
            f"OOS: {self.oos_start} → {self.oos_end}",
            "=" * 70,
            "",
            "── IC Persistence ──────────────────────────────────────────────",
            f"{'Strategy+Regime':<30} {'IS IC':>7} {'OOS IC':>7} {'Decay':>7} {'IS Edge':>12} {'Persists':>9}",
            "-" * 70,
        ]
        for snap in sorted(self.edge_snapshots, key=lambda s: (s.strategy_name, s.regime_label)):
            is_ic = f"{snap.is_avg_ic:.4f}" if snap.is_avg_ic is not None else "  n/a "
            oos_ic = f"{snap.oos_avg_ic:.4f}" if snap.oos_avg_ic is not None else "  n/a "
            decay = f"{snap.ic_decay_pct:+.1f}%" if snap.ic_decay_pct is not None else "  n/a "
            persists = "✅ YES" if snap.edge_persists else ("❌ NO " if snap.edge_persists is not None else "  n/a")
            lines.append(
                f"{snap.strategy_name}:{snap.regime_label:<20} {is_ic:>7} {oos_ic:>7} {decay:>7} "
                f"{snap.is_edge_state.value:>12} {persists:>9}"
            )

        is_m = self.is_replay.metrics
        oos_m = self.oos_replay.metrics
        lines += [
            "",
            "── Portfolio Performance ────────────────────────────────────────",
            f"{'Metric':<25} {'IN-SAMPLE':>12} {'OOS':>12} {'Delta':>10}",
            "-" * 60,
            f"{'CAGR':<25} {is_m.cagr_pct:>11.2f}% {oos_m.cagr_pct:>11.2f}% {oos_m.cagr_pct-is_m.cagr_pct:>+9.2f}%",
            f"{'Sharpe':<25} {(is_m.sharpe_ratio or 0):>12.2f} {(oos_m.sharpe_ratio or 0):>12.2f} {((oos_m.sharpe_ratio or 0)-(is_m.sharpe_ratio or 0)):>+10.2f}",
            f"{'Max Drawdown':<25} {is_m.max_drawdown_pct:>11.2f}% {oos_m.max_drawdown_pct:>11.2f}% {oos_m.max_drawdown_pct-is_m.max_drawdown_pct:>+9.2f}%",
            f"{'Profit Factor':<25} {is_m.profit_factor:>12.2f} {oos_m.profit_factor:>12.2f} {oos_m.profit_factor-is_m.profit_factor:>+10.2f}",
            f"{'Win Rate':<25} {is_m.win_rate_pct:>11.1f}% {oos_m.win_rate_pct:>11.1f}% {oos_m.win_rate_pct-is_m.win_rate_pct:>+9.1f}%",
            f"{'Total Trades':<25} {is_m.total_trades:>12d} {oos_m.total_trades:>12d} {oos_m.total_trades-is_m.total_trades:>+10d}",
            f"{'Total Return':<25} {is_m.total_return_pct:>11.2f}% {oos_m.total_return_pct:>11.2f}%",
            "",
            "── Verdict ──────────────────────────────────────────────────────",
        ]

        # Count edges that persisted
        measurable = [s for s in self.edge_snapshots if s.edge_persists is not None]
        persisted = [s for s in measurable if s.edge_persists]
        if measurable:
            pct = len(persisted) / len(measurable) * 100
            lines.append(f"  IC persistence: {len(persisted)}/{len(measurable)} strategy-regime pairs ({pct:.0f}%)")

        cagr_delta = oos_m.cagr_pct - is_m.cagr_pct
        if cagr_delta >= -3:
            verdict = "✅ EDGE PERSISTS — OOS performance within acceptable range of IS"
        elif cagr_delta >= -8:
            verdict = "⚠️  PARTIAL DECAY — Meaningful degradation but positive OOS edge"
        else:
            verdict = "❌ SIGNIFICANT DECAY — OOS performance materially below IS"
        lines.append(f"  Portfolio: {verdict}")
        lines.append("=" * 70)
        return "\n".join(lines)


# ── Frozen IS-RCEE cache ──────────────────────────────────────────────────────

class FrozenISRCEECache(PointInTimeRCEECache):
    """RCEE cache frozen at train_end — every OOS day uses IS-only IC evidence.

    Unlike PointInTimeRCEECache which grows as the replay advances day-by-day,
    this cache is fixed at the IS cutoff for all OOS replay days.
    This is the correct walk-forward methodology: thresholds set in-sample,
    applied unchanged to out-of-sample.
    """

    @classmethod
    def build_frozen(
        cls,
        db: Session,
        train_end: date,
        oos_trading_days: list[date],
        strategies: list[str],
        rcee_config: RCEEConfig | None = None,
    ) -> "FrozenISRCEECache":
        """Build RCEE using only IS data (as_of_date <= train_end - 30 days).
        Apply the same edge state to every OOS replay day.
        """
        if rcee_config is None:
            rcee_config = RCEEConfig()

        is_cutoff = train_end - timedelta(days=_OOS_LAG_DAYS)
        logger.info(
            "Building frozen IS-RCEE cache (data up to %s, applied to %d OOS days)",
            is_cutoff, len(oos_trading_days)
        )

        # Fetch only IS daily ICs
        is_daily_ics = cls._fetch_is_daily_ics(db, strategies, is_cutoff)
        logger.info("Fetched %d IS daily IC observations", len(is_daily_ics))

        cache = cls(is_daily_ics, rcee_config)

        # Build cache: every OOS day gets the SAME edge state
        # (frozen at train_end — no additional data leaks in)
        by_sr: dict[tuple[str, str], list[_DailyIC]] = {}
        for dic in is_daily_ics:
            key = (dic.strategy_name, dic.regime_label)
            by_sr.setdefault(key, []).append(dic)

        for oos_day in oos_trading_days:
            for (strategy, regime), ics in by_sr.items():
                # All ICs already filtered to IS cutoff — use all of them
                fit = cache._aggregate(strategy, regime, ics, oos_day)
                cache._cache[(oos_day, strategy, regime)] = fit

        logger.info("Frozen IS-RCEE cache ready: %d entries", len(cache._cache))
        return cache

    @staticmethod
    def _fetch_is_daily_ics(
        db: Session, strategies: list[str], is_cutoff: date
    ) -> list[_DailyIC]:
        """Fetch daily ICs using only IS data (as_of_date <= is_cutoff)."""
        sql = text("""
            WITH fwd AS (
                SELECT
                    rr.id AS run_id, rr.as_of_date, rr.strategy_name, rr.regime_label,
                    res.score AS composite_score,
                    CASE WHEN md_entry.close > 0
                         THEN (md_exit.close - md_entry.close) / md_entry.close
                         ELSE NULL END AS fwd_return
                FROM ranking_runs rr
                JOIN ranking_results res ON res.ranking_run_id = rr.id
                JOIN (
                    SELECT DISTINCT ON (strategy_name, as_of_date)
                        id, strategy_name, as_of_date
                    FROM ranking_runs
                    WHERE strategy_name = ANY(:strategies)
                      AND status = 'completed'
                      AND regime_label IS NOT NULL
                      AND as_of_date <= :is_cutoff
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
            )
            SELECT
                run_id::text, as_of_date, strategy_name, regime_label,
                CORR(composite_score::float, fwd_return::float) AS ic
            FROM fwd
            WHERE fwd_return IS NOT NULL
            GROUP BY run_id, as_of_date, strategy_name, regime_label
            HAVING COUNT(*) >= :min_stocks
               AND CORR(composite_score::float, fwd_return::float) IS NOT NULL
            ORDER BY as_of_date
        """)
        rows = db.execute(sql, {
            "strategies": strategies,
            "is_cutoff": is_cutoff,
            "min_stocks": _MIN_STOCKS,
        }).fetchall()
        return [
            _DailyIC(
                run_id=str(r.run_id),
                as_of_date=r.as_of_date,
                strategy_name=r.strategy_name,
                regime_label=r.regime_label,
                ic=float(r.ic),
                ic_positive=float(r.ic) > 0,
            )
            for r in rows
        ]


# ── OOS IC measurement ────────────────────────────────────────────────────────

def _compute_oos_ic(
    db: Session,
    strategies: list[str],
    oos_start: date,
    oos_end: date,
    rcee_config: RCEEConfig,
) -> dict[tuple[str, str], dict]:
    """Compute actual OOS IC for each (strategy, regime) pair.
    Uses only OOS data (as_of_date in [oos_start, oos_end]).
    Forward window must be fully closed (as_of_date <= today - 30d).
    """
    oos_cutoff = min(oos_end, date.today() - timedelta(days=_OOS_LAG_DAYS))

    sql = text("""
        WITH fwd AS (
            SELECT rr.id AS run_id, rr.as_of_date, rr.strategy_name, rr.regime_label,
                res.score, rr.as_of_date AS trade_date,
                CASE WHEN md_entry.close > 0
                     THEN (md_exit.close - md_entry.close) / md_entry.close
                     ELSE NULL END AS fwd_return
            FROM ranking_runs rr
            JOIN ranking_results res ON res.ranking_run_id = rr.id
            JOIN (
                SELECT DISTINCT ON (strategy_name, as_of_date)
                    id, strategy_name, as_of_date
                FROM ranking_runs
                WHERE strategy_name = ANY(:strategies)
                  AND status = 'completed'
                  AND regime_label IS NOT NULL
                  AND as_of_date BETWEEN :oos_start AND :oos_cutoff
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
        ),
        daily AS (
            SELECT as_of_date, strategy_name, regime_label,
                CORR(score::float, fwd_return::float) AS ic
            FROM fwd WHERE fwd_return IS NOT NULL
            GROUP BY as_of_date, strategy_name, regime_label
            HAVING COUNT(*) >= :min_stocks
               AND CORR(score::float, fwd_return::float) IS NOT NULL
        )
        SELECT strategy_name, regime_label,
            COUNT(*) AS n,
            AVG(ic) AS avg_ic,
            STDDEV(ic) AS std_ic,
            AVG(CASE WHEN ic > 0 THEN 1.0 ELSE 0.0 END) AS hit_rate
        FROM daily
        GROUP BY strategy_name, regime_label
    """)
    rows = db.execute(sql, {
        "strategies": strategies,
        "oos_start": oos_start,
        "oos_cutoff": oos_cutoff,
        "min_stocks": _MIN_STOCKS,
    }).fetchall()

    result = {}
    for r in rows:
        n = int(r.n)
        avg_ic = float(r.avg_ic) if r.avg_ic is not None else None
        std_ic = float(r.std_ic) if r.std_ic is not None else 0.0
        ic_lower_95 = (avg_ic - 1.645 * std_ic / math.sqrt(n)) if (avg_ic is not None and n > 1) else None
        result[(r.strategy_name, r.regime_label)] = {
            "avg_ic": avg_ic,
            "ic_lower_95": ic_lower_95,
            "hit_rate": float(r.hit_rate) if r.hit_rate else None,
            "sample_days": n,
        }
    return result


# ── Main engine ───────────────────────────────────────────────────────────────

class WalkForwardEngine:
    """Runs a full walk-forward OOS evaluation.

    1. Builds frozen IS-RCEE from [train_start, train_end] data.
    2. Runs IS replay (same period, normal PIT-RCEE for fair comparison).
    3. Runs OOS replay (oos_start → oos_end, frozen IS-RCEE applied).
    4. Computes OOS IC independently.
    5. Produces comparison report.
    """

    def __init__(
        self,
        train_start: date,
        train_end: date,
        oos_start: date,
        oos_end: date,
        strategies: list[str],
        initial_cash: float = 1_000_000,
        rcee_config: RCEEConfig | None = None,
        verbose: bool = False,
    ) -> None:
        self.train_start = train_start
        self.train_end = train_end
        self.oos_start = oos_start
        self.oos_end = oos_end
        self.strategies = strategies
        self.initial_cash = initial_cash
        self.rcee_config = rcee_config or RCEEConfig()
        self.verbose = verbose

    def run(self) -> WalkForwardResult:
        from app.db.session import get_session_factory
        SessionFactory = get_session_factory()

        # ── Step 1: IS replay with normal PIT-RCEE ────────────────────────
        logger.info("Running IS replay: %s → %s", self.train_start, self.train_end)
        is_config = self._make_config(
            experiment_id="WF_IS",
            name="Walk-Forward IN-SAMPLE",
            start=self.train_start,
            end=self.train_end,
        )
        is_replay = ReplayEngine(verbose=self.verbose).run(is_config)

        # ── Step 2: OOS replay with frozen IS-RCEE ───────────────────────
        logger.info("Running OOS replay: %s → %s", self.oos_start, self.oos_end)

        # Patch the engine to use frozen IS-RCEE for OOS
        oos_result = self._run_oos_replay()

        # ── Step 3: OOS IC measurement ────────────────────────────────────
        logger.info("Computing OOS IC...")
        with SessionFactory() as db:
            oos_ic_data = _compute_oos_ic(
                db, self.strategies, self.oos_start, self.oos_end, self.rcee_config
            )
            is_ic_data = _compute_oos_ic(
                db, self.strategies, self.train_start, self.train_end, self.rcee_config
            )

        # ── Step 4: Build edge snapshots ──────────────────────────────────
        edge_snapshots = self._build_snapshots(is_ic_data, oos_ic_data)

        result = WalkForwardResult(
            train_start=self.train_start,
            train_end=self.train_end,
            oos_start=self.oos_start,
            oos_end=self.oos_end,
            strategies=self.strategies,
            edge_snapshots=edge_snapshots,
            is_replay=is_replay,
            oos_replay=oos_result,
        )

        # Print summary
        print(result.summary_table())
        return result

    def _run_oos_replay(self) -> ReplayResult:
        """Run OOS replay with frozen IS-RCEE injected."""
        from app.db.session import get_session_factory
        from app.replay.day_processor import ReplayDayProcessor
        from app.replay.metrics_collector import ReplayMetricsCollector
        from app.replay.portfolio_manager import ReplayPortfolioManager
        from app.replay.report_generator import ReplayReportGenerator

        oos_config = self._make_config(
            experiment_id="WF_OOS",
            name="Walk-Forward OOS",
            start=self.oos_start,
            end=self.oos_end,
        )

        SessionFactory = get_session_factory()
        portfolio = ReplayPortfolioManager(oos_config)
        collector = ReplayMetricsCollector()
        processor = ReplayDayProcessor()
        days_processed = 0

        with SessionFactory() as db:
            # Resolve OOS trading days
            from sqlalchemy import text as sqlt
            rows = db.execute(sqlt("""
                SELECT DISTINCT as_of_date FROM ranking_runs
                WHERE as_of_date BETWEEN :s AND :e
                  AND strategy_name = ANY(:strats)
                  AND status = 'completed'
                ORDER BY as_of_date
            """), {"s": self.oos_start, "e": self.oos_end,
                   "strats": self.strategies}).fetchall()
            oos_days = [r.as_of_date for r in rows]

            logger.info("OOS trading days: %d", len(oos_days))

            # Build frozen IS-RCEE — the key step
            frozen_cache = FrozenISRCEECache.build_frozen(
                db=db,
                train_end=self.train_end,
                oos_trading_days=oos_days,
                strategies=self.strategies,
                rcee_config=self.rcee_config,
            )

            for i, day in enumerate(oos_days):
                context = ReplayDayProcessor.resolve_context(
                    db=db,
                    as_of_date=day,
                    strategies=oos_config.strategies,
                    trading_day_index=i,
                    prev_month_first_day=None,
                )
                if context is None:
                    continue

                entries, exits = processor.process_day(
                    context=context,
                    db=db,
                    config=oos_config,
                    portfolio=portfolio,
                    pitm_cache=frozen_cache,   # frozen IS cache
                )

                snap = portfolio.snapshot(
                    as_of_date=day,
                    regime_label=context.regime_label,
                    buys_today=len(entries),
                    exits_today=len(exits),
                    sip_today=0.0,
                )
                collector.record_day(snap)
                days_processed += 1

                if self.verbose or (i % 100 == 0):
                    logger.info(
                        "OOS [%d/%d] %s | NAV=%.0f | pos=%d | buys=%d | regime=%s",
                        i + 1, len(oos_days), day, snap.nav,
                        snap.active_positions, len(entries), context.regime_label,
                    )

        collector.all_trades = portfolio.all_trades
        metrics = collector.compute_final_metrics(self.oos_start, self.oos_end)

        logger.info(
            "OOS replay complete: CAGR=%.2f%% | Sharpe=%.2f | MaxDD=%.2f%%",
            metrics.cagr_pct, metrics.sharpe_ratio or 0, metrics.max_drawdown_pct,
        )

        # Write OOS report
        try:
            ReplayReportGenerator(oos_config).generate(collector, metrics)
        except Exception:
            pass

        from app.replay.engine import ReplayResult
        return ReplayResult(
            config=oos_config,
            metrics=metrics,
            snapshots=collector.snapshots,
            all_trades=portfolio.all_trades,
            days_processed=days_processed,
        )

    def _build_snapshots(
        self,
        is_data: dict,
        oos_data: dict,
    ) -> list[RegimeEdgeSnapshot]:
        snapshots = []
        all_keys = set(is_data.keys()) | set(oos_data.keys())

        for (strategy, regime) in sorted(all_keys):
            is_d = is_data.get((strategy, regime), {})
            oos_d = oos_data.get((strategy, regime), {})

            is_ic = is_d.get("avg_ic")
            is_lb = is_d.get("ic_lower_95")
            oos_ic = oos_d.get("avg_ic")
            oos_lb = oos_d.get("ic_lower_95")

            # IS edge state from IS data
            is_n = is_d.get("sample_days", 0)
            is_hr = is_d.get("hit_rate") or 0.0
            cfg = self.rcee_config
            if (is_lb is not None and is_lb >= cfg.edge_present_ic_lower_95
                    and is_hr >= cfg.edge_present_hit_rate
                    and is_n >= cfg.edge_present_sample_days):
                is_edge = EdgeState.EDGE_PRESENT
            elif (is_lb is not None and is_lb >= cfg.edge_weak_ic_lower_95
                    and is_hr >= cfg.edge_weak_hit_rate
                    and is_n >= cfg.edge_weak_sample_days):
                is_edge = EdgeState.EDGE_WEAK
            elif is_n > 0:
                is_edge = EdgeState.NO_EDGE
            else:
                is_edge = EdgeState.UNKNOWN

            # IC decay
            ic_decay = None
            if is_ic is not None and is_ic != 0 and oos_ic is not None:
                ic_decay = (oos_ic - is_ic) / abs(is_ic) * 100

            # Does edge persist OOS?
            edge_persists = None
            if is_edge == EdgeState.EDGE_PRESENT and oos_lb is not None:
                edge_persists = oos_lb >= cfg.edge_present_ic_lower_95
            elif is_edge == EdgeState.NO_EDGE and oos_lb is not None:
                edge_persists = oos_lb < cfg.edge_present_ic_lower_95

            snapshots.append(RegimeEdgeSnapshot(
                strategy_name=strategy,
                regime_label=regime,
                is_avg_ic=is_ic,
                is_ic_lower_95=is_lb,
                is_hit_rate=is_hr or None,
                is_sample_days=is_n,
                is_edge_state=is_edge,
                oos_avg_ic=oos_ic,
                oos_ic_lower_95=oos_lb,
                oos_hit_rate=oos_d.get("hit_rate"),
                oos_sample_days=oos_d.get("sample_days", 0),
                ic_decay_pct=ic_decay,
                edge_persists=edge_persists,
            ))
        return snapshots

    def _make_config(
        self, experiment_id: str, name: str, start: date, end: date
    ) -> ReplayExperimentConfig:
        return ReplayExperimentConfig(
            experiment_id=experiment_id,
            name=name,
            mode="AUTONOMOUS_RCEE",
            start_date=start,
            end_date=end,
            strategies=self.strategies,
            capital=CapitalConfig(
                initial_cash=self.initial_cash,
                monthly_contribution=0,
            ),
            execution=ExecutionConfig(),
            recommendations=RecommendationConfig(),
            portfolio=PortfolioConfig(max_positions=10, max_buy_slots=5),
            outputs=OutputConfig(output_dir="docs/experiments/results"),
        )
