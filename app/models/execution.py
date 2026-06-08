"""Execution platform ORM models — Track K."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ExecutionOrder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "execution_orders"

    portfolio_id: Mapped[UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    strategy_name: Mapped[str | None] = mapped_column(String(64))
    recommendation_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendation_results.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approval_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendation_approvals.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    executed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    execution_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="PAPER")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="EXECUTION_PENDING")
    client_order_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    broker_name: Mapped[str | None] = mapped_column(String(32))
    broker_order_id: Mapped[str | None] = mapped_column(String(64), index=True)
    filled_quantity: Mapped[float | None] = mapped_column(Numeric(18, 8))
    avg_fill_price: Mapped[float | None] = mapped_column(Numeric(18, 4))
    fees: Mapped[float | None] = mapped_column(Numeric(12, 2))
    slippage: Mapped[float | None] = mapped_column(Numeric(10, 4))
    paper_trade_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("paper_trades.id", ondelete="SET NULL"), nullable=True
    )
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_execution_orders_status", "status"),
        Index("ix_execution_orders_portfolio_status", "portfolio_id", "status"),
    )


class ExecutionEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "execution_events"

    execution_order_id: Mapped[UUID] = mapped_column(
        ForeignKey("execution_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, default="STATE_TRANSITION")
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    __table_args__ = (Index("ix_execution_events_order_created", "execution_order_id", "created_at"),)


class ExecutionConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "execution_configs"

    portfolio_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True, index=True
    )
    execution_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="PAPER")
    broker_name: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(String(256))


class ExecutionAudit(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "execution_audit"

    execution_order_id: Mapped[UUID] = mapped_column(
        ForeignKey("execution_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    execution_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    broker_name: Mapped[str | None] = mapped_column(String(32))
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    __table_args__ = (Index("ix_execution_audit_order_created", "execution_order_id", "created_at"),)
