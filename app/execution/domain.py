"""Execution domain types — Track K."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.execution.constants import ExecutionMode, ExecutionStatus


@dataclass(frozen=True)
class TradeRequest:
    """Outbound order intent — created only after human approval."""

    portfolio_id: UUID
    symbol: str
    side: str
    quantity: Decimal
    strategy_name: str
    recommendation_id: UUID
    approval_id: UUID
    requested_by: UUID
    execution_mode: ExecutionMode
    timestamp: datetime
    client_order_id: str
    order_type: str = "MARKET"
    limit_price: Decimal | None = None
    idempotency_key: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TradeResult:
    """Inbound fill or terminal status from broker or paper simulator."""

    broker_name: str
    broker_order_id: str | None
    execution_status: ExecutionStatus
    filled_quantity: Decimal
    avg_fill_price: Decimal | None
    fees: Decimal | None = None
    slippage: Decimal | None = None
    raw_response: dict = field(default_factory=dict)
    rejection_reason: str | None = None
    filled_at: datetime | None = None
