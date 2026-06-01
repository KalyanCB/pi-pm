from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.constants import MARKET_DATA_SOURCE_YAHOO
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.stock_repository import StockRepository
from app.ops.daily_batch.models import TradingDayResolution

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_MARKET_CLOSE = time(15, 35)


class TradingDayResolver:
    def __init__(
        self,
        db: Session,
        *,
        benchmark_symbol: str,
        market_close_time: time = DEFAULT_MARKET_CLOSE,
    ) -> None:
        self.stock_repo = StockRepository(db)
        self.market_data_repo = MarketDataRepository(db)
        self.benchmark_symbol = benchmark_symbol
        self.market_close_time = market_close_time

    def resolve(
        self,
        *,
        target_date: date | None = None,
        assume_session_done: bool = False,
        force: bool = False,
    ) -> TradingDayResolution:
        now_ist = datetime.now(IST)
        calendar_today = now_ist.date()

        if target_date is not None:
            latest = self._latest_benchmark_date()
            return TradingDayResolution(
                target_trading_day=target_date,
                calendar_today=calendar_today,
                session_complete=True,
                latest_benchmark_date=latest,
                resolution_reason="target_date_override",
            )

        latest_benchmark = self._latest_benchmark_date()
        session_complete = force or assume_session_done or (
            calendar_today.weekday() < 5 and now_ist.time() >= self.market_close_time
        )

        if latest_benchmark is None:
            if session_complete and calendar_today.weekday() < 5:
                target = calendar_today
                reason = "no_benchmark_data_assume_calendar"
            else:
                raise ValueError(f"No benchmark data for {self.benchmark_symbol}")
        elif session_complete and calendar_today.weekday() < 5:
            target = max(latest_benchmark, calendar_today - timedelta(days=0))
            if calendar_today > latest_benchmark:
                target = calendar_today
            else:
                target = latest_benchmark
            reason = "post_close_max_benchmark_or_today"
        else:
            target = latest_benchmark
            reason = "benchmark_latest_pre_close_or_weekend"

        return TradingDayResolution(
            target_trading_day=target,
            calendar_today=calendar_today,
            session_complete=session_complete,
            latest_benchmark_date=latest_benchmark,
            resolution_reason=reason,
        )

    def _latest_benchmark_date(self) -> date | None:
        stock = self.stock_repo.get_by_symbol(self.benchmark_symbol)
        if stock is None:
            return None
        latest = self.market_data_repo.get_latest_market_data(stock.id, source=MARKET_DATA_SOURCE_YAHOO)
        return latest.date if latest else None
