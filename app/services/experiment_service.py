from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.structured_logging import log_event
from app.db.repositories.experiment_run_repository import ExperimentRunRepository
from app.models.platform_traceability import ExperimentRun

logger = logging.getLogger(__name__)


class ExperimentService:
    def __init__(
        self,
        db: Session,
        experiment_repo: ExperimentRunRepository,
    ) -> None:
        self.db = db
        self.experiment_repo = experiment_repo

    def start(
        self,
        *,
        experiment_name: str,
        strategy_name: str,
        strategy_version: str,
        parameter_set: dict,
        notes: str | None = None,
    ) -> ExperimentRun:
        run = self.experiment_repo.create(
            experiment_name=experiment_name,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            parameter_set=parameter_set,
            notes=notes,
        )
        log_event(
            logger,
            "experiment_started",
            experiment_id=run.id,
            experiment_name=run.experiment_name,
            strategy_name=run.strategy_name,
            strategy_version=run.strategy_version,
        )
        self.db.commit()
        return run

    def complete(self, experiment_id: UUID) -> ExperimentRun:
        run = self.experiment_repo.get_by_id(experiment_id)
        if run is None:
            raise ValueError(f"Experiment not found: {experiment_id}")
        completed = self.experiment_repo.complete(run)
        log_event(
            logger,
            "experiment_completed",
            experiment_id=completed.id,
            status=completed.status,
        )
        self.db.commit()
        return completed
