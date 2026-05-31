from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import RegimeBacktestRunStatus
from app.models.regime_policy import RegimeBacktestRun


class RegimeBacktestRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_running(
        self,
        *,
        experiment_run_id: UUID,
        policy_config_id: UUID,
        baseline_policy_config_id: UUID | None,
        strategy_name: str,
        strategy_version: str,
        universe_code: str,
        horizon: int,
        window_spec: dict,
        start_date,
        end_date,
        holdout_start_date,
    ) -> RegimeBacktestRun:
        run = RegimeBacktestRun(
            experiment_run_id=experiment_run_id,
            policy_config_id=policy_config_id,
            baseline_policy_config_id=baseline_policy_config_id,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            horizon=horizon,
            window_spec=window_spec,
            start_date=start_date,
            end_date=end_date,
            holdout_start_date=holdout_start_date,
            train_metrics={},
            holdout_metrics={},
            status=RegimeBacktestRunStatus.RUNNING.value,
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def complete(
        self,
        run: RegimeBacktestRun,
        *,
        train_metrics: dict,
        holdout_metrics: dict,
        comparison_vs_baseline: dict | None,
        research_findings: dict | None,
        days_included: int,
        days_excluded: int,
    ) -> RegimeBacktestRun:
        run.train_metrics = train_metrics
        run.holdout_metrics = holdout_metrics
        run.comparison_vs_baseline = comparison_vs_baseline
        run.research_findings = research_findings
        run.days_included = days_included
        run.days_excluded = days_excluded
        run.status = RegimeBacktestRunStatus.COMPLETED.value
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def fail(self, run: RegimeBacktestRun, error_message: str) -> RegimeBacktestRun:
        run.status = RegimeBacktestRunStatus.FAILED.value
        run.error_message = error_message
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def get_by_id(self, run_id: UUID) -> RegimeBacktestRun | None:
        return self.db.scalar(select(RegimeBacktestRun).where(RegimeBacktestRun.id == run_id))

    def list_runs(
        self,
        *,
        experiment_run_id: UUID | None = None,
        policy_config_id: UUID | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[RegimeBacktestRun]:
        stmt = select(RegimeBacktestRun).order_by(RegimeBacktestRun.started_at.desc())
        if experiment_run_id:
            stmt = stmt.where(RegimeBacktestRun.experiment_run_id == experiment_run_id)
        if policy_config_id:
            stmt = stmt.where(RegimeBacktestRun.policy_config_id == policy_config_id)
        if status:
            stmt = stmt.where(RegimeBacktestRun.status == status)
        return list(self.db.scalars(stmt.limit(limit)).all())
