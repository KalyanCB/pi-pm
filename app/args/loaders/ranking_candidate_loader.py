from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.validation.constants import VALIDATION_STATUS_COMPLETED


class RankingCandidateLoader:
    def __init__(
        self,
        db: Session,
        ranking_run_repo: RankingRunRepository,
        ranking_result_repo: RankingResultRepository,
        validation_repo: RankingValidationRepository,
    ) -> None:
        self.db = db
        self.ranking_run_repo = ranking_run_repo
        self.ranking_result_repo = ranking_result_repo
        self.validation_repo = validation_repo

    def load(
        self,
        ranking_run_id: UUID,
        *,
        top_n: int,
        require_completed_validation: bool = True,
    ) -> tuple[RankingRun, list[RankingResult]]:
        run = self.ranking_run_repo.get_by_id(ranking_run_id)
        if run is None:
            raise NotFoundError(f"Ranking run not found: {ranking_run_id}")

        if require_completed_validation:
            report = self.validation_repo.get_by_ranking_run_id(ranking_run_id)
            if report is None or report.status != VALIDATION_STATUS_COMPLETED:
                raise NotFoundError(
                    f"Completed validation required for ranking run {ranking_run_id}"
                )

        candidates = self.ranking_result_repo.list_top(ranking_run_id, top_n)
        if not candidates:
            raise NotFoundError(f"No ranking results for run {ranking_run_id}")
        return run, candidates
