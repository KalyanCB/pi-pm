from __future__ import annotations

from app.core.constants import (
    RANKING_STRATEGY_MOMENTUM_V1,
    RANKING_STRATEGY_MOMENTUM_V1_VERSION,
)
from app.core.exceptions import StrategyNotFoundError
from app.ranking.strategies.momentum_v1 import MomentumV1Strategy
from app.ranking.strategy import RankingStrategy


class RankingStrategyRegistry:
    def __init__(self) -> None:
        self._strategies: dict[tuple[str, str], RankingStrategy] = {}
        self.register(MomentumV1Strategy())

    def register(self, strategy: RankingStrategy) -> None:
        self._strategies[(strategy.name, strategy.version)] = strategy

    def get(self, name: str, version: str) -> RankingStrategy:
        strategy = self._strategies.get((name, version))
        if strategy is None:
            raise StrategyNotFoundError(f"Ranking strategy not found: {name}@{version}")
        return strategy

    def default(self) -> RankingStrategy:
        return self.get(RANKING_STRATEGY_MOMENTUM_V1, RANKING_STRATEGY_MOMENTUM_V1_VERSION)
