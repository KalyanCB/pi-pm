from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.core.constants import MARKET_DATA_SOURCE_YAHOO
from app.db.repositories.market_data_repository import MarketDataRepository
from app.ranking.math_utils import PriceBar


class MarketDataCache:
    """Session-scoped bar cache shared between universe filtering and ranking.

    Sprint 3.1 introduces the abstraction only; Sprint 4 may add optimizations.
    """

    def __init__(self, market_data_repo: MarketDataRepository) -> None:
        self._market_data_repo = market_data_repo
        self._bars: dict[tuple, tuple[PriceBar, ...]] = {}

    def load_series(
        self,
        stock_id: UUID,
        as_of_date: date,
        source: str = MARKET_DATA_SOURCE_YAHOO,
    ) -> list[PriceBar]:
        key = (stock_id, as_of_date, source)
        if key not in self._bars:
            rows = self._market_data_repo.get_by_stock_and_date_range(
                stock_id,
                end_date=as_of_date,
                source=source,
            )
            bars = [
                PriceBar(
                    date=row.date,
                    close=Decimal(str(row.adj_close if row.adj_close is not None else row.close)),
                    volume=row.volume,
                )
                for row in rows
            ]
            bars.sort(key=lambda bar: bar.date)
            self._bars[key] = tuple(bars)
        return list(self._bars[key])

    def load_extended_series(
        self,
        stock_id: UUID,
        through_date: date,
        source: str = MARKET_DATA_SOURCE_YAHOO,
    ) -> list[PriceBar]:
        """Load all bars with date <= through_date (include forward window for validation)."""
        key = (stock_id, through_date, source, "extended")
        if key not in self._bars:
            rows = self._market_data_repo.get_by_stock_and_date_range(
                stock_id,
                end_date=through_date,
                source=source,
            )
            bars = [
                PriceBar(
                    date=row.date,
                    close=Decimal(str(row.adj_close if row.adj_close is not None else row.close)),
                    volume=row.volume,
                )
                for row in rows
            ]
            bars.sort(key=lambda bar: bar.date)
            self._bars[key] = tuple(bars)
        return list(self._bars[key])

    def clear(self) -> None:
        self._bars.clear()
