from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import IngestionRunStatus
from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.platform_traceability import IngestionBatchRun


class MarketDataIngestionRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "market_data_ingestion_runs"

    batch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ingestion_batch_runs.id", ondelete="SET NULL"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_period: Mapped[str] = mapped_column(String(8), nullable=False)
    rows_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=IngestionRunStatus.RUNNING.value
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    ingestion_mode: Mapped[str | None] = mapped_column(String(16))
    first_date_loaded: Mapped[date | None] = mapped_column(Date)
    last_date_loaded: Mapped[date | None] = mapped_column(Date)

    batch: Mapped[IngestionBatchRun | None] = relationship(back_populates="symbol_runs")

    __table_args__ = (
        Index("ix_market_data_ingestion_runs_symbol_started", "symbol", "started_at"),
        Index("ix_market_data_ingestion_runs_batch_id", "batch_id"),
    )
