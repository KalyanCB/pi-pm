from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.stock import Stock


class PortfolioConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Owner-configured capital parameters. One active row at a time."""
    __tablename__ = "portfolio_configs"

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    total_equity: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)  # INR
    deploy_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.85)
    cash_floor_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.15)
    reserve_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.02)
    # Regime slot table (stored as JSONB for PO tunability)
    # Format: {"risk_on": {"max_positions": 8, "max_buy_per_day": 2}, ...}
    regime_slots: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    single_name_cap_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.18)
    sector_cap_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.30)
    slippage_bps: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=5.0)
    fee_per_leg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=20.0)
    notes: Mapped[str | None] = mapped_column(String(256))


class PortfolioPosition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "portfolio_positions"

    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    recommendation_result_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recommendation_results.id", ondelete="SET NULL", use_alter=True,
                   name="fk_portfolio_position_rec_result"),
        nullable=True,
    )
    quantity: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False, default=0)
    avg_cost: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    entry_price: Mapped[float | None] = mapped_column(Numeric(18, 6))
    exit_price: Mapped[float | None] = mapped_column(Numeric(18, 6))
    entry_date: Mapped[date | None] = mapped_column(Date)
    exit_date: Mapped[date | None] = mapped_column(Date)
    market_value: Mapped[float | None] = mapped_column(Numeric(18, 2))
    unrealized_pnl: Mapped[float | None] = mapped_column(Numeric(18, 2))
    realized_pnl: Mapped[float | None] = mapped_column(Numeric(18, 2))
    weight_pct: Mapped[float | None] = mapped_column(Numeric(8, 4))
    conviction_band: Mapped[str | None] = mapped_column(String(16))
    strategy_name: Mapped[str | None] = mapped_column(String(64))
    sector: Mapped[str | None] = mapped_column(String(64))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    position_status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    # OPEN | CLOSED

    stock: Mapped[Stock] = relationship("Stock")

    __table_args__ = (
        Index("ix_portfolio_positions_current", "is_current"),
        Index("ix_portfolio_positions_stock_as_of", "stock_id", "as_of"),
        Index("ix_portfolio_positions_status", "position_status"),
    )
