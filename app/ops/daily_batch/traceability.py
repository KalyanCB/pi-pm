from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.constants import (
    DailyBatchArtifactType,
    LineageEntityType,
    LineageRelationshipType,
)
from app.db.repositories.daily_batch_artifact_repository import DailyBatchArtifactRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository


class DailyBatchTraceabilityRecorder:
    def __init__(self, db: Session) -> None:
        self.lineage_repo = RunLineageRepository(db)
        self.artifact_repo = DailyBatchArtifactRepository(db)

    def record_ingestion_batch(self, daily_batch_id: UUID, batch_id: UUID, *, status: str) -> None:
        self._link(daily_batch_id, LineageEntityType.INGESTION_BATCH, batch_id, LineageRelationshipType.DAILY_BATCH_INGESTION)
        self.artifact_repo.add(
            daily_batch_run_id=daily_batch_id,
            artifact_type=DailyBatchArtifactType.INGESTION_BATCH.value,
            artifact_id=batch_id,
            status=status,
        )

    def record_ranking_run(
        self,
        daily_batch_id: UUID,
        ranking_run_id: UUID,
        *,
        strategy_name: str,
        as_of_date,
        status: str,
    ) -> None:
        self._link(daily_batch_id, LineageEntityType.RANKING_RUN, ranking_run_id, LineageRelationshipType.DAILY_BATCH_RANKING)
        self.artifact_repo.add(
            daily_batch_run_id=daily_batch_id,
            artifact_type=DailyBatchArtifactType.RANKING_RUN.value,
            artifact_id=ranking_run_id,
            strategy_name=strategy_name,
            as_of_date=as_of_date,
            status=status,
        )

    def record_validation_report(self, daily_batch_id: UUID, report_id: UUID, *, status: str) -> None:
        self._link(
            daily_batch_id,
            LineageEntityType.VALIDATION_REPORT,
            report_id,
            LineageRelationshipType.DAILY_BATCH_VALIDATION,
        )
        self.artifact_repo.add(
            daily_batch_run_id=daily_batch_id,
            artifact_type=DailyBatchArtifactType.VALIDATION_REPORT.value,
            artifact_id=report_id,
            status=status,
        )

    def record_factor_run(self, daily_batch_id: UUID, run_id: UUID, *, strategy_name: str, status: str) -> None:
        self._link(
            daily_batch_id,
            LineageEntityType.FACTOR_PERFORMANCE_RUN,
            run_id,
            LineageRelationshipType.DAILY_BATCH_FACTOR_IC,
        )
        self.artifact_repo.add(
            daily_batch_run_id=daily_batch_id,
            artifact_type=DailyBatchArtifactType.FACTOR_PERFORMANCE_RUN.value,
            artifact_id=run_id,
            strategy_name=strategy_name,
            status=status,
        )

    def record_regime_history_backfill(
        self,
        daily_batch_id: UUID,
        artifact_id: UUID,
        *,
        rows_written: int,
    ) -> None:
        self.artifact_repo.add(
            daily_batch_run_id=daily_batch_id,
            artifact_type=DailyBatchArtifactType.REGIME_HISTORY_BACKFILL.value,
            artifact_id=artifact_id,
            status="completed",
        )

    def record_regime_performance_refresh(
        self,
        daily_batch_id: UUID,
        artifact_id: UUID,
        *,
        strategy_name: str,
    ) -> None:
        self.artifact_repo.add(
            daily_batch_run_id=daily_batch_id,
            artifact_type=DailyBatchArtifactType.REGIME_PERFORMANCE_REFRESH.value,
            artifact_id=artifact_id,
            strategy_name=strategy_name,
            status="completed",
        )

    def record_research_intelligence_run(
        self,
        daily_batch_id: UUID,
        run_id: UUID,
        *,
        status: str,
    ) -> None:
        self._link(
            daily_batch_id,
            LineageEntityType.RESEARCH_INTELLIGENCE_RUN,
            run_id,
            LineageRelationshipType.DAILY_BATCH_RESEARCH,
        )
        self.artifact_repo.add(
            daily_batch_run_id=daily_batch_id,
            artifact_type=DailyBatchArtifactType.RESEARCH_INTELLIGENCE_RUN.value,
            artifact_id=run_id,
            status=status,
        )

    def record_exit_research_run(self, daily_batch_id: UUID, run_id: UUID, *, strategy_name: str, status: str) -> None:
        self._link(
            daily_batch_id,
            LineageEntityType.EXIT_RESEARCH_RUN,
            run_id,
            LineageRelationshipType.DAILY_BATCH_EXIT_RESEARCH,
        )
        self.artifact_repo.add(
            daily_batch_run_id=daily_batch_id,
            artifact_type=DailyBatchArtifactType.EXIT_RESEARCH_RUN.value,
            artifact_id=run_id,
            strategy_name=strategy_name,
            status=status,
        )

    def _link(
        self,
        daily_batch_id: UUID,
        child_type: LineageEntityType,
        child_id: UUID,
        relationship: LineageRelationshipType,
    ) -> None:
        self.lineage_repo.link(
            child_entity_type=child_type.value,
            child_entity_id=child_id,
            parent_entity_type=LineageEntityType.DAILY_BATCH_RUN.value,
            parent_entity_id=daily_batch_id,
            relationship_type=relationship.value,
        )
