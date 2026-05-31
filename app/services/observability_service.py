from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import IngestionRunStatus, RankingRunStatus
from app.db.repositories.experiment_run_repository import ExperimentRunRepository
from app.db.repositories.ingestion_batch_repository import IngestionBatchRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.models.market_data_ingestion_run import MarketDataIngestionRun
from app.models.platform_traceability import (
    ExperimentRun,
    IngestionBatchRun,
    ValidationHorizonMetric,
)
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport


class ObservabilityService:
    def __init__(
        self,
        db: Session,
        ingestion_batch_repo: IngestionBatchRepository,
        ranking_run_repo: RankingRunRepository,
        experiment_run_repo: ExperimentRunRepository,
        lineage_repo: RunLineageRepository,
    ) -> None:
        self.db = db
        self.ingestion_batch_repo = ingestion_batch_repo
        self.ranking_run_repo = ranking_run_repo
        self.experiment_run_repo = experiment_run_repo
        self.lineage_repo = lineage_repo

    def get_platform_health(self) -> dict:
        latest_ingestion = self.db.scalar(
            select(IngestionBatchRun)
            .order_by(IngestionBatchRun.started_at.desc())
            .limit(1)
        )
        latest_ranking = self.db.scalar(
            select(RankingRun)
            .where(RankingRun.status == RankingRunStatus.COMPLETED.value)
            .order_by(RankingRun.completed_at.desc())
            .limit(1)
        )
        latest_validation = self.db.scalar(
            select(RankingValidationReport)
            .order_by(RankingValidationReport.computed_at.desc())
            .limit(1)
        )
        failed_ingestions_24h = self.db.scalar(
            select(func.count())
            .select_from(MarketDataIngestionRun)
            .where(MarketDataIngestionRun.status == IngestionRunStatus.FAILED.value)
        )
        return {
            "status": "ok",
            "latest_ingestion_batch": _batch_summary(latest_ingestion),
            "latest_ranking_run": _ranking_summary(latest_ranking),
            "latest_validation_report": _validation_summary(latest_validation),
            "failed_ingestion_runs_total": int(failed_ingestions_24h or 0),
        }

    def list_recent_ingestion_batches(self, limit: int = 20) -> list[dict]:
        batches = self.ingestion_batch_repo.list_recent(limit)
        return [_batch_summary(batch) for batch in batches]

    def get_ingestion_batch(self, batch_id: UUID) -> dict | None:
        batch = self.ingestion_batch_repo.get_by_id(batch_id)
        if batch is None:
            return None
        symbol_runs = self.db.scalars(
            select(MarketDataIngestionRun).where(MarketDataIngestionRun.batch_id == batch_id)
        ).all()
        return {
            **_batch_summary(batch),
            "symbol_runs": [_symbol_run_summary(run) for run in symbol_runs],
        }

    def list_recent_ranking_runs(self, limit: int = 20) -> list[dict]:
        runs = self.db.scalars(
            select(RankingRun)
            .where(RankingRun.status == RankingRunStatus.COMPLETED.value)
            .order_by(RankingRun.completed_at.desc())
            .limit(limit)
        ).all()
        return [_ranking_summary(run) for run in runs]

    def list_recent_experiments(self, limit: int = 20) -> list[dict]:
        runs = self.experiment_run_repo.list_recent(limit)
        return [_experiment_summary(run) for run in runs]

    def get_lineage(self, entity_type: str, entity_id: UUID) -> list[dict]:
        records = self.lineage_repo.list_for_entity(entity_type, entity_id)
        return [
            {
                "child_entity_type": record.child_entity_type,
                "child_entity_id": str(record.child_entity_id),
                "parent_entity_type": record.parent_entity_type,
                "parent_entity_id": str(record.parent_entity_id),
                "relationship_type": record.relationship_type,
                "created_at": record.created_at.isoformat(),
            }
            for record in records
        ]

    def get_validation_metrics_summary(
        self,
        *,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
        regime_label: str | None = None,
        horizon: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        stmt = select(ValidationHorizonMetric).order_by(ValidationHorizonMetric.computed_at.desc())
        if strategy_name:
            stmt = stmt.where(ValidationHorizonMetric.strategy_name == strategy_name)
        if strategy_version:
            stmt = stmt.where(ValidationHorizonMetric.strategy_version == strategy_version)
        if regime_label:
            stmt = stmt.where(ValidationHorizonMetric.regime_label == regime_label)
        if horizon is not None:
            stmt = stmt.where(ValidationHorizonMetric.horizon == horizon)
        rows = self.db.scalars(stmt.limit(limit)).all()
        return [
            {
                "validation_report_id": str(row.validation_report_id),
                "ranking_run_id": str(row.ranking_run_id),
                "strategy_name": row.strategy_name,
                "strategy_version": row.strategy_version,
                "regime_label": row.regime_label,
                "horizon": row.horizon,
                "ic_pearson": float(row.ic_pearson) if row.ic_pearson is not None else None,
                "rank_ic_spearman": (
                    float(row.rank_ic_spearman) if row.rank_ic_spearman is not None else None
                ),
                "spread": float(row.spread) if row.spread is not None else None,
                "sample_size": row.sample_size,
                "computed_at": row.computed_at.isoformat(),
            }
            for row in rows
        ]


def _batch_summary(batch: IngestionBatchRun | None) -> dict | None:
    if batch is None:
        return None
    return {
        "batch_id": str(batch.id),
        "provider": batch.provider,
        "period": batch.period,
        "ingestion_mode": batch.ingestion_mode,
        "symbol_count_requested": batch.symbol_count_requested,
        "symbol_count_succeeded": batch.symbol_count_succeeded,
        "symbol_count_failed": batch.symbol_count_failed,
        "rows_inserted": batch.rows_inserted,
        "rows_updated": batch.rows_updated,
        "rows_skipped": batch.rows_skipped,
        "execution_duration_ms": batch.execution_duration_ms,
        "status": batch.status,
        "started_at": batch.started_at.isoformat(),
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
    }


def _symbol_run_summary(run: MarketDataIngestionRun) -> dict:
    return {
        "run_id": str(run.id),
        "symbol": run.symbol,
        "status": run.status,
        "rows_inserted": run.rows_inserted,
        "rows_updated": run.rows_updated,
        "first_date_loaded": run.first_date_loaded.isoformat() if run.first_date_loaded else None,
        "last_date_loaded": run.last_date_loaded.isoformat() if run.last_date_loaded else None,
        "error_message": run.error_message,
    }


def _ranking_summary(run: RankingRun | None) -> dict | None:
    if run is None:
        return None
    return {
        "ranking_run_id": str(run.id),
        "strategy_name": run.strategy_name,
        "strategy_version": run.strategy_version,
        "universe_code": run.universe_code,
        "regime_label": run.regime_label,
        "as_of_date": run.as_of_date.isoformat(),
        "benchmark": run.benchmark_symbol,
        "filter_config_hash": run.filter_config_hash,
        "weight_config_hash": run.weight_config_hash,
        "ranked_stock_count": run.ranked_stock_count,
        "excluded_stock_count": run.excluded_stock_count,
        "execution_duration_ms": run.execution_duration_ms,
        "status": run.status,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


def _validation_summary(report: RankingValidationReport | None) -> dict | None:
    if report is None:
        return None
    return {
        "validation_report_id": str(report.id),
        "ranking_run_id": str(report.ranking_run_id),
        "regime_label": report.regime_label,
        "status": report.status,
        "computed_at": report.computed_at.isoformat() if report.computed_at else None,
    }


def _experiment_summary(run: ExperimentRun) -> dict:
    return {
        "experiment_id": str(run.id),
        "experiment_name": run.experiment_name,
        "strategy_name": run.strategy_name,
        "strategy_version": run.strategy_version,
        "parameter_set": run.parameter_set,
        "status": run.status,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "notes": run.notes,
    }
