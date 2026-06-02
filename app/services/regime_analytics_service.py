from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.backtest.trading_calendar import TradingCalendar
from app.core.constants import MARKET_DATA_SOURCE_YAHOO

from app.core.config import Settings
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.db.repositories.stock_repository import StockRepository
from app.market_data.cache import MarketDataCache
from app.models.platform_traceability import RegimeHistory, StrategyRegimePerformance
from app.validation.regimes import classify_regime


@dataclass(frozen=True)
class RegimeHistoryBackfillResult:
    trading_days_attempted: int
    rows_written: int
    rows_skipped: int


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
        self.calendar = TradingCalendar(market_data_repo)

    def backfill_regime_history(
        self,
        *,
        start_date: date,
        end_date: date,
        benchmark_symbol: str | None = None,
    ) -> RegimeHistoryBackfillResult:
        """Populate regime_history for each benchmark trading day in [start_date, end_date]."""
        symbol = (benchmark_symbol or self.settings.ranking_default_benchmark).upper()
        benchmark_stock = self.stock_repo.get_by_symbol(symbol)
        if benchmark_stock is None:
            return RegimeHistoryBackfillResult(
                trading_days_attempted=0, rows_written=0, rows_skipped=0
            )

        trading_days = self.calendar.trading_days_in_range(
            start_date,
            end_date,
            universe_stock_ids=[],
            benchmark_stock_id=benchmark_stock.id,
            source=MARKET_DATA_SOURCE_YAHOO,
        )
        written = 0
        skipped = 0
        for as_of in trading_days:
            stored = self.compute_and_store_regime(as_of_date=as_of, benchmark_symbol=symbol)
            if stored is None:
                skipped += 1
            else:
                written += 1
        self.db.flush()
        return RegimeHistoryBackfillResult(
            trading_days_attempted=len(trading_days),
            rows_written=written,
            rows_skipped=skipped,
        )

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
