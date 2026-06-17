"""Kite instrument token cache.

Downloads the NSE instruments CSV from Kite on first use (or when stale),
and provides symbol → instrument_token lookup.

Kite symbols are bare (e.g. "TRENT"), Pi-PM symbols have ".NS" suffix.
The cache is refreshed once per day (instruments change with new listings).
"""
from __future__ import annotations

import csv
import io
import logging
import threading
import time
from datetime import date

logger = logging.getLogger(__name__)

# Refresh the instruments list once per calendar day
_CACHE_TTL_SECONDS = 86_400

_lock = threading.Lock()
_cache: dict[str, int] = {}       # pipm_symbol → instrument_token
_loaded_date: date | None = None


def _strip_suffix(symbol: str) -> str:
    """TRENT.NS → TRENT  (BSE uses .BO but we only map NSE here)."""
    return symbol.removesuffix(".NS").removesuffix(".BO")


def load(kite) -> None:
    """Download and cache the instruments list from Kite.

    kite — an authenticated KiteConnect instance.
    """
    global _cache, _loaded_date
    with _lock:
        today = date.today()
        if _loaded_date == today and _cache:
            return
        logger.info("kite_instruments: downloading instrument list")
        instruments = kite.instruments("NSE")
        mapping: dict[str, int] = {}
        for row in instruments:
            token = row.get("instrument_token") or row.get("token")
            trading_symbol = row.get("tradingsymbol", "")
            if token and trading_symbol:
                pipm_symbol = f"{trading_symbol}.NS"
                mapping[pipm_symbol] = int(token)
        _cache = mapping
        _loaded_date = today
        logger.info("kite_instruments: cached %d NSE instruments", len(_cache))


def get_token(symbol: str) -> int | None:
    """Return the Kite instrument_token for a Pi-PM symbol (e.g. 'TRENT.NS')."""
    return _cache.get(symbol)


def ensure_loaded(kite) -> None:
    """Load the cache if it's empty or stale."""
    today = date.today()
    if _loaded_date != today or not _cache:
        load(kite)
