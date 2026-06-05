from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.platform_traceability import (
    RegimeHistory,
    StrategyRegimePerformance,
    ValidationHorizonMetric,
)


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
            existing.recorded_at = datetime.now(UTC)
            self.db.flush()
            return existing
        row = RegimeHistory(
            as_of_date=as_of_date,
            benchmark_symbol=benchmark_symbol,
            trend_regime=trend_regime,
            vol_regime=vol_regime,
            regime_label=regime_label,
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

    def refresh_strategy_regime_performance(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        horizon: int,
    ) -> list[StrategyRegimePerformance]:
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
