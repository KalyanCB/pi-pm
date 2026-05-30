from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DataStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.market_data import MarketData
    from app.models.universe_membership import UniverseMembership


class Stock(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "stocks"

    symbol: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    sector: Mapped[str | None] = mapped_column(String(64))
    industry: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    data_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DataStatus.ACTIVE.value
    )

    market_data: Mapped[list[MarketData]] = relationship(back_populates="stock")
    universe_memberships: Mapped[list[UniverseMembership]] = relationship(back_populates="stock")

    __table_args__ = (
        Index("ix_stocks_active_exchange", "is_active", "exchange"),
        Index("ix_stocks_data_status", "data_status"),
    )
