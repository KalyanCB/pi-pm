from __future__ import annotations

import bisect
from datetime import date
from uuid import UUID

from app.core.constants import MARKET_DATA_SOURCE_YAHOO
from app.db.repositories.market_data_repository import MarketDataRepository
from app.ranking.math_utils import PriceBar


class GlobalBarStore:
    """Load ALL market data for ALL stocks in ONE SQL query at replay/batch start.

    Rankings and validation then do zero DB queries for bars — all date filtering
    is in-memory bisect. ~32MB for 1000 stocks × 1348 days.

    Usage:
        store = GlobalBarStore.load(repo, stock_ids, end_date, source)
        cache = store.as_cache()   # drop-in MarketDataCache backed by this store
    """

    def __init__(self) -> None:
        # {stock_id: tuple[PriceBar, ...]} sorted by date ascending
        self._all_bars: dict[UUID, tuple[PriceBar, ...]] = {}
        # sorted date lists for bisect — parallel to _all_bars values
        self._dates: dict[UUID, list[date]] = {}

    @classmethod
    def load(
        cls,
        repo: MarketDataRepository,
        stock_ids: list[UUID],
        end_date: date,
        source: str,
        start_date: date | None = None,
    ) -> "GlobalBarStore":
        store = cls()
        rows_by_stock = repo.get_all_by_stock_ids_up_to_date(
            stock_ids, end_date=end_date, source=source, start_date=start_date
        )
        for stock_id, rows in rows_by_stock.items():
            bars = sorted(
                (
                    PriceBar(
                        date=row.date,
                        close=float(row.adj_close if row.adj_close is not None else row.close),
                        volume=row.volume,
                    )
                    for row in rows
                ),
                key=lambda b: b.date,
            )
            store._all_bars[stock_id] = tuple(bars)
            store._dates[stock_id] = [b.date for b in bars]
        return store

    def bars_up_to(self, stock_id: UUID, as_of_date: date) -> list[PriceBar]:
        """All bars with date <= as_of_date. O(log n) bisect, no DB."""
        bars = self._all_bars.get(stock_id)
        if not bars:
            return []
        dates = self._dates[stock_id]
        # bisect_right gives insertion point after all dates == as_of_date
        idx = bisect.bisect_right(dates, as_of_date)
        return list(bars[:idx])

    def as_cache(self, repo: MarketDataRepository | None = None) -> "MarketDataCache":
        """Return a MarketDataCache that delegates bar lookups to this store."""
        return _GlobalBackedCache(self, repo)


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
                    close=float(row.adj_close if row.adj_close is not None else row.close),
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
                    close=float(row.adj_close if row.adj_close is not None else row.close),
                    volume=row.volume,
                )
                for row in rows
            ]
            bars.sort(key=lambda bar: bar.date)
            self._bars[key] = tuple(bars)
        return list(self._bars[key])

    def bulk_preload(
        self,
        stock_ids: list[UUID],
        as_of_date: date,
        source: str = MARKET_DATA_SOURCE_YAHOO,
    ) -> None:
        """Fetch all stocks in a single query and populate the cache."""
        rows_by_stock = self._market_data_repo.get_all_by_stock_ids_up_to_date(
            stock_ids, end_date=as_of_date, source=source
        )
        for stock_id, rows in rows_by_stock.items():
            key = (stock_id, as_of_date, source)
            if key not in self._bars:
                bars = [
                    PriceBar(
                        date=row.date,
                        close=float(row.adj_close if row.adj_close is not None else row.close),
                        volume=row.volume,
                    )
                    for row in rows
                ]
                bars.sort(key=lambda bar: bar.date)
                self._bars[key] = tuple(bars)

    def bulk_preload_extended(
        self,
        stock_ids: list,
        through_date: date,
        source: str = MARKET_DATA_SOURCE_YAHOO,
        start_date: date | None = None,
    ) -> None:
        """Bulk preload for load_extended_series in one SQL query.

        start_date trims historical data we don't need (validation only needs
        bars from just before as_of_date through the forward window).
        """
        missing = [sid for sid in stock_ids
                   if (sid, through_date, source, "extended") not in self._bars]
        if not missing:
            return
        rows_by_stock = self._market_data_repo.get_all_by_stock_ids_up_to_date(
            missing, end_date=through_date, source=source, start_date=start_date
        )
        for stock_id in missing:
            key = (stock_id, through_date, source, "extended")
            rows = rows_by_stock.get(stock_id, [])
            bars = [
                PriceBar(
                    date=row.date,
                    close=float(row.adj_close if row.adj_close is not None else row.close),
                    volume=row.volume,
                )
                for row in rows
            ]
            bars.sort(key=lambda bar: bar.date)
            self._bars[key] = tuple(bars)

    def clear(self) -> None:
        self._bars.clear()


class _GlobalBackedCache(MarketDataCache):
    """MarketDataCache whose load_series / load_extended_series hit GlobalBarStore
    (zero DB round-trips). Falls back to DB for stocks not in the store."""

    def __init__(self, store: GlobalBarStore, repo: MarketDataRepository | None) -> None:
        # repo may be None if store covers everything
        super().__init__(repo)  # type: ignore[arg-type]
        self._store = store

    def load_series(self, stock_id: UUID, as_of_date: date, source: str = MARKET_DATA_SOURCE_YAHOO) -> list[PriceBar]:
        if stock_id in self._store._all_bars:
            return self._store.bars_up_to(stock_id, as_of_date)
        return super().load_series(stock_id, as_of_date, source)

    def load_extended_series(self, stock_id: UUID, through_date: date, source: str = MARKET_DATA_SOURCE_YAHOO) -> list[PriceBar]:
        if stock_id in self._store._all_bars:
            return self._store.bars_up_to(stock_id, through_date)
        return super().load_extended_series(stock_id, through_date, source)

    def bulk_preload(self, stock_ids, as_of_date, source=MARKET_DATA_SOURCE_YAHOO) -> None:
        pass  # store already has all bars in memory

    def bulk_preload_extended(self, stock_ids, through_date, source=MARKET_DATA_SOURCE_YAHOO, start_date=None) -> None:
        pass  # store already has all bars in memory
