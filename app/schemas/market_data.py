from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import IngestBatchStatus, IngestionMode, IngestionRunStatus


class MarketDataRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stock_id: UUID
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: int | None
    adj_close: float | None
    dividend: float | None
    split_factor: float | None
    source: str
    ingested_at: datetime


class IngestionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    provider: str
    requested_period: str
    rows_inserted: int
    rows_updated: int
    rows_skipped: int
    status: IngestionRunStatus
    error_message: str | None = None
    first_date_loaded: date | None = None
    last_date_loaded: date | None = None


class MarketDataIngestResponse(BaseModel):
    batch_id: UUID | None = None
    symbols_processed: int
    symbols_failed: int
    rows_inserted: int
    rows_updated: int
    rows_skipped: int
    status: IngestBatchStatus
    ingestion_mode: IngestionMode = IngestionMode.FULL_REFRESH
    execution_duration_ms: int | None = None
    runs: list[IngestionRunRead] = Field(default_factory=list)

    @property
    def failure_rate(self) -> float:
        total = self.symbols_processed + self.symbols_failed
        if total == 0:
            return 0.0
        return self.symbols_failed / total

    @property
    def is_unhealthy_batch(self) -> bool:
        return self.failure_rate > 0.5
