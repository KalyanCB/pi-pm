from __future__ import annotations

from datetime import UTC, datetime

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
    ) -> MarketDataIngestionRun:
        run = MarketDataIngestionRun(
            symbol=symbol,
            provider=provider,
            requested_period=requested_period,
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
    ) -> MarketDataIngestionRun:
        run.rows_inserted = rows_inserted
        run.rows_updated = rows_updated
        run.rows_skipped = rows_skipped
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
