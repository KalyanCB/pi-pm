"""Kite Connect provider — drop-in replacement for YahooFinanceProvider.

Implements the same interface:
  fetch_metadata(symbol)        → YahooStockMetadata
  fetch_history(symbol, period) → list[YahooOHLCVBar]
  fetch_history_since(symbol, start_date, end_date) → list[YahooOHLCVBar]
  fetch_fundamentals(symbol)    → dict   (delegated to yfinance; Kite has none)
  fetch_news(symbol, max_items) → dict   (delegated to yfinance; Kite has none)

Access token must be set before use:
  - Set KITE_ACCESS_TOKEN in .env, OR
  - Complete the OAuth flow via GET /api/v1/ops/kite/login → callback saves to DB.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from app.core.constants import IngestPeriod
from app.core.exceptions import InvalidSymbolError, ProviderError
from app.providers.yahoo.models import YahooOHLCVBar, YahooStockMetadata

logger = logging.getLogger(__name__)

# Kite historical_data max date range per request (days)
_MAX_DAYS_PER_CALL = 365
# Throttle: Kite allows 3 req/sec on historical API
_MIN_INTERVAL_SEC = 0.34


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        d = Decimal(str(value))
        return None if d != d else d   # NaN guard
    except (InvalidOperation, ValueError, TypeError):
        return None


def _period_to_days(period: IngestPeriod) -> int:
    mapping = {
        IngestPeriod.ONE_DAY: 1,
        IngestPeriod.FIVE_DAYS: 5,
        IngestPeriod.ONE_MONTH: 30,
        IngestPeriod.THREE_MONTHS: 91,
        IngestPeriod.SIX_MONTHS: 183,
        IngestPeriod.ONE_YEAR: 365,
        IngestPeriod.TWO_YEARS: 730,
        IngestPeriod.FIVE_YEARS: 1825,
        IngestPeriod.TEN_YEARS: 3650,
        IngestPeriod.MAX: 3650,
    }
    return mapping.get(period, 365)


class KiteConnectProvider:
    """Wraps kiteconnect.KiteConnect for OHLCV ingestion.

    Fundamentals and news are transparently delegated to the Yahoo provider
    because Kite does not offer that data.
    """

    def __init__(self, api_key: str, access_token: str) -> None:
        try:
            from kiteconnect import KiteConnect  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "kiteconnect is not installed. Add it with: uv add kiteconnect"
            ) from exc

        self._kite = KiteConnect(api_key=api_key)
        self._kite.set_access_token(access_token)
        self._last_call: float = 0.0

        from app.providers.kite import instruments
        instruments.ensure_loaded(self._kite)

        # Lazy Yahoo fallback for fundamentals + news
        self._yahoo = None

    # ── public helpers ────────────────────────────────────────────────────────

    @property
    def kite(self):
        return self._kite

    def generate_login_url(self) -> str:
        return self._kite.login_url()

    def complete_login(self, request_token: str) -> str:
        """Exchange request_token for access_token. Returns the access_token."""
        from app.core.config import get_settings
        settings = get_settings()
        session = self._kite.generate_session(request_token, api_secret=settings.kite_api_secret)
        access_token = session["access_token"]
        self._kite.set_access_token(access_token)
        return access_token

    # ── interface ─────────────────────────────────────────────────────────────

    def fetch_metadata(self, symbol: str) -> YahooStockMetadata:
        """Fetch stock metadata. Kite instruments list is the source."""
        if symbol.startswith("^"):
            return self._get_yahoo().fetch_metadata(symbol)
        from app.providers.kite import instruments
        instruments.ensure_loaded(self._kite)
        token = instruments.get_token(symbol)
        if token is None:
            raise InvalidSymbolError(f"Symbol not found in Kite NSE instruments: {symbol}")

        # Basic metadata from the instruments list
        bare = symbol.removesuffix(".NS").removesuffix(".BO")
        exchange = "NSE" if symbol.endswith(".NS") else "BSE"

        # Enrich name from Yahoo fallback (one-time, non-critical)
        name = bare
        try:
            yahoo = self._get_yahoo()
            meta = yahoo.fetch_metadata(symbol)
            name = meta.name
            sector = meta.sector
            industry = meta.industry
        except Exception:
            sector = None
            industry = None

        return YahooStockMetadata(
            symbol=symbol,
            name=name,
            exchange=exchange,
            sector=sector,
            industry=industry,
        )

    def fetch_history(self, symbol: str, period: IngestPeriod) -> list[YahooOHLCVBar]:
        if symbol.startswith("^"):
            return self._get_yahoo().fetch_history(symbol, period)
        days = _period_to_days(period)
        end = datetime.now(UTC).date()
        start = end - timedelta(days=days)
        return self.fetch_history_since(symbol, start, end)

    def fetch_history_since(
        self,
        symbol: str,
        start_date: date,
        end_date: date | None = None,
    ) -> list[YahooOHLCVBar]:
        # Index symbols (^NSEI, ^BSESN …) are not in Kite equity instruments
        if symbol.startswith("^"):
            return self._get_yahoo().fetch_history_since(symbol, start_date, end_date)

        from app.providers.kite import instruments
        instruments.ensure_loaded(self._kite)

        token = instruments.get_token(symbol)
        if token is None:
            raise InvalidSymbolError(f"Symbol not found in Kite NSE instruments: {symbol}")

        end = end_date or datetime.now(UTC).date()
        if start_date > end:
            return []

        bars: list[YahooOHLCVBar] = []
        cursor = start_date
        while cursor <= end:
            chunk_end = min(cursor + timedelta(days=_MAX_DAYS_PER_CALL - 1), end)
            bars.extend(self._fetch_chunk(token, symbol, cursor, chunk_end))
            cursor = chunk_end + timedelta(days=1)

        return bars

    def fetch_fundamentals(self, symbol: str) -> dict:
        return self._get_yahoo().fetch_fundamentals(symbol)

    def fetch_news(self, symbol: str, max_items: int = 10) -> dict:
        return self._get_yahoo().fetch_news(symbol, max_items)

    # ── internals ─────────────────────────────────────────────────────────────

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < _MIN_INTERVAL_SEC:
            time.sleep(_MIN_INTERVAL_SEC - elapsed)
        self._last_call = time.monotonic()

    def _fetch_chunk(
        self,
        instrument_token: int,
        symbol: str,
        from_date: date,
        to_date: date,
    ) -> list[YahooOHLCVBar]:
        self._throttle()
        try:
            records = self._kite.historical_data(
                instrument_token,
                from_date=datetime(from_date.year, from_date.month, from_date.day),
                to_date=datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59),
                interval="day",
            )
        except Exception as exc:
            logger.exception("Kite historical_data failed for %s (%d)", symbol, instrument_token)
            raise ProviderError(f"Kite fetch failed for {symbol}") from exc

        bars: list[YahooOHLCVBar] = []
        for r in records:
            bar_date = r["date"].date() if isinstance(r["date"], datetime) else r["date"]
            close = _to_decimal(r.get("close"))
            if close is None:
                continue
            bars.append(
                YahooOHLCVBar(
                    date=bar_date,
                    open=_to_decimal(r.get("open")),
                    high=_to_decimal(r.get("high")),
                    low=_to_decimal(r.get("low")),
                    close=close,
                    volume=int(r["volume"]) if r.get("volume") is not None else None,
                    adj_close=close,   # Kite provides adjusted prices by default
                    dividend=None,
                    split_factor=None,
                )
            )
        return bars

    def _get_yahoo(self):
        if self._yahoo is None:
            from app.providers.yahoo.client import YahooFinanceProvider
            self._yahoo = YahooFinanceProvider()
        return self._yahoo
