from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.db.repositories.stock_repository import StockRepository
from app.market_data.cache import MarketDataCache
from app.models.platform_traceability import RegimeHistory, StrategyRegimePerformance
from app.validation.regimes import classify_regime


class RegimeAnalyticsService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        regime_repo: RegimeAnalyticsRepository,
        stock_repo: StockRepository,
        market_data_repo: MarketDataRepository,
    ) -> None:
        self.db = db
        self.settings = settings
        self.regime_repo = regime_repo
        self.stock_repo = stock_repo
        self.market_data_repo = market_data_repo

    def compute_and_store_regime(
        self,
        *,
        as_of_date: date,
        benchmark_symbol: str | None = None,
    ) -> RegimeHistory | None:
        symbol = (benchmark_symbol or self.settings.ranking_default_benchmark).upper()
        benchmark_stock = self.stock_repo.get_by_symbol(symbol)
        if benchmark_stock is None:
            return None

        cache = MarketDataCache(self.market_data_repo)
        bars = cache.load_extended_series(benchmark_stock.id, as_of_date)
        high_vol_threshold = Decimal(str(self.settings.validation_high_vol_threshold))
        regime = classify_regime(bars, as_of_date, high_vol_threshold)
        if regime is None:
            return None

        return self.regime_repo.upsert_regime(
            as_of_date=as_of_date,
            benchmark_symbol=symbol,
            trend_regime=regime.trend_regime,
            vol_regime=regime.vol_regime,
            regime_label=regime.regime_label,
        )

    def get_current_regime(
        self,
        *,
        benchmark_symbol: str | None = None,
        as_of_date: date | None = None,
    ) -> RegimeHistory | None:
        symbol = (benchmark_symbol or self.settings.ranking_default_benchmark).upper()
        stored = self.regime_repo.get_current(benchmark_symbol=symbol, as_of_date=as_of_date)
        if stored is not None:
            return stored
        if as_of_date is None:
            return None
        return self.compute_and_store_regime(as_of_date=as_of_date, benchmark_symbol=symbol)

    def refresh_strategy_regime_performance(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        horizon: int = 20,
    ) -> list[StrategyRegimePerformance]:
        return self.regime_repo.refresh_strategy_regime_performance(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            horizon=horizon,
        )

    def list_strategy_regime_performance(
        self,
        *,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
        horizon: int | None = None,
    ) -> list[StrategyRegimePerformance]:
        return self.regime_repo.list_strategy_regime_performance(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            horizon=horizon,
        )
