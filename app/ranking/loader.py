from __future__ import annotations

from datetime import date
from uuid import UUID

from app.core.constants import MARKET_DATA_SOURCE_YAHOO
from app.market_data.cache import MarketDataCache
from app.ranking.math_utils import PriceBar


class MarketDataLoader:
    def __init__(self, market_data_cache: MarketDataCache) -> None:
        self.market_data_cache = market_data_cache

    def load_series(
        self,
        stock_id: UUID,
        as_of_date: date,
        source: str = MARKET_DATA_SOURCE_YAHOO,
    ) -> list[PriceBar]:
        return self.market_data_cache.load_series(stock_id, as_of_date, source=source)

    def load_by_symbol(
        self,
        symbol: str,
        stock_id: UUID | None,
        as_of_date: date,
        source: str = MARKET_DATA_SOURCE_YAHOO,
    ) -> list[PriceBar]:
        if stock_id is None:
            return []
        return self.load_series(stock_id, as_of_date, source=source)
