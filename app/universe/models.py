from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class UniverseFilterConfig:
    universe_code: str
    min_history_days: int = 63
    min_avg_daily_traded_value: Decimal = Decimal("10000000")
    min_stock_price: Decimal = Decimal("50")
    require_data_status_active: bool = True
    require_stock_active: bool = True
    market_data_source: str = "yahoo"

    def to_canonical_dict(self) -> dict:
        return {
            "universe_code": self.universe_code,
            "min_history_days": self.min_history_days,
            "min_avg_daily_traded_value": str(self.min_avg_daily_traded_value),
            "min_stock_price": str(self.min_stock_price),
            "require_data_status_active": self.require_data_status_active,
            "require_stock_active": self.require_stock_active,
            "market_data_source": self.market_data_source,
        }

    def config_hash(self) -> str:
        payload = json.dumps(self.to_canonical_dict(), sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class StockSnapshot:
    stock_id: UUID
    symbol: str
    name: str
    exchange: str
    sector: str | None
    data_status: str
    is_active: bool


@dataclass(frozen=True)
class FilterDecision:
    stock_id: UUID
    symbol: str
    included: bool
    reason_code: str
    reason_detail: str
    metrics: dict[str, str | int | None]


@dataclass(frozen=True)
class TradableUniverse:
    universe_code: str
    as_of_date: date
    filter_config: UniverseFilterConfig
    filter_config_hash: str
    included: tuple[StockSnapshot, ...]
    excluded: tuple[FilterDecision, ...]
    exclusion_summary: dict[str, int]

    @property
    def stock_count(self) -> int:
        return len(self.included)
