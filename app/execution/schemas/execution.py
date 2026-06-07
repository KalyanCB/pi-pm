"""Execution API schemas — Track K."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.execution.constants import ExecutionMode


class SubmitOrderRequest(BaseModel):
    recommendation_id: UUID
    approval_id: UUID | None = None
    as_of_date: date | None = None
    idempotency_key: str | None = None
    execution_mode: ExecutionMode | None = None


class ExecutionOrderRead(BaseModel):
    id: UUID
    portfolio_id: UUID
    symbol: str
    side: str
    quantity: float
    strategy_name: str | None
    recommendation_id: UUID
    approval_id: UUID
    requested_by: UUID | None
    approved_by: UUID | None
    executed_by: UUID | None
    execution_mode: str
    status: str
    broker_name: str | None
    broker_order_id: str | None
    filled_quantity: float | None
    avg_fill_price: float | None
    fees: float | None
    slippage: float | None
    paper_trade_id: UUID | None
    rejection_reason: str | None
    submitted_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    raw_response: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class ExecutionEventRead(BaseModel):
    id: UUID
    execution_order_id: UUID
    from_status: str | None
    to_status: str
    event_type: str
    actor_id: UUID | None
    payload: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ExecutionConfigRead(BaseModel):
    portfolio_id: str | None
    execution_mode: str
    broker_name: str | None
    enable_live_trading: bool
    settings: dict[str, Any]
    notes: str | None


class ExecutionConfigUpdate(BaseModel):
    execution_mode: ExecutionMode
    broker_name: str | None = None
    settings: dict[str, Any] | None = None
    notes: str | None = None


class ExecutionHealthRead(BaseModel):
    execution_mode: str
    broker_name: str
    healthy: bool
    status: str
    detail: dict[str, Any]
    rejection_reason: str | None = None
