from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.platform_traceability import (
    RegimeHistory,
    StrategyRegimePerformance,
    ValidationHorizonMetric,
)

# Minimum ranked stocks per day to include that day's IC in the aggregate
_MIN_RANKED_STOCKS_PER_DAY = 100
# OOS cutoff: only use ranking runs that were as_of_date <= today - 30 days
_OOS_CUTOFF_LAG_DAYS = 30
# Cost hurdle for expectancy_after_costs
_ROUND_TRIP_COST = 0.001


class RegimeAnalyticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_regime(
        self,
        *,
        as_of_date: date,
        benchmark_symbol: str,
        trend_regime: str,
        vol_regime: str,
        regime_label: str,
        market_regime_3way: str | None = None,
    ) -> RegimeHistory:
        existing = self.db.scalar(
            select(RegimeHistory).where(
                RegimeHistory.as_of_date == as_of_date,
                RegimeHistory.benchmark_symbol == benchmark_symbol,
            )
        )
        if existing is not None:
            existing.trend_regime = trend_regime
            existing.vol_regime = vol_regime
            existing.regime_label = regime_label
            existing.market_regime_3way = market_regime_3way
            existing.recorded_at = datetime.now(UTC)
            self.db.flush()
            return existing
        row = RegimeHistory(
            as_of_date=as_of_date,
            benchmark_symbol=benchmark_symbol,
            trend_regime=trend_regime,
            vol_regime=vol_regime,
            regime_label=regime_label,
            market_regime_3way=market_regime_3way,
            recorded_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def count_regime_history(
        self,
        *,
        benchmark_symbol: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(RegimeHistory)
        if benchmark_symbol:
            stmt = stmt.where(RegimeHistory.benchmark_symbol == benchmark_symbol)
        if start_date:
            stmt = stmt.where(RegimeHistory.as_of_date >= start_date)
        if end_date:
            stmt = stmt.where(RegimeHistory.as_of_date <= end_date)
        return int(self.db.scalar(stmt) or 0)

    def get_current(
        self,
        *,
        benchmark_symbol: str,
        as_of_date: date | None = None,
    ) -> RegimeHistory | None:
        stmt = select(RegimeHistory).where(RegimeHistory.benchmark_symbol == benchmark_symbol)
        if as_of_date is not None:
            stmt = stmt.where(RegimeHistory.as_of_date == as_of_date)
        else:
            stmt = stmt.order_by(RegimeHistory.as_of_date.desc())
        return self.db.scalar(stmt.limit(1))

    # ── Legacy method (reads from validation_horizon_metrics) ─────────────────
    # Kept for backward compat; daily_batch_service now calls refresh_from_market_data.

    def refresh_from_validation_metrics(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        horizon: int,
    ) -> list[StrategyRegimePerformance]:
        """Original implementation — reads from validation_horizon_metrics.

        WARNING: validation_horizon_metrics is currently empty (0 rows) because the
        20-day forward window never closes. Use refresh_from_market_data instead.
        Retained for backward compat with any callers that have not been updated.
        """
        rows = self.db.execute(
            select(
                ValidationHorizonMetric.regime_label,
                func.avg(ValidationHorizonMetric.rank_ic_spearman),
                func.avg(ValidationHorizonMetric.spread),
                func.count(ValidationHorizonMetric.id),
            )
            .where(
                ValidationHorizonMetric.strategy_name == strategy_name,
                ValidationHorizonMetric.strategy_version == strategy_version,
                ValidationHorizonMetric.horizon == horizon,
                ValidationHorizonMetric.regime_label.is_not(None),
            )
            .group_by(ValidationHorizonMetric.regime_label)
        ).all()
        saved: list[StrategyRegimePerformance] = []
        now = datetime.now(UTC)
        for regime_label, avg_ic, avg_spread, sample_count in rows:
            existing = self.db.scalar(
                select(StrategyRegimePerformance).where(
                    StrategyRegimePerformance.strategy_name == strategy_name,
                    StrategyRegimePerformance.strategy_version == strategy_version,
                    StrategyRegimePerformance.regime_label == regime_label,
                    StrategyRegimePerformance.horizon == horizon,
                )
            )
            if existing is None:
                existing = StrategyRegimePerformance(
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    regime_label=regime_label,
                    horizon=horizon,
                    sample_count=0,
                    last_updated=now,
                )
                self.db.add(existing)
            existing.avg_ic = float(avg_ic) if avg_ic is not None else None
            existing.avg_spread = float(avg_spread) if avg_spread is not None else None
            existing.sample_count = int(sample_count or 0)
            existing.last_updated = now
            saved.append(existing)
        self.db.flush()
        return saved

    # Keep old name as alias for any callers not yet updated
    def refresh_strategy_regime_performance(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        horizon: int,
    ) -> list[StrategyRegimePerformance]:
        """Alias for refresh_from_validation_metrics (backward compat)."""
        return self.refresh_from_validation_metrics(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            horizon=horizon,
        )

    # ── New method: direct IC computation from market_data + ranking_results ──

    def refresh_from_market_data(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        horizon: int = 20,
        cutoff_date: date | None = None,
    ) -> list[StrategyRegimePerformance]:
        """Compute OOS regime-conditional IC directly from ranking_results + market_data.

        Walk-forward OOS: only uses ranking runs where as_of_date <= cutoff_date
        (default: today - 30 days) to ensure no lookahead bias.

        Forward return: closing price 28+ calendar days after as_of_date
        (nearest available trading date >= as_of_date + 28 days).

        IC per day = Spearman correlation(rank, fwd_return) across all ranked stocks.
        Minimum _MIN_RANKED_STOCKS_PER_DAY stocks per day to include that day.

        Aggregates per (strategy, regime):
          avg_ic, stddev(ic), count(days), hit_rate (% days IC > 0),
          ic_lower_95 = avg_ic - 1.645 * std / sqrt(n),
          expectancy = avg(top-20 fwd returns per day),
          expectancy_after_costs = expectancy - _ROUND_TRIP_COST.

        Sets computed_from = 'market_data_direct'.
        """
        if cutoff_date is None:
            cutoff_date = date.today() - timedelta(days=_OOS_CUTOFF_LAG_DAYS)

        # Step 1: Compute per-day IC using raw SQL for performance.
        # One run per as_of_date (highest ranked_stock_count wins, ties broken by id).
        # IC = CORR(composite_score, fwd_return) — positive = good edge (standard convention).
        # composite_score is high for better-ranked stocks, so positive IC means top picks outperform.
        per_day_sql = text("""
            WITH one_run_per_day AS (
                -- Deduplicate to one run per (strategy, as_of_date) to avoid inflated sample counts.
                -- Prefer the run with the most ranked stocks; break ties by id DESC.
                SELECT DISTINCT ON (rr.as_of_date)
                    rr.id           AS run_id,
                    rr.as_of_date,
                    rr.regime_label
                FROM ranking_runs rr
                WHERE rr.strategy_name = :strategy_name
                  AND rr.strategy_version = :strategy_version
                  AND rr.status = 'completed'
                  AND rr.as_of_date <= :cutoff_date
                  AND rr.regime_label IS NOT NULL
                ORDER BY rr.as_of_date, rr.ranked_stock_count DESC NULLS LAST, rr.id DESC
            ),
            ranked AS (
                -- All ranking results for the selected runs
                SELECT
                    d.run_id,
                    d.as_of_date,
                    d.regime_label,
                    res.stock_id,
                    res.rank,
                    res.score       AS composite_score
                FROM one_run_per_day d
                JOIN ranking_results res ON res.ranking_run_id = d.run_id
            ),
            fwd_prices AS (
                -- Nearest available close price >= as_of_date + 28 calendar days
                SELECT
                    r.run_id,
                    r.stock_id,
                    r.rank,
                    r.composite_score,
                    r.as_of_date,
                    r.regime_label,
                    -- Entry price: close on or nearest after as_of_date
                    entry_md.close   AS entry_close,
                    -- Exit price: close on nearest date >= as_of_date + 28 days
                    (
                        SELECT md2.close
                        FROM market_data md2
                        WHERE md2.stock_id = r.stock_id
                          AND md2.date >= r.as_of_date + INTERVAL '28 days'
                        ORDER BY md2.date ASC
                        LIMIT 1
                    ) AS exit_close
                FROM ranked r
                JOIN market_data entry_md
                  ON entry_md.stock_id = r.stock_id
                 AND entry_md.date = (
                        SELECT MIN(md3.date)
                        FROM market_data md3
                        WHERE md3.stock_id = r.stock_id
                          AND md3.date >= r.as_of_date
                 )
            ),
            with_returns AS (
                SELECT
                    run_id,
                    stock_id,
                    rank,
                    composite_score,
                    as_of_date,
                    regime_label,
                    CASE
                        WHEN entry_close IS NOT NULL AND exit_close IS NOT NULL
                             AND entry_close > 0
                        THEN (exit_close - entry_close) / entry_close
                        ELSE NULL
                    END AS fwd_return
                FROM fwd_prices
            ),
            -- Only include days with enough ranked stocks that have valid returns
            day_counts AS (
                SELECT run_id, as_of_date, regime_label,
                       COUNT(*) FILTER (WHERE fwd_return IS NOT NULL) AS valid_count
                FROM with_returns
                GROUP BY run_id, as_of_date, regime_label
            ),
            valid_days AS (
                SELECT dc.run_id
                FROM day_counts dc
                WHERE dc.valid_count >= :min_stocks
            ),
            -- IC = CORR(composite_score, fwd_return) per day.
            -- composite_score is higher for better-ranked stocks, so positive IC = good edge.
            -- This matches the threshold convention: ic_lower_95 >= 0.010 means EDGE_PRESENT.
            daily_ic AS (
                SELECT
                    wr.run_id,
                    wr.as_of_date,
                    wr.regime_label,
                    CORR(wr.composite_score::float, wr.fwd_return::float) AS ic_spearman
                FROM with_returns wr
                JOIN valid_days vd ON vd.run_id = wr.run_id
                WHERE wr.fwd_return IS NOT NULL
                GROUP BY wr.run_id, wr.as_of_date, wr.regime_label
                HAVING COUNT(*) >= :min_stocks
            ),
            -- Top-20 per day for expectancy
            top20_returns AS (
                SELECT
                    wr.run_id,
                    AVG(wr.fwd_return) AS avg_top20_return
                FROM with_returns wr
                JOIN valid_days vd ON vd.run_id = wr.run_id
                WHERE wr.rank <= 20 AND wr.fwd_return IS NOT NULL
                GROUP BY wr.run_id
            )
            SELECT
                dic.regime_label,
                AVG(dic.ic_spearman)                                    AS avg_ic,
                STDDEV(dic.ic_spearman)                                 AS std_ic,
                COUNT(dic.run_id)                                       AS n_days,
                AVG(CASE WHEN dic.ic_spearman > 0 THEN 1.0 ELSE 0.0 END) AS hit_rate,
                AVG(t20.avg_top20_return)                               AS expectancy
            FROM daily_ic dic
            LEFT JOIN top20_returns t20 ON t20.run_id = dic.run_id
            GROUP BY dic.regime_label
            ORDER BY dic.regime_label
        """)

        result_rows = self.db.execute(
            per_day_sql,
            {
                "strategy_name": strategy_name,
                "strategy_version": strategy_version,
                "cutoff_date": cutoff_date,
                "min_stocks": _MIN_RANKED_STOCKS_PER_DAY,
            },
        ).all()

        saved: list[StrategyRegimePerformance] = []
        now = datetime.now(UTC)

        for row in result_rows:
            regime_label = row[0]
            avg_ic = float(row[1]) if row[1] is not None else None
            std_ic = float(row[2]) if row[2] is not None else None
            n_days = int(row[3]) if row[3] is not None else 0
            hit_rate_val = float(row[4]) if row[4] is not None else None
            expectancy_val = float(row[5]) if row[5] is not None else None

            # ic_lower_95 = avg_ic - 1.645 * std / sqrt(n)
            ic_lower_95 = None
            if avg_ic is not None and std_ic is not None and n_days > 1:
                ic_lower_95 = avg_ic - 1.645 * std_ic / math.sqrt(n_days)

            expectancy_after_costs = (
                expectancy_val - _ROUND_TRIP_COST if expectancy_val is not None else None
            )

            existing = self.db.scalar(
                select(StrategyRegimePerformance).where(
                    StrategyRegimePerformance.strategy_name == strategy_name,
                    StrategyRegimePerformance.strategy_version == strategy_version,
                    StrategyRegimePerformance.regime_label == regime_label,
                    StrategyRegimePerformance.horizon == horizon,
                )
            )
            if existing is None:
                existing = StrategyRegimePerformance(
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    regime_label=regime_label,
                    horizon=horizon,
                    sample_count=0,
                    last_updated=now,
                )
                self.db.add(existing)

            existing.avg_ic = avg_ic
            existing.sample_count = n_days
            existing.last_updated = now
            existing.ic_std = std_ic
            existing.ic_lower_95 = ic_lower_95
            existing.hit_rate = hit_rate_val
            existing.expectancy = expectancy_val
            existing.expectancy_after_costs = expectancy_after_costs
            existing.computed_from = "market_data_direct"
            saved.append(existing)

        self.db.flush()
        return saved

    def get_strategy_regime_performance(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        regime_label: str,
        horizon: int,
    ) -> StrategyRegimePerformance | None:
        return self.db.scalar(
            select(StrategyRegimePerformance).where(
                StrategyRegimePerformance.strategy_name == strategy_name,
                StrategyRegimePerformance.strategy_version == strategy_version,
                StrategyRegimePerformance.regime_label == regime_label,
                StrategyRegimePerformance.horizon == horizon,
            )
        )

    def list_strategy_regime_performance(
        self,
        *,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
        horizon: int | None = None,
    ) -> list[StrategyRegimePerformance]:
        stmt = select(StrategyRegimePerformance)
        if strategy_name:
            stmt = stmt.where(StrategyRegimePerformance.strategy_name == strategy_name)
        if strategy_version:
            stmt = stmt.where(StrategyRegimePerformance.strategy_version == strategy_version)
        if horizon is not None:
            stmt = stmt.where(StrategyRegimePerformance.horizon == horizon)
        return list(self.db.scalars(stmt.order_by(StrategyRegimePerformance.regime_label)).all())
