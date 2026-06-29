from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import MARKET_DATA_SOURCE_YAHOO
from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.stock import Stock


class MarketDataIntraday(Base, UUIDPrimaryKeyMixin):
    """Intraday OHLCV bars (e.g. 60-minute) used for realistic next-session VWAP
    fills and size-vs-ADV market-impact modelling. Kept separate from the daily
    ``market_data`` table so the daily signal pipeline is untouched.
    """

    __tablename__ = "market_data_intraday"

    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)  # "60minute" | "minute" | …
    open: Mapped[float | None] = mapped_column(Numeric(18, 6))
    high: Mapped[float | None] = mapped_column(Numeric(18, 6))
    low: Mapped[float | None] = mapped_column(Numeric(18, 6))
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default=MARKET_DATA_SOURCE_YAHOO
    )
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    stock: Mapped[Stock] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "stock_id", "ts", "interval", "source", name="uq_md_intraday_stock_ts_interval_source"
        ),
        Index("ix_md_intraday_stock_ts", "stock_id", "ts"),
    )
