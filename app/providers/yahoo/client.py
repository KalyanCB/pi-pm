from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

import yfinance as yf
from datetime import datetime as dt

from app.core.constants import IngestPeriod
from app.core.exceptions import InvalidSymbolError, ProviderError
from app.providers.yahoo.models import YahooOHLCVBar, YahooStockMetadata

logger = logging.getLogger(__name__)


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        if isinstance(value, float) and value != value:
            return None
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _infer_exchange(symbol: str, raw_exchange: str | None) -> str:
    if raw_exchange:
        return raw_exchange
    if symbol.endswith(".NS"):
        return "NSE"
    if symbol.endswith(".BO"):
        return "BSE"
    return "UNKNOWN"


class YahooFinanceProvider:
    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch_metadata(self, symbol: str) -> YahooStockMetadata:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
        except Exception as exc:
            logger.exception("Yahoo metadata fetch failed for %s", symbol)
            raise ProviderError(f"Yahoo metadata fetch failed for {symbol}") from exc

        name = info.get("longName") or info.get("shortName")
        if not name:
            raise InvalidSymbolError(f"No metadata found for symbol: {symbol}")

        return YahooStockMetadata(
            symbol=symbol,
            name=str(name),
            exchange=_infer_exchange(symbol, info.get("exchange")),
            sector=info.get("sector"),
            industry=info.get("industry"),
        )

    def fetch_history(self, symbol: str, period: IngestPeriod) -> list[YahooOHLCVBar]:
        try:
            ticker = yf.Ticker(symbol)
            frame = ticker.history(period=period.value, auto_adjust=False)
        except Exception as exc:
            logger.exception("Yahoo history fetch failed for %s", symbol)
            raise ProviderError(f"Yahoo history fetch failed for {symbol}") from exc

        if frame is None or frame.empty:
            return []

        bars: list[YahooOHLCVBar] = []
        for index, row in frame.iterrows():
            bar_date = index.date() if isinstance(index, datetime) else index.to_pydatetime().date()
            close = _to_decimal(row.get("Close"))
            if close is None:
                continue

            volume_raw = row.get("Volume")
            if volume_raw is not None and volume_raw == volume_raw:
                volume = int(volume_raw)
            else:
                volume = None

            bars.append(
                YahooOHLCVBar(
                    date=bar_date,
                    open=_to_decimal(row.get("Open")),
                    high=_to_decimal(row.get("High")),
                    low=_to_decimal(row.get("Low")),
                    close=close,
                    volume=volume,
                    adj_close=_to_decimal(row.get("Adj Close")),
                    dividend=_to_decimal(row.get("Dividends")) if "Dividends" in row else None,
                    split_factor=_to_decimal(row.get("Stock Splits"))
                    if "Stock Splits" in row
                    else None,
                )
            )

        return bars

    def fetch_history_since(
        self,
        symbol: str,
        start_date: date,
        end_date: date | None = None,
    ) -> list[YahooOHLCVBar]:
        end = end_date or datetime.now(UTC).date()
        if start_date > end:
            return []
        try:
            ticker = yf.Ticker(symbol)
            frame = ticker.history(
                start=start_date.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                auto_adjust=False,
            )
        except Exception as exc:
            logger.exception("Yahoo incremental history fetch failed for %s", symbol)
            raise ProviderError(f"Yahoo incremental history fetch failed for {symbol}") from exc

        if frame is None or frame.empty:
            return []

        bars: list[YahooOHLCVBar] = []
        for index, row in frame.iterrows():
            bar_date = index.date() if isinstance(index, dt) else index.to_pydatetime().date()
            if bar_date < start_date or bar_date > end:
                continue
            close = _to_decimal(row.get("Close"))
            if close is None:
                continue

            volume_raw = row.get("Volume")
            if volume_raw is not None and volume_raw == volume_raw:
                volume = int(volume_raw)
            else:
                volume = None

            bars.append(
                YahooOHLCVBar(
                    date=bar_date,
                    open=_to_decimal(row.get("Open")),
                    high=_to_decimal(row.get("High")),
                    low=_to_decimal(row.get("Low")),
                    close=close,
                    volume=volume,
                    adj_close=_to_decimal(row.get("Adj Close")),
                    dividend=_to_decimal(row.get("Dividends")) if "Dividends" in row else None,
                    split_factor=_to_decimal(row.get("Stock Splits"))
                    if "Stock Splits" in row
                    else None,
                )
            )

        return bars
