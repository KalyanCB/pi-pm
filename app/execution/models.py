"""Backward-compatible re-exports for execution domain types."""
from __future__ import annotations

from app.execution.constants import ExecutionMode, ExecutionStatus
from app.execution.domain import TradeRequest, TradeResult

# Legacy aliases (ADR-030 / Track I)
OrderStatus = ExecutionStatus
TradeConfirmation = TradeResult

__all__ = [
    "ExecutionMode",
    "ExecutionStatus",
    "OrderStatus",
    "TradeConfirmation",
    "TradeRequest",
    "TradeResult",
]
