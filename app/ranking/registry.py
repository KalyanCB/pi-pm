from __future__ import annotations

from app.core.constants import (
    RANKING_STRATEGY_MOMENTUM_V1,
    RANKING_STRATEGY_MOMENTUM_V1_VERSION,
)
from app.core.exceptions import StrategyNotFoundError
from app.ranking.strategies.breakout_v1 import BreakoutV1Strategy
from app.ranking.strategies.breakout_v2 import BreakoutV2Strategy
from app.ranking.strategies.breakout_v3 import (
    build_breakout_v3_broad_strategy,
    build_breakout_v3_def_strategy,
)
from app.ranking.strategies.low_vol_v1 import LowVolV1Strategy
from app.ranking.strategies.momentum_v1 import MomentumV1Strategy
from app.ranking.strategies.momentum_v2 import MomentumV2Strategy
from app.ranking.strategies.momentum_v3 import MomentumV3Strategy
from app.ranking.strategies.reversal_v1 import ReversalV1Strategy
from app.ranking.strategies.reversion_v2 import ReversionV2Strategy
from app.ranking.strategies.reversion_v3 import ReversionV3Strategy
from app.ranking.strategy import RankingStrategy


class RankingStrategyRegistry:
    def __init__(self) -> None:
        self._strategies: dict[tuple[str, str], RankingStrategy] = {}
        self.register(MomentumV1Strategy())
        self.register(BreakoutV1Strategy())
        self.register(LowVolV1Strategy())
        self.register(ReversalV1Strategy())
        # v2: anticipation-weighted, forward-IC-calibrated (2026-06)
        self.register(BreakoutV2Strategy())
        self.register(MomentumV2Strategy())
        self.register(ReversionV2Strategy())
        # v3: validated edges that need longer holds — deep-oversold bear reversion
        # (~20d) and classic 12mo momentum (~quarter)
        self.register(ReversionV3Strategy())
        self.register(MomentumV3Strategy())
        # v3 breakout: deterministic 2-state regime tilt (breadth-selected sleeves —
        # broad: proximity+momentum+efficiency; defensive: proximity+low_vol)
        self.register(build_breakout_v3_broad_strategy())
        self.register(build_breakout_v3_def_strategy())

    def register(self, strategy: RankingStrategy) -> None:
        self._strategies[(strategy.name, strategy.version)] = strategy

    def get(self, name: str, version: str) -> RankingStrategy:
        strategy = self._strategies.get((name, version))
        if strategy is None:
            raise StrategyNotFoundError(f"Ranking strategy not found: {name}@{version}")
        return strategy

    def default(self) -> RankingStrategy:
        return self.get(RANKING_STRATEGY_MOMENTUM_V1, RANKING_STRATEGY_MOMENTUM_V1_VERSION)
