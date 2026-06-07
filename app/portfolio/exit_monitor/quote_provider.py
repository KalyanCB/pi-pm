"""Quote provider abstraction for T1 intraday exit monitor (ADR-033).

Production hierarchy:
  Live S1+  → KiteQuoteProvider  (real-time LTP via Kite WebSocket / REST)
  Paper S0  → LastCloseProvider  (uses latest close from market_data as proxy)

The T1 monitor receives a QuoteProvider at construction; callers inject the
appropriate implementation. No LTP logic leaks into the monitor itself.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.repositories.market_data_repository import MarketDataRepository


class QuoteProvider(ABC):
    """Return current LTP (or best available proxy) for a position."""

    @abstractmethod
    def get_ltp(self, stock_id: UUID) -> float | None:
        """Return last traded price or None if unavailable."""
        ...


class LastCloseQuoteProvider(QuoteProvider):
    """Paper-mode proxy: returns the most recent daily close from market_data.

    Eliminates intraday wick false-stops (the dominant false-stop source per
    the ADR-033 counterfactual analysis — 25 wicked trades, -₹20.6k cost).
    """

    def __init__(self, db: Session) -> None:
        self._repo = MarketDataRepository(db)

    def get_ltp(self, stock_id: UUID) -> float | None:
        bar = self._repo.get_latest_market_data(stock_id)
        return float(bar.close) if bar else None
