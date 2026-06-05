"""Portfolio analytics models — NAV history, cash ledger, reconciliation, exit recommendations."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PortfolioNavHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Daily NAV snapshot — append-only time series."""

    __tablename__ = "portfolio_nav_history"

    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    total_equity: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    cash_balance: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    market_value: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    realized_pnl_cumulative: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, default=0
    )
    open_positions: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    cash_pct: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0)
    day_return_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    benchmark_return_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    alpha_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    regime_label: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (Index("ix_portfolio_nav_history_date", "as_of_date"),)


class CashLedger(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Append-only cash movement log — never update, only insert."""

    __tablename__ = "portfolio_cash_ledger"

    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # INITIAL_CAPITAL | TRADE_BUY | TRADE_SELL | FEE | DIVIDEND | ADJUSTMENT
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    # Positive = cash in, Negative = cash out
    balance_after: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    reference_id: Mapped[UUID | None] = mapped_column()
    # Points to paper_trade.id or portfolio_position.id
    reference_type: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(String(256))
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        Index("ix_cash_ledger_date", "as_of_date"),
        Index("ix_cash_ledger_type", "entry_type"),
    )


class PortfolioReconciliationReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Daily reconciliation result — gates analytics."""

    __tablename__ = "portfolio_reconciliation_reports"

    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    # PASS | WARNING | FAIL

    # Computed values
    cash_from_ledger: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    market_value_from_positions: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    realized_pnl_from_closed: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    computed_nav: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    reported_nav: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    discrepancy: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    discrepancy_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)

    # Checks
    checks: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # {"trade_consistency": "PASS", "position_consistency": "WARNING", ...}
    warnings: Mapped[list[str] | None] = mapped_column(JSONB)
    failures: Mapped[list[str] | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_recon_reports_status", "status"),
        Index("ix_recon_reports_date", "as_of_date"),
    )


class ExitRecommendation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Machine-generated exit candidates awaiting human confirmation.

    Exit Monitor writes these. Never auto-executes.
    Human confirms via POST /portfolio/trades/exit.
    """

    __tablename__ = "portfolio_exit_recommendations"

    portfolio_position_id: Mapped[UUID] = mapped_column(
        ForeignKey("portfolio_positions.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    # PENDING | CONFIRMED | REJECTED | EXPIRED

    # Exit triggers fired (one or more)
    triggers: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    # ["EXIT_RANK_DROP", "EXIT_TIME", ...]

    trigger_details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # {"EXIT_RANK_DROP": {"current_rank": 45, "threshold": 40}, ...}

    # Metrics at trigger time
    current_rank: Mapped[int | None] = mapped_column()
    days_held: Mapped[int | None] = mapped_column()
    unrealized_pnl_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    urgency: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")
    # LOW | NORMAL | HIGH | CRITICAL

    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(256))

    position: Mapped[PortfolioPosition] = relationship("PortfolioPosition")

    __table_args__ = (
        Index("ix_exit_recs_status", "status"),
        Index("ix_exit_recs_date", "as_of_date"),
        Index("ix_exit_recs_position", "portfolio_position_id"),
    )


# Forward reference fix
from app.models.portfolio_position import PortfolioPosition  # noqa: E402

ExitRecommendation.__annotations__["position"] = PortfolioPosition
