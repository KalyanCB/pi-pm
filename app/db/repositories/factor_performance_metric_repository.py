from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.factor_analytics.models import DailyFactorIC, FactorMetricResult
from app.models.factor_analytics import FactorDailyMetric, FactorPerformanceMetric


class FactorPerformanceMetricRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_daily(self, row: DailyFactorIC, *, strategy_name: str, strategy_version: str, universe_code: str) -> None:
        existing = self.db.scalar(
            select(FactorDailyMetric).where(
                FactorDailyMetric.factor_name == row.factor_name,
                FactorDailyMetric.strategy_name == strategy_name,
                FactorDailyMetric.strategy_version == strategy_version,
                FactorDailyMetric.universe_code == universe_code,
                FactorDailyMetric.regime_label == row.regime_label,
                FactorDailyMetric.horizon == row.horizon,
                FactorDailyMetric.ranking_run_id == row.ranking_run_id,
            )
        )
        now = datetime.now(UTC)
        if existing is None:
            self.db.add(
                FactorDailyMetric(
                    factor_name=row.factor_name,
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    universe_code=universe_code,
                    regime_label=row.regime_label,
                    horizon=row.horizon,
                    ranking_run_id=row.ranking_run_id,
                    as_of_date=row.as_of_date,
                    dataset_split=row.dataset_split,
                    ic_spearman=row.ic_spearman,
                    sample_size=row.sample_size,
                    created_at=now,
                )
            )
        else:
            existing.ic_spearman = row.ic_spearman
            existing.sample_size = row.sample_size
            existing.as_of_date = row.as_of_date
            existing.dataset_split = row.dataset_split
            existing.created_at = now
        self.db.flush()

    def upsert_metric(self, result: FactorMetricResult) -> FactorPerformanceMetric:
        existing = self.db.scalar(
            select(FactorPerformanceMetric).where(
                FactorPerformanceMetric.factor_name == result.factor_name,
                FactorPerformanceMetric.strategy_name == result.strategy_name,
                FactorPerformanceMetric.strategy_version == result.strategy_version,
                FactorPerformanceMetric.universe_code == result.universe_code,
                FactorPerformanceMetric.horizon == result.horizon,
                FactorPerformanceMetric.regime_label == result.regime_label,
                FactorPerformanceMetric.dataset_split == result.dataset_split,
                FactorPerformanceMetric.as_of_date_start == result.as_of_date_start,
                FactorPerformanceMetric.as_of_date_end == result.as_of_date_end,
                FactorPerformanceMetric.holdout_start_date == result.holdout_start_date,
            )
        )
        now = datetime.now(UTC)
        if existing is None:
            row = FactorPerformanceMetric(
                factor_name=result.factor_name,
                strategy_name=result.strategy_name,
                strategy_version=result.strategy_version,
                universe_code=result.universe_code,
                horizon=result.horizon,
                regime_label=result.regime_label,
                dataset_split=result.dataset_split,
                ic_spearman=result.ic_spearman,
                ic_pearson=result.ic_pearson,
                hit_rate=result.hit_rate,
                spread_contribution=result.spread_contribution,
                sample_size=result.sample_size,
                ranked_days=result.ranked_days,
                regime_coverage_pct=result.regime_coverage_pct,
                stability_score=result.stability_score,
                stability_label=result.stability_label,
                coverage_label=result.coverage_label,
                bootstrap_ci_lower=result.bootstrap_ci_lower,
                bootstrap_ci_upper=result.bootstrap_ci_upper,
                p_value=result.p_value,
                is_statistically_significant=result.is_statistically_significant,
                confidence=result.confidence,
                bootstrap_sample_count=result.bootstrap_sample_count,
                bootstrap_method=result.bootstrap_method,
                holdout_start_date=result.holdout_start_date,
                as_of_date_start=result.as_of_date_start,
                as_of_date_end=result.as_of_date_end,
                computed_at=now,
            )
            self.db.add(row)
            self.db.flush()
            return row

        existing.ic_spearman = result.ic_spearman
        existing.ic_pearson = result.ic_pearson
        existing.hit_rate = result.hit_rate
        existing.spread_contribution = result.spread_contribution
        existing.sample_size = result.sample_size
        existing.ranked_days = result.ranked_days
        existing.regime_coverage_pct = result.regime_coverage_pct
        existing.stability_score = result.stability_score
        existing.stability_label = result.stability_label
        existing.coverage_label = result.coverage_label
        existing.bootstrap_ci_lower = result.bootstrap_ci_lower
        existing.bootstrap_ci_upper = result.bootstrap_ci_upper
        existing.p_value = result.p_value
        existing.is_statistically_significant = result.is_statistically_significant
        existing.confidence = result.confidence
        existing.bootstrap_sample_count = result.bootstrap_sample_count
        existing.bootstrap_method = result.bootstrap_method
        existing.computed_at = now
        self.db.flush()
        return existing

    def delete_metrics_for_window(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        universe_code: str,
        as_of_date_start,
        as_of_date_end,
        holdout_start_date,
    ) -> None:
        self.db.execute(
            delete(FactorPerformanceMetric).where(
                FactorPerformanceMetric.strategy_name == strategy_name,
                FactorPerformanceMetric.strategy_version == strategy_version,
                FactorPerformanceMetric.universe_code == universe_code,
                FactorPerformanceMetric.as_of_date_start == as_of_date_start,
                FactorPerformanceMetric.as_of_date_end == as_of_date_end,
                FactorPerformanceMetric.holdout_start_date == holdout_start_date,
            )
        )

    def delete_daily_for_window(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        universe_code: str,
        start_date,
        end_date,
    ) -> None:
        self.db.execute(
            delete(FactorDailyMetric).where(
                FactorDailyMetric.strategy_name == strategy_name,
                FactorDailyMetric.strategy_version == strategy_version,
                FactorDailyMetric.universe_code == universe_code,
                FactorDailyMetric.as_of_date >= start_date,
                FactorDailyMetric.as_of_date <= end_date,
            )
        )

    def list_metrics(
        self,
        *,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
        universe_code: str | None = None,
        factor_name: str | None = None,
        regime_label: str | None = None,
        horizon: int | None = None,
        dataset_split: str | None = None,
        as_of_date_start=None,
        as_of_date_end=None,
        limit: int = 500,
    ) -> list[FactorPerformanceMetric]:
        stmt = select(FactorPerformanceMetric)
        if strategy_name:
            stmt = stmt.where(FactorPerformanceMetric.strategy_name == strategy_name)
        if strategy_version:
            stmt = stmt.where(FactorPerformanceMetric.strategy_version == strategy_version)
        if universe_code:
            stmt = stmt.where(FactorPerformanceMetric.universe_code == universe_code)
        if factor_name:
            stmt = stmt.where(FactorPerformanceMetric.factor_name == factor_name)
        if regime_label:
            stmt = stmt.where(FactorPerformanceMetric.regime_label == regime_label)
        if horizon is not None:
            stmt = stmt.where(FactorPerformanceMetric.horizon == horizon)
        if dataset_split:
            stmt = stmt.where(FactorPerformanceMetric.dataset_split == dataset_split)
        if as_of_date_start:
            stmt = stmt.where(FactorPerformanceMetric.as_of_date_start == as_of_date_start)
        if as_of_date_end:
            stmt = stmt.where(FactorPerformanceMetric.as_of_date_end == as_of_date_end)
        stmt = stmt.order_by(
            FactorPerformanceMetric.factor_name,
            FactorPerformanceMetric.horizon,
            FactorPerformanceMetric.regime_label,
        ).limit(limit)
        return list(self.db.scalars(stmt).all())
