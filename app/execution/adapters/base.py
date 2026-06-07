"""Execution adapter contract — Track K."""
from __future__ import annotations

from typing import Protocol

from app.execution.domain import TradeRequest, TradeResult


class ExecutionAdapter(Protocol):
    """Broker port — the only path from approved intent to market."""

    @property
    def broker_name(self) -> str:
        """Stable identifier, e.g. 'paper', 'zerodha_kite'."""
        ...

    def place_order(self, request: TradeRequest) -> TradeResult:
        """Submit order. Must be idempotent on client_order_id."""
        ...

    def get_order_status(self, broker_order_id: str) -> TradeResult:
        """Poll current order state."""
        ...

    def cancel_order(self, broker_order_id: str) -> TradeResult:
        """Cancel if still open."""
        ...

    def health_check(self) -> TradeResult:
        """Connectivity probe — FILLED means healthy, REJECTED means down."""
        ...

    def sync_holdings(self, portfolio_id: str) -> list[dict]:
        """Return broker-reported holdings for reconciliation (live adapters)."""
        ...

    def sync_positions(self, portfolio_id: str) -> list[dict]:
        """Return broker-reported positions for reconciliation (live adapters)."""
        ...
