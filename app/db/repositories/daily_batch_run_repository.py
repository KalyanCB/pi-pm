from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import DailyBatchRunStatus
from app.models.daily_batch import DailyBatchRun


class DailyBatchRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_running(
        self,
        *,
        universe_code: str,
        benchmark_symbol: str,
        parameter_set: dict,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> DailyBatchRun:
        run = DailyBatchRun(
            idempotency_key=idempotency_key,
            status=DailyBatchRunStatus.RUNNING.value if not dry_run else DailyBatchRunStatus.PLANNED.value,
            universe_code=universe_code,
            benchmark_symbol=benchmark_symbol,
            parameter_set=parameter_set,
            dry_run=dry_run,
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def get_by_id(self, run_id: UUID) -> DailyBatchRun | None:
        return self.db.get(DailyBatchRun, run_id)

    def get_by_idempotency_key(self, key: str) -> DailyBatchRun | None:
        return self.db.scalar(select(DailyBatchRun).where(DailyBatchRun.idempotency_key == key))

    def update_plan(
        self,
        run: DailyBatchRun,
        *,
        target_trading_day,
        from_date,
        plan_snapshot: dict,
    ) -> DailyBatchRun:
        run.target_trading_day = target_trading_day
        run.from_date = from_date
        run.plan_snapshot = plan_snapshot
        self.db.flush()
        return run

    def update_progress(
        self,
        run: DailyBatchRun,
        *,
        current_phase: str | None = None,
        percent_complete: float | None = None,
        current_load: dict | None = None,
    ) -> DailyBatchRun:
        if current_phase is not None:
            run.current_phase = current_phase
        if percent_complete is not None:
            run.percent_complete = percent_complete
        if current_load is not None:
            run.current_load = current_load
        self.db.flush()
        return run

    def set_phase_results(self, run: DailyBatchRun, phase_results: dict) -> DailyBatchRun:
        run.phase_results = phase_results
        self.db.flush()
        return run

    def complete(self, run: DailyBatchRun, *, duration_seconds: float) -> DailyBatchRun:
        run.status = DailyBatchRunStatus.COMPLETED.value
        run.current_phase = DailyBatchRunStatus.COMPLETED.value
        run.percent_complete = 100.0
        run.completed_at = datetime.now(UTC)
        run.duration_seconds = duration_seconds
        self.db.flush()
        return run

    def fail(self, run: DailyBatchRun, error_message: str) -> DailyBatchRun:
        run.status = DailyBatchRunStatus.FAILED.value
        run.current_phase = DailyBatchRunStatus.FAILED.value
        run.error_message = error_message
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def list_runs(self, *, limit: int = 50) -> list[DailyBatchRun]:
        stmt = select(DailyBatchRun).order_by(DailyBatchRun.started_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())
