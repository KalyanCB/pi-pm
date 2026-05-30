from __future__ import annotations

from datetime import date

from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.market_data.cache import MarketDataCache
from app.universe.filter_engine import UniverseFilterEngine
from app.universe.models import TradableUniverse, UniverseFilterConfig


class UniverseFilterService:
    def __init__(
        self,
        universe_repo: UniverseRepository,
        market_data_repo: MarketDataRepository,
    ) -> None:
        self.universe_repo = universe_repo
        self.market_data_repo = market_data_repo

    def build_tradable_universe(
        self,
        as_of_date: date,
        config: UniverseFilterConfig,
        market_data_cache: MarketDataCache,
    ) -> TradableUniverse:
        engine = UniverseFilterEngine(self.universe_repo, market_data_cache)
        return engine.build_tradable_universe(as_of_date, config)
