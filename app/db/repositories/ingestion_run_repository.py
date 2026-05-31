from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import IngestionRunStatus
from app.models.market_data_ingestion_run import MarketDataIngestionRun


class IngestionRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_running(
        self,
        symbol: str,
        provider: str,
        requested_period: str,
        *,
        batch_id: UUID | None = None,
        ingestion_mode: str | None = None,
    ) -> MarketDataIngestionRun:
        run = MarketDataIngestionRun(
            symbol=symbol,
            provider=provider,
            requested_period=requested_period,
            batch_id=batch_id,
            ingestion_mode=ingestion_mode,
            started_at=datetime.now(UTC),
            status=IngestionRunStatus.RUNNING.value,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def complete(
        self,
        run: MarketDataIngestionRun,
        rows_inserted: int,
        rows_updated: int,
        rows_skipped: int,
        *,
        first_date_loaded=None,
        last_date_loaded=None,
    ) -> MarketDataIngestionRun:
        run.rows_inserted = rows_inserted
        run.rows_updated = rows_updated
        run.rows_skipped = rows_skipped
        run.first_date_loaded = first_date_loaded
        run.last_date_loaded = last_date_loaded
        run.completed_at = datetime.now(UTC)
        run.status = IngestionRunStatus.COMPLETED.value
        self.db.flush()
        return run

    def fail(self, run: MarketDataIngestionRun, error_message: str) -> MarketDataIngestionRun:
        run.completed_at = datetime.now(UTC)
        run.status = IngestionRunStatus.FAILED.value
        run.error_message = error_message
        self.db.flush()
        return run

    def get_latest_completed_for_symbol(
        self,
        symbol: str,
        *,
        before_date=None,
    ) -> MarketDataIngestionRun | None:
        stmt = (
            select(MarketDataIngestionRun)
            .where(
                MarketDataIngestionRun.symbol == symbol,
                MarketDataIngestionRun.status == IngestionRunStatus.COMPLETED.value,
            )
            .order_by(MarketDataIngestionRun.completed_at.desc())
        )
        if before_date is not None:
            stmt = stmt.where(MarketDataIngestionRun.last_date_loaded <= before_date)
        return self.db.scalar(stmt.limit(1))

    def link_batch_symbol(
        self,
        run: MarketDataIngestionRun,
        batch_id: UUID,
    ) -> MarketDataIngestionRun:
        run.batch_id = batch_id
        self.db.flush()
        return run
