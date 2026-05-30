from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import TradeStatus
from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.stock import Stock


class PaperTrade(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "paper_trades"

    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    limit_price: Mapped[float | None] = mapped_column(Numeric(18, 6))
    fill_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    fill_quantity: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=TradeStatus.PENDING.value)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    ranking_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="SET NULL"), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)

    stock: Mapped[Stock] = relationship("Stock")

    __table_args__ = (
        Index("ix_paper_trades_stock_filled", "stock_id", "filled_at"),
        Index("ix_paper_trades_status", "status"),
    )
