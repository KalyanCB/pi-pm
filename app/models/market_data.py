from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Date,
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


class MarketData(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "market_data"

    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float | None] = mapped_column(Numeric(18, 6))
    high: Mapped[float | None] = mapped_column(Numeric(18, 6))
    low: Mapped[float | None] = mapped_column(Numeric(18, 6))
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    adj_close: Mapped[float | None] = mapped_column(Numeric(18, 6))
    dividend: Mapped[float | None] = mapped_column(Numeric(18, 6))
    split_factor: Mapped[float | None] = mapped_column(Numeric(18, 8))
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default=MARKET_DATA_SOURCE_YAHOO
    )
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    stock: Mapped[Stock] = relationship(back_populates="market_data")

    __table_args__ = (
        UniqueConstraint("stock_id", "date", "source", name="uq_market_data_stock_date_source"),
        Index("ix_market_data_stock_date", "stock_id", "date"),
    )
