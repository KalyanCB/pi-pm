"""Kite Connect LTP helpers — used by API endpoints for live price display."""
from __future__ import annotations

import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Kite ltp() accepts up to 500 instruments per call
_BATCH_SIZE = 500


def _symbol_to_kite(symbol: str) -> str:
    """'TRENT.NS' → 'NSE:TRENT',  'TRENT.BO' → 'BSE:TRENT'"""
    if symbol.endswith(".NS"):
        return "NSE:" + symbol[:-3]
    if symbol.endswith(".BO"):
        return "BSE:" + symbol[:-3]
    return "NSE:" + symbol


def bulk_ltp(symbols: list[str], db: Session) -> dict[str, float]:
    """Return {symbol: ltp} for all symbols that Kite can quote.

    Non-equity symbols (^NSEI etc.) are silently skipped.
    Returns an empty dict on any Kite error rather than raising.
    """
    from app.core.config import get_settings
    from app.providers.kite import token_store

    settings = get_settings()
    try:
        from kiteconnect import KiteConnect  # type: ignore[import]
    except ImportError:
        return {}

    token = token_store.get_token(db) or settings.kite_access_token
    if not token:
        return {}

    kite = KiteConnect(api_key=settings.kite_api_key)
    kite.set_access_token(token)

    # Filter out index symbols — not in Kite equity instruments
    tradeable = [s for s in symbols if not s.startswith("^")]
    kite_syms = [_symbol_to_kite(s) for s in tradeable]
    original = {_symbol_to_kite(s): s for s in tradeable}

    result: dict[str, float] = {}
    for i in range(0, len(kite_syms), _BATCH_SIZE):
        batch = kite_syms[i : i + _BATCH_SIZE]
        try:
            data = kite.ltp(batch)
            for kite_key, entry in data.items():
                ltp = entry.get("last_price")
                orig_sym = original.get(kite_key)
                if ltp is not None and orig_sym:
                    result[orig_sym] = float(ltp)
        except Exception as exc:
            logger.warning("bulk_ltp batch failed: %s", exc)

    return result
