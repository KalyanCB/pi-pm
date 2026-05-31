from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.core.constants import (
    DEFAULT_BENCHMARK_SYMBOL,
    DEFAULT_MIN_HISTORY_DAYS,
    NIFTY500_MIN_BREAKOUT_HISTORY_DAYS,
)
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository


@dataclass(frozen=True)
class UniverseCoverageReport:
    universe_code: str
    as_of_date: date
    membership_count: int
    stock_master_total: int
    stocks_with_any_data: int
    stocks_with_filter_history: int
    stocks_with_breakout_history: int
    data_status_breakdown: dict[str, int]
    benchmark_symbol: str
    benchmark_bar_count: int
    benchmark_available: bool
    sample_insufficient_symbols: list[str] = field(default_factory=list)


class UniverseCoverageService:
    def __init__(
        self,
        stock_repo: StockRepository,
        universe_repo: UniverseRepository,
        market_data_repo: MarketDataRepository,
    ) -> None:
        self.stock_repo = stock_repo
        self.universe_repo = universe_repo
        self.market_data_repo = market_data_repo

    def build_report(
        self,
        universe_code: str,
        as_of_date: date,
        *,
        min_filter_history_days: int = DEFAULT_MIN_HISTORY_DAYS,
        min_breakout_history_days: int = NIFTY500_MIN_BREAKOUT_HISTORY_DAYS,
        benchmark_symbol: str = DEFAULT_BENCHMARK_SYMBOL,
        insufficient_sample_limit: int = 20,
    ) -> UniverseCoverageReport:
        stocks = self.universe_repo.list_stocks_in_universe(universe_code)
        status_breakdown: dict[str, int] = {}
        with_any_data = 0
        with_filter_history = 0
        with_breakout_history = 0
        insufficient: list[str] = []

        for stock in stocks:
            status_breakdown[stock.data_status] = status_breakdown.get(stock.data_status, 0) + 1
            bar_count = self.market_data_repo.count_bars_on_or_before(stock.id, as_of_date)
            if bar_count == 0:
                if len(insufficient) < insufficient_sample_limit:
                    insufficient.append(stock.symbol)
                continue

            with_any_data += 1
            if bar_count >= min_filter_history_days:
                with_filter_history += 1
            if bar_count >= min_breakout_history_days:
                with_breakout_history += 1
            elif len(insufficient) < insufficient_sample_limit:
                insufficient.append(stock.symbol)

        benchmark = self.stock_repo.get_by_symbol(benchmark_symbol)
        benchmark_bar_count = 0
        if benchmark is not None:
            benchmark_bar_count = self.market_data_repo.count_bars_on_or_before(
                benchmark.id, as_of_date
            )

        return UniverseCoverageReport(
            universe_code=universe_code,
            as_of_date=as_of_date,
            membership_count=len(stocks),
            stock_master_total=len(self.stock_repo.list_stocks()),
            stocks_with_any_data=with_any_data,
            stocks_with_filter_history=with_filter_history,
            stocks_with_breakout_history=with_breakout_history,
            data_status_breakdown=status_breakdown,
            benchmark_symbol=benchmark_symbol,
            benchmark_bar_count=benchmark_bar_count,
            benchmark_available=benchmark_bar_count >= min_breakout_history_days,
            sample_insufficient_symbols=insufficient,
        )

    def report_to_dict(self, report: UniverseCoverageReport) -> dict:
        return {
            "universe_code": report.universe_code,
            "as_of_date": report.as_of_date.isoformat(),
            "membership_count": report.membership_count,
            "stock_master_total": report.stock_master_total,
            "stocks_with_any_data": report.stocks_with_any_data,
            "stocks_with_filter_history": report.stocks_with_filter_history,
            "stocks_with_breakout_history": report.stocks_with_breakout_history,
            "data_status_breakdown": report.data_status_breakdown,
            "benchmark_symbol": report.benchmark_symbol,
            "benchmark_bar_count": report.benchmark_bar_count,
            "benchmark_available": report.benchmark_available,
            "sample_insufficient_symbols": report.sample_insufficient_symbols,
        }
