from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import IngestionRunStatus
from app.models.platform_traceability import IngestionBatchRun


class IngestionBatchRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_running(
        self,
        *,
        provider: str,
        period: str,
        ingestion_mode: str,
        symbol_count_requested: int,
    ) -> IngestionBatchRun:
        batch = IngestionBatchRun(
            provider=provider,
            period=period,
            ingestion_mode=ingestion_mode,
            symbol_count_requested=symbol_count_requested,
            status=IngestionRunStatus.RUNNING.value,
            started_at=datetime.now(UTC),
        )
        self.db.add(batch)
        self.db.flush()
        return batch

    def complete(
        self,
        batch: IngestionBatchRun,
        *,
        symbol_count_succeeded: int,
        symbol_count_failed: int,
        rows_inserted: int,
        rows_updated: int,
        rows_skipped: int,
        execution_duration_ms: int,
        status: str,
        error_summary: str | None = None,
    ) -> IngestionBatchRun:
        batch.symbol_count_succeeded = symbol_count_succeeded
        batch.symbol_count_failed = symbol_count_failed
        batch.rows_inserted = rows_inserted
        batch.rows_updated = rows_updated
        batch.rows_skipped = rows_skipped
        batch.execution_duration_ms = execution_duration_ms
        batch.status = status
        batch.error_summary = error_summary
        batch.completed_at = datetime.now(UTC)
        self.db.flush()
        return batch

    def get_by_id(self, batch_id: UUID) -> IngestionBatchRun | None:
        return self.db.scalar(
            select(IngestionBatchRun).where(IngestionBatchRun.id == batch_id)
        )

    def list_recent(self, limit: int = 20) -> list[IngestionBatchRun]:
        return list(
            self.db.scalars(
                select(IngestionBatchRun).order_by(IngestionBatchRun.started_at.desc()).limit(limit)
            ).all()
        )
