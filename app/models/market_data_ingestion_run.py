from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import IngestionRunStatus
from app.db.base import Base, UUIDPrimaryKeyMixin


class MarketDataIngestionRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "market_data_ingestion_runs"

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

    __table_args__ = (
        Index("ix_market_data_ingestion_runs_symbol_started", "symbol", "started_at"),
    )
