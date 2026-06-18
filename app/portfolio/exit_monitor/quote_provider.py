"""Quote provider abstraction for T1 intraday exit monitor (ADR-033).

Production hierarchy:
  Live S1+  → KiteQuoteProvider  (real-time LTP via Kite REST ltp())
  Paper S0  → LastCloseProvider  (uses latest close from market_data as proxy)

The T1 monitor receives a QuoteProvider at construction; callers inject the
appropriate implementation. No LTP logic leaks into the monitor itself.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.repositories.market_data_repository import MarketDataRepository

logger = logging.getLogger(__name__)


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


class KiteQuoteProvider(QuoteProvider):
    """Live LTP via Kite Connect REST ltp() — used when intraday monitor is active.

    Calls kite.ltp(["NSE:SYMBOL"]) per stock_id. Results are NOT cached between
    calls so each get_ltp() returns a fresh quote — callers should batch positions
    through a single run() cycle rather than calling get_ltp() in a tight loop.

    Symbol resolution: stock_id → Stock.symbol (e.g. "TRENT.NS") → "NSE:TRENT"
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._symbol_cache: dict[UUID, str | None] = {}  # stock_id → "NSE:SYMBOL"
        self._kite = self._build_kite()

    @staticmethod
    def _build_kite():
        from app.core.config import get_settings
        from app.providers.kite import token_store

        settings = get_settings()
        try:
            from kiteconnect import KiteConnect  # type: ignore[import]
        except ImportError as exc:
            raise ImportError("kiteconnect package not installed") from exc

        # Inline DB session just for token lookup — we don't hold it open
        from app.db.session import get_db
        db_gen = get_db()
        token_db = next(db_gen)
        try:
            token = token_store.get_token(token_db) or settings.kite_access_token
        finally:
            token_db.close()

        if not token:
            raise RuntimeError("No Kite access token available — run kite_token_refresh.py first")

        kite = KiteConnect(api_key=settings.kite_api_key)
        kite.set_access_token(token)
        return kite

    def _to_kite_symbol(self, stock_id: UUID) -> str | None:
        """Resolve stock_id → NSE:SYMBOL, with per-instance cache."""
        if stock_id not in self._symbol_cache:
            from app.models.stock import Stock
            stock = self._db.scalar(select(Stock).where(Stock.id == stock_id))
            if stock is None:
                self._symbol_cache[stock_id] = None
            else:
                # "TRENT.NS" → "NSE:TRENT",  "TRENT.BO" → "BSE:TRENT"
                sym = stock.symbol
                if sym.endswith(".NS"):
                    self._symbol_cache[stock_id] = "NSE:" + sym[:-3]
                elif sym.endswith(".BO"):
                    self._symbol_cache[stock_id] = "BSE:" + sym[:-3]
                else:
                    self._symbol_cache[stock_id] = "NSE:" + sym
        return self._symbol_cache[stock_id]

    def get_ltp(self, stock_id: UUID) -> float | None:
        kite_sym = self._to_kite_symbol(stock_id)
        if kite_sym is None:
            return None
        try:
            result = self._kite.ltp([kite_sym])
            entry = result.get(kite_sym) or {}
            ltp = entry.get("last_price")
            return float(ltp) if ltp is not None else None
        except Exception as exc:
            logger.warning("KiteQuoteProvider.get_ltp failed for %s: %s", kite_sym, exc)
            return None
