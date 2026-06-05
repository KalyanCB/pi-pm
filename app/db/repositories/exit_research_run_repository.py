from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import ExitResearchPhase, ExitResearchRunStatus
from app.models.exit_research import ExitResearchRun


class ExitResearchRunRepository:
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
        parameter_set: dict,
    ) -> ExitResearchRun:
        run = ExitResearchRun(
            status=ExitResearchRunStatus.RUNNING.value,
            current_phase=ExitResearchPhase.COLLECTING_ENTRIES.value,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            as_of_date_start=as_of_date_start,
            as_of_date_end=as_of_date_end,
            holdout_start_date=holdout_start_date,
            parameter_set=parameter_set,
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def set_phase(self, run: ExitResearchRun, phase: ExitResearchPhase | str) -> ExitResearchRun:
        value = phase.value if isinstance(phase, ExitResearchPhase) else phase
        run.current_phase = value
        run.last_progress_at = datetime.now(UTC)
        self.db.flush()
        return run

    def set_total_entries(self, run: ExitResearchRun, total_entries: int) -> ExitResearchRun:
        run.total_entries = total_entries
        run.processed_entries = 0
        run.percent_complete = 0.0 if total_entries else None
        self.db.flush()
        return run

    def update_progress(
        self,
        run: ExitResearchRun,
        *,
        processed_entries: int,
        percent_complete: float,
        elapsed_seconds: float,
    ) -> ExitResearchRun:
        run.processed_entries = processed_entries
        run.percent_complete = percent_complete
        run.elapsed_seconds = elapsed_seconds
        run.last_progress_at = datetime.now(UTC)
        self.db.flush()
        return run

    def set_persistence_totals(
        self,
        run: ExitResearchRun,
        *,
        persistence_items_total: int,
    ) -> ExitResearchRun:
        run.persistence_items_total = persistence_items_total
        run.persistence_items_processed = 0
        self.db.flush()
        return run

    def update_persistence_progress(
        self,
        run: ExitResearchRun,
        *,
        persistence_items_processed: int,
        percent_complete: float,
        elapsed_seconds: float,
    ) -> ExitResearchRun:
        run.persistence_items_processed = persistence_items_processed
        run.percent_complete = percent_complete
        run.elapsed_seconds = elapsed_seconds
        run.last_progress_at = datetime.now(UTC)
        self.db.flush()
        return run

    def complete(
        self, run: ExitResearchRun, *, signals_processed: int, metrics_written: int
    ) -> ExitResearchRun:
        run.status = ExitResearchRunStatus.COMPLETED.value
        run.current_phase = ExitResearchPhase.COMPLETED.value
        run.signals_processed = signals_processed
        run.metrics_written = metrics_written
        run.completed_at = datetime.now(UTC)
        run.percent_complete = 100.0
        self.db.flush()
        return run

    def fail(self, run: ExitResearchRun, error_message: str) -> ExitResearchRun:
        run.status = ExitResearchRunStatus.FAILED.value
        run.current_phase = ExitResearchPhase.FAILED.value
        run.error_message = error_message
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def get_by_id(self, run_id: UUID) -> ExitResearchRun | None:
        return self.db.get(ExitResearchRun, run_id)

    def list_runs(self, *, limit: int = 50) -> list[ExitResearchRun]:
        stmt = select(ExitResearchRun).order_by(ExitResearchRun.started_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())
