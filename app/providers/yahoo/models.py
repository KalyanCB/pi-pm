from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class YahooStockMetadata:
    symbol: str
    name: str
    exchange: str
    sector: str | None
    industry: str | None


@dataclass(frozen=True)
class YahooOHLCVBar:
    date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal
    volume: int | None
    adj_close: Decimal | None
    dividend: Decimal | None = None
    split_factor: Decimal | None = None
