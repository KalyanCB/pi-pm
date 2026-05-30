from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.stock import Stock
    from app.models.stock_universe import StockUniverse


class UniverseMembership(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "universe_memberships"

    universe_id: Mapped[UUID] = mapped_column(
        ForeignKey("stock_universes.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    universe: Mapped[StockUniverse] = relationship(back_populates="memberships")
    stock: Mapped[Stock] = relationship(back_populates="universe_memberships")

    __table_args__ = (
        UniqueConstraint("universe_id", "stock_id", name="uq_universe_membership_universe_stock"),
        Index("ix_universe_memberships_universe", "universe_id"),
    )
