from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import FactorPerformanceRunStatus
from app.models.factor_analytics import FactorPerformanceRun


class FactorPerformanceRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_running(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        universe_code: str,
        as_of_date_start,
        as_of_date_end,
        holdout_start_date,
        horizon: int | None,
        parameter_set: dict,
    ) -> FactorPerformanceRun:
        run = FactorPerformanceRun(
            status=FactorPerformanceRunStatus.RUNNING.value,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            horizon=horizon,
            as_of_date_start=as_of_date_start,
            as_of_date_end=as_of_date_end,
            holdout_start_date=holdout_start_date,
            parameter_set=parameter_set,
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def complete(
        self,
        run: FactorPerformanceRun,
        *,
        reports_processed: int,
        metrics_written: int,
    ) -> FactorPerformanceRun:
        run.status = FactorPerformanceRunStatus.COMPLETED.value
        run.reports_processed = reports_processed
        run.metrics_written = metrics_written
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def fail(self, run: FactorPerformanceRun, error_message: str) -> FactorPerformanceRun:
        run.status = FactorPerformanceRunStatus.FAILED.value
        run.error_message = error_message
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def get_by_id(self, run_id: UUID) -> FactorPerformanceRun | None:
        return self.db.get(FactorPerformanceRun, run_id)

    def list_runs(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[FactorPerformanceRun]:
        stmt = select(FactorPerformanceRun).order_by(FactorPerformanceRun.started_at.desc())
        if status:
            stmt = stmt.where(FactorPerformanceRun.status == status)
        stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).all())
