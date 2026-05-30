from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.stock import Stock


class PortfolioPosition(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "portfolio_positions"

    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False, default=0)
    avg_cost: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    market_value: Mapped[float | None] = mapped_column(Numeric(18, 2))
    weight_pct: Mapped[float | None] = mapped_column(Numeric(8, 4))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    stock: Mapped[Stock] = relationship("Stock")

    __table_args__ = (
        Index("ix_portfolio_positions_current", "is_current"),
        Index("ix_portfolio_positions_stock_as_of", "stock_id", "as_of"),
    )
