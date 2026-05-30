from __future__ import annotations

from datetime import date
from uuid import UUID

from app.core.constants import MARKET_DATA_SOURCE_YAHOO
from app.db.repositories.market_data_repository import MarketDataRepository


class TradingCalendar:
    """Resolve trading days from stored market data (data-driven calendar)."""

    def __init__(self, market_data_repo: MarketDataRepository) -> None:
        self.market_data_repo = market_data_repo

    def trading_days_in_range(
        self,
        start_date: date,
        end_date: date,
        universe_stock_ids: list[UUID],
        benchmark_stock_id: UUID | None,
        source: str = MARKET_DATA_SOURCE_YAHOO,
    ) -> list[date]:
        if start_date > end_date:
            return []

        anchor_ids = [benchmark_stock_id] if benchmark_stock_id is not None else universe_stock_ids
        if not anchor_ids:
            return []

        days = self.market_data_repo.list_distinct_trading_dates(
            anchor_ids,
            start_date=start_date,
            end_date=end_date,
            source=source,
        )
        return sorted(day for day in days if start_date <= day <= end_date)
