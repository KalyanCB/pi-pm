"""Broker adapter protocol — backward-compatible alias (Track I → Track K).

See: docs/architecture/ADR-031-Unified-Execution-Architecture.md
"""
from __future__ import annotations

from app.execution.adapters.base import ExecutionAdapter
from app.execution.domain import TradeRequest, TradeResult

# Legacy name from ADR-030
BrokerAdapter = ExecutionAdapter

__all__ = ["BrokerAdapter", "ExecutionAdapter", "TradeRequest", "TradeResult"]
