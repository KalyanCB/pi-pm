from __future__ import annotations

from sqlalchemy.orm import Session

from app.backtest.ranking_replayer import RankingReplayer
from app.backtest.trading_calendar import TradingCalendar
from app.core.config import Settings
from app.core.exceptions import BacktestError, NotFoundError
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.schemas.backtest import GenerateRankingsRequest
from app.services.ranking_service import RankingService


class BacktestService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        ranking_service: RankingService,
        universe_repo: UniverseRepository,
        stock_repo: StockRepository,
        market_data_repo: MarketDataRepository,
    ) -> None:
        self.db = db
        self.settings = settings
        self.ranking_service = ranking_service
        self.universe_repo = universe_repo
        self.stock_repo = stock_repo
        self.market_data_repo = market_data_repo
        self.trading_calendar = TradingCalendar(market_data_repo)
        self.replayer = RankingReplayer(ranking_service)

    def generate_rankings(self, request: GenerateRankingsRequest):
        universe_code = request.universe_code or self.settings.ranking_default_universe_code
        strategy_name = request.strategy_name or self.settings.ranking_default_strategy
        strategy_version = (
            request.strategy_version or self.settings.ranking_default_strategy_version
        )
        benchmark_symbol = (
            request.benchmark_symbol or self.settings.ranking_default_benchmark
        ).upper()
        source = (
            request.filter_config.market_data_source
            if request.filter_config is not None
            else self.settings.ranking_market_data_source
        )

        universe = self.universe_repo.get_by_code(universe_code)
        if universe is None:
            raise NotFoundError(f"Universe not found: {universe_code}")

        universe_stocks = self.universe_repo.list_stocks_in_universe(universe_code)
        universe_stock_ids = [stock.id for stock in universe_stocks]

        benchmark_stock = self.stock_repo.get_by_symbol(benchmark_symbol)
        benchmark_stock_id = benchmark_stock.id if benchmark_stock else None

        trading_days = self.trading_calendar.trading_days_in_range(
            request.start_date,
            request.end_date,
            universe_stock_ids,
            benchmark_stock_id,
            source=source,
        )
        if not trading_days:
            raise BacktestError(
                "No trading days found in range for the configured universe and benchmark"
            )

        return self.replayer.generate(
            request,
            trading_days,
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            benchmark_symbol=benchmark_symbol,
        )
