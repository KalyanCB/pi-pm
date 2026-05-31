from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import ExperimentRunStatus
from app.models.platform_traceability import ExperimentRun


class ExperimentRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        experiment_name: str,
        strategy_name: str,
        strategy_version: str,
        parameter_set: dict,
        notes: str | None = None,
    ) -> ExperimentRun:
        run = ExperimentRun(
            experiment_name=experiment_name,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            parameter_set=parameter_set,
            status=ExperimentRunStatus.RUNNING.value,
            notes=notes,
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def complete(self, run: ExperimentRun) -> ExperimentRun:
        run.status = ExperimentRunStatus.COMPLETED.value
        run.completed_at = datetime.now(UTC)
        self.db.flush()
        return run

    def get_by_id(self, experiment_id: UUID) -> ExperimentRun | None:
        return self.db.scalar(select(ExperimentRun).where(ExperimentRun.id == experiment_id))

    def list_recent(self, limit: int = 20) -> list[ExperimentRun]:
        return list(
            self.db.scalars(
                select(ExperimentRun).order_by(ExperimentRun.started_at.desc()).limit(limit)
            ).all()
        )
