from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.workspace_exit_research.models import AlphaDecayPointResult, PolicyMetricResult
from app.models.exit_research import ExitResearchAlphaDecayPoint, ExitResearchPolicyMetric


class ExitResearchMetricRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_policy_metric(
        self,
        research_run_id: UUID,
        result: PolicyMetricResult,
    ) -> None:
        existing = self.db.scalar(
            select(ExitResearchPolicyMetric).where(
                ExitResearchPolicyMetric.research_run_id == research_run_id,
                ExitResearchPolicyMetric.policy_family == result.policy_family,
                ExitResearchPolicyMetric.policy_variant == result.policy_variant,
                ExitResearchPolicyMetric.regime_label == result.regime_label,
                ExitResearchPolicyMetric.dataset_split == result.dataset_split,
                ExitResearchPolicyMetric.horizon == result.horizon,
            )
        )
        now = datetime.now(UTC)
        if existing is None:
            self.db.add(
                ExitResearchPolicyMetric(
                    research_run_id=research_run_id,
                    policy_family=result.policy_family,
                    policy_variant=result.policy_variant,
                    strategy_name=result.strategy_name,
                    strategy_version=result.strategy_version,
                    universe_code=result.universe_code,
                    regime_label=result.regime_label,
                    dataset_split=result.dataset_split,
                    horizon=result.horizon,
                    sample_size=result.sample_size,
                    mean_return=result.mean_return,
                    median_return=result.median_return,
                    std_dev=result.std_dev,
                    hit_rate=result.hit_rate,
                    avg_holding_days=result.avg_holding_days,
                    ci_lower=result.ci_lower,
                    ci_upper=result.ci_upper,
                    conclusion_status=result.conclusion_status,
                    holdout_start_date=result.holdout_start_date,
                    as_of_date_start=result.as_of_date_start,
                    as_of_date_end=result.as_of_date_end,
                    computed_at=now,
                )
            )
        else:
            existing.sample_size = result.sample_size
            existing.mean_return = result.mean_return
            existing.median_return = result.median_return
            existing.std_dev = result.std_dev
            existing.hit_rate = result.hit_rate
            existing.avg_holding_days = result.avg_holding_days
            existing.ci_lower = result.ci_lower
            existing.ci_upper = result.ci_upper
            existing.conclusion_status = result.conclusion_status
            existing.computed_at = now
        self.db.flush()

    def upsert_alpha_decay_point(
        self,
        research_run_id: UUID,
        *,
        strategy_name: str,
        strategy_version: str,
        universe_code: str,
        holdout_start_date,
        as_of_date_start,
        as_of_date_end,
        point: AlphaDecayPointResult,
    ) -> None:
        existing = self.db.scalar(
            select(ExitResearchAlphaDecayPoint).where(
                ExitResearchAlphaDecayPoint.research_run_id == research_run_id,
                ExitResearchAlphaDecayPoint.regime_label == point.regime_label,
                ExitResearchAlphaDecayPoint.dataset_split == point.dataset_split,
                ExitResearchAlphaDecayPoint.trading_day == point.trading_day,
            )
        )
        now = datetime.now(UTC)
        if existing is None:
            self.db.add(
                ExitResearchAlphaDecayPoint(
                    research_run_id=research_run_id,
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    universe_code=universe_code,
                    regime_label=point.regime_label,
                    dataset_split=point.dataset_split,
                    trading_day=point.trading_day,
                    sample_size=point.sample_size,
                    mean_return=point.mean_return,
                    cumulative_mean_return=point.cumulative_mean_return,
                    conclusion_status=point.conclusion_status,
                    holdout_start_date=holdout_start_date,
                    as_of_date_start=as_of_date_start,
                    as_of_date_end=as_of_date_end,
                    computed_at=now,
                )
            )
        else:
            existing.sample_size = point.sample_size
            existing.mean_return = point.mean_return
            existing.cumulative_mean_return = point.cumulative_mean_return
            existing.conclusion_status = point.conclusion_status
            existing.computed_at = now
        self.db.flush()

    def delete_for_run(self, research_run_id: UUID) -> None:
        self.db.execute(
            delete(ExitResearchPolicyMetric).where(
                ExitResearchPolicyMetric.research_run_id == research_run_id
            )
        )
        self.db.execute(
            delete(ExitResearchAlphaDecayPoint).where(
                ExitResearchAlphaDecayPoint.research_run_id == research_run_id
            )
        )

    def list_policy_metrics(
        self,
        *,
        strategy_name: str | None = None,
        universe_code: str | None = None,
        policy_family: str | None = None,
        regime_label: str | None = None,
        dataset_split: str | None = None,
        research_run_id: UUID | None = None,
        limit: int = 500,
    ) -> list[ExitResearchPolicyMetric]:
        stmt = select(ExitResearchPolicyMetric)
        if strategy_name:
            stmt = stmt.where(ExitResearchPolicyMetric.strategy_name == strategy_name)
        if universe_code:
            stmt = stmt.where(ExitResearchPolicyMetric.universe_code == universe_code)
        if policy_family:
            stmt = stmt.where(ExitResearchPolicyMetric.policy_family == policy_family)
        if regime_label:
            stmt = stmt.where(ExitResearchPolicyMetric.regime_label == regime_label)
        if dataset_split:
            stmt = stmt.where(ExitResearchPolicyMetric.dataset_split == dataset_split)
        if research_run_id:
            stmt = stmt.where(ExitResearchPolicyMetric.research_run_id == research_run_id)
        return list(self.db.scalars(stmt.limit(limit)).all())

    def list_policy_metrics_covering_as_of(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        universe_code: str,
        as_of_date,
        regime_labels: list[str] | None = None,
        limit: int = 100,
    ) -> list[ExitResearchPolicyMetric]:
        """Policy metrics from the latest exit-research window with as_of_date_end <= as_of_date."""
        from sqlalchemy import func

        latest_end = self.db.scalar(
            select(func.max(ExitResearchPolicyMetric.as_of_date_end)).where(
                ExitResearchPolicyMetric.strategy_name == strategy_name,
                ExitResearchPolicyMetric.strategy_version == strategy_version,
                ExitResearchPolicyMetric.universe_code == universe_code,
                ExitResearchPolicyMetric.as_of_date_end <= as_of_date,
            )
        )
        if latest_end is None:
            return []

        stmt = select(ExitResearchPolicyMetric).where(
            ExitResearchPolicyMetric.strategy_name == strategy_name,
            ExitResearchPolicyMetric.strategy_version == strategy_version,
            ExitResearchPolicyMetric.universe_code == universe_code,
            ExitResearchPolicyMetric.as_of_date_end == latest_end,
        )
        if regime_labels:
            stmt = stmt.where(ExitResearchPolicyMetric.regime_label.in_(regime_labels))
        return list(self.db.scalars(stmt.order_by(ExitResearchPolicyMetric.policy_family).limit(limit)).all())

    def list_alpha_decay(
        self,
        *,
        research_run_id: UUID | None = None,
        regime_label: str | None = None,
        dataset_split: str | None = None,
        universe_code: str | None = None,
    ) -> list[ExitResearchAlphaDecayPoint]:
        stmt = select(ExitResearchAlphaDecayPoint).order_by(ExitResearchAlphaDecayPoint.trading_day)
        if research_run_id:
            stmt = stmt.where(ExitResearchAlphaDecayPoint.research_run_id == research_run_id)
        if regime_label:
            stmt = stmt.where(ExitResearchAlphaDecayPoint.regime_label == regime_label)
        if dataset_split:
            stmt = stmt.where(ExitResearchAlphaDecayPoint.dataset_split == dataset_split)
        if universe_code:
            stmt = stmt.where(ExitResearchAlphaDecayPoint.universe_code == universe_code)
        return list(self.db.scalars(stmt).all())
