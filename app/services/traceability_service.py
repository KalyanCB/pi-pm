from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import LineageEntityType, LineageRelationshipType
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.ranking_factor_contribution_repository import (
    RankingFactorContributionRepository,
)
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.validation_metrics_repository import ValidationMetricsRepository
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.ranking.weight_hashing import hash_weight_config
from app.validation.constants import VALIDATION_STATUS_COMPLETED


class TraceabilityService:
    def __init__(
        self,
        db: Session,
        factor_contribution_repo: RankingFactorContributionRepository,
        validation_metrics_repo: ValidationMetricsRepository,
        lineage_repo: RunLineageRepository,
        ingestion_run_repo: IngestionRunRepository,
    ) -> None:
        self.db = db
        self.factor_contribution_repo = factor_contribution_repo
        self.validation_metrics_repo = validation_metrics_repo
        self.lineage_repo = lineage_repo
        self.ingestion_run_repo = ingestion_run_repo

    def record_ranking_traceability(
        self,
        run: RankingRun,
        *,
        weight_config_hash: str | None,
        regime_label: str | None,
        ranked_stock_count: int,
        excluded_stock_count: int,
        execution_duration_ms: int,
        benchmark_ingestion_run_id: UUID | None = None,
    ) -> int:
        run.weight_config_hash = weight_config_hash
        run.regime_label = regime_label
        run.ranked_stock_count = ranked_stock_count
        run.excluded_stock_count = excluded_stock_count
        run.execution_duration_ms = execution_duration_ms
        self.db.flush()

        factor_rows = self.factor_contribution_repo.sync_from_results(run.id)

        if benchmark_ingestion_run_id is not None:
            self.lineage_repo.link(
                child_entity_type=LineageEntityType.RANKING_RUN.value,
                child_entity_id=run.id,
                parent_entity_type=LineageEntityType.INGESTION_SYMBOL.value,
                parent_entity_id=benchmark_ingestion_run_id,
                relationship_type=LineageRelationshipType.RANKING_INGESTION.value,
            )

        return factor_rows

    def ensure_ranking_traceability(self, run: RankingRun) -> bool:
        """Idempotently populate ranking traceability from persisted artifacts."""
        if self._ranking_traceability_complete(run):
            return False

        changed = False
        metadata = run.metadata_ or {}

        if run.weight_config_hash is None:
            weights = metadata.get("effective_weights") or {}
            if weights:
                run.weight_config_hash = hash_weight_config(weights)
                changed = True

        if run.ranked_stock_count is None:
            ranked = metadata.get("ranked_stock_count")
            if ranked is not None:
                run.ranked_stock_count = int(ranked)
                changed = True
            else:
                result_count = self._count_ranking_results(run.id)
                if result_count > 0:
                    run.ranked_stock_count = result_count
                    changed = True

        if run.excluded_stock_count is None:
            universe_count = metadata.get("universe_stock_count")
            if universe_count is not None and run.ranked_stock_count is not None:
                run.excluded_stock_count = max(int(universe_count) - run.ranked_stock_count, 0)
                changed = True

        if run.regime_label is None:
            regime_label = self._regime_label_from_validation(run.id)
            if regime_label is not None:
                run.regime_label = regime_label
                changed = True

        if not self.factor_contribution_repo.has_for_run(run.id):
            if self._has_score_components(run.id):
                self.factor_contribution_repo.sync_from_results(run.id)
                changed = True

        if changed:
            self.db.flush()
            self.db.commit()
        return changed

    def record_validation_traceability(
        self,
        report: RankingValidationReport,
        ranking_run: RankingRun,
        horizon_metrics: dict,
    ) -> None:
        self.validation_metrics_repo.replace_for_report(report, ranking_run, horizon_metrics)
        self._link_validation_lineage(report, ranking_run)

    def ensure_validation_traceability(
        self,
        report: RankingValidationReport,
        ranking_run: RankingRun,
    ) -> bool:
        """Idempotently populate validation metrics from persisted JSONB."""
        if self.validation_metrics_repo.has_for_report(report.id):
            return False
        if report.status != VALIDATION_STATUS_COMPLETED:
            return False
        if not report.horizon_metrics:
            return False

        self.record_validation_traceability(report, ranking_run, report.horizon_metrics)
        self.db.commit()
        return True

    def ensure_validation_lineage(
        self,
        report: RankingValidationReport,
        ranking_run: RankingRun,
    ) -> bool:
        """Best-effort lineage links without touching validation metrics."""
        before = len(
            self.lineage_repo.list_for_entity(
                LineageEntityType.VALIDATION_REPORT.value,
                report.id,
            )
        )
        self._link_validation_lineage(report, ranking_run)
        self.db.flush()
        after = len(
            self.lineage_repo.list_for_entity(
                LineageEntityType.VALIDATION_REPORT.value,
                report.id,
            )
        )
        if after > before:
            self.db.commit()
            return True
        return False

    def get_validation_lineage(self, validation_report_id: UUID) -> list[dict]:
        records = self.lineage_repo.list_for_entity(
            LineageEntityType.VALIDATION_REPORT.value,
            validation_report_id,
        )
        return [_lineage_to_dict(record) for record in records]

    def reconstruct_score(
        self,
        ranking_run_id: UUID,
        stock_id: UUID,
    ) -> dict:
        rows = self.factor_contribution_repo.list_by_run(ranking_run_id)
        stock_rows = [row for row in rows if row.stock_id == stock_id]
        total = sum(float(row.weighted_factor_value or 0) for row in stock_rows)
        return {
            "ranking_run_id": str(ranking_run_id),
            "stock_id": str(stock_id),
            "reconstructed_score": total,
            "factors": [
                {
                    "factor_name": row.factor_name,
                    "raw": float(row.raw_factor_value) if row.raw_factor_value is not None else None,
                    "normalized": (
                        float(row.normalized_factor_value)
                        if row.normalized_factor_value is not None
                        else None
                    ),
                    "weighted": (
                        float(row.weighted_factor_value)
                        if row.weighted_factor_value is not None
                        else None
                    ),
                }
                for row in stock_rows
            ],
        }

    def _ranking_traceability_complete(self, run: RankingRun) -> bool:
        if not self.factor_contribution_repo.has_for_run(run.id):
            return False
        if run.weight_config_hash is None:
            return False
        if run.ranked_stock_count is None:
            return False
        return True

    def _link_validation_lineage(
        self,
        report: RankingValidationReport,
        ranking_run: RankingRun,
    ) -> None:
        self.lineage_repo.link(
            child_entity_type=LineageEntityType.VALIDATION_REPORT.value,
            child_entity_id=report.id,
            parent_entity_type=LineageEntityType.RANKING_RUN.value,
            parent_entity_id=ranking_run.id,
            relationship_type=LineageRelationshipType.VALIDATES_RANKING.value,
        )

        benchmark_run = self.ingestion_run_repo.get_latest_completed_for_symbol(
            ranking_run.benchmark_symbol,
            before_date=ranking_run.as_of_date,
        )
        if benchmark_run is not None:
            self.lineage_repo.link(
                child_entity_type=LineageEntityType.RANKING_RUN.value,
                child_entity_id=ranking_run.id,
                parent_entity_type=LineageEntityType.INGESTION_SYMBOL.value,
                parent_entity_id=benchmark_run.id,
                relationship_type=LineageRelationshipType.RANKING_INGESTION.value,
            )
            if benchmark_run.batch_id is not None:
                self.lineage_repo.link(
                    child_entity_type=LineageEntityType.INGESTION_SYMBOL.value,
                    child_entity_id=benchmark_run.id,
                    parent_entity_type=LineageEntityType.INGESTION_BATCH.value,
                    parent_entity_id=benchmark_run.batch_id,
                    relationship_type=LineageRelationshipType.BATCH_SYMBOL.value,
                )

    def _count_ranking_results(self, ranking_run_id: UUID) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(RankingResult)
                .where(RankingResult.ranking_run_id == ranking_run_id)
            )
            or 0
        )

    def _has_score_components(self, ranking_run_id: UUID) -> bool:
        count = self.db.scalar(
            select(func.count())
            .select_from(RankingResult)
            .where(
                RankingResult.ranking_run_id == ranking_run_id,
                RankingResult.score_components.is_not(None),
            )
        )
        return int(count or 0) > 0

    def _regime_label_from_validation(self, ranking_run_id: UUID) -> str | None:
        report = self.db.scalar(
            select(RankingValidationReport).where(
                RankingValidationReport.ranking_run_id == ranking_run_id,
                RankingValidationReport.regime_label.is_not(None),
            )
        )
        return report.regime_label if report is not None else None


def _lineage_to_dict(record) -> dict:
    return {
        "child_entity_type": record.child_entity_type,
        "child_entity_id": str(record.child_entity_id),
        "parent_entity_type": record.parent_entity_type,
        "parent_entity_id": str(record.parent_entity_id),
        "relationship_type": record.relationship_type,
        "created_at": record.created_at.isoformat(),
    }
