from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.core.constants import RANKING_STRATEGY_BREAKOUT_V1, RANKING_STRATEGY_MOMENTUM_V1
from app.ranking.math_utils import PriceBar
from app.ranking.strategies.breakout_v1 import BreakoutV1Strategy
from app.ranking.strategies.momentum_v1 import MomentumV1Strategy
from app.universe.models import StockSnapshot


class _RawFactorStrategy(Protocol):
    def factor_names(self) -> tuple[str, ...]: ...

    def compute_raw_factors(
        self,
        stock: StockSnapshot,
        price_series: list[PriceBar],
        benchmark_series: list[PriceBar] | None,
        as_of_date: date,
    ) -> dict[str, Decimal | None]: ...


@dataclass(frozen=True)
class SeeStrategyConfig:
    strategy_name: str
    factor_names: tuple[str, ...]
    strategy: _RawFactorStrategy


_BREAKOUT = BreakoutV1Strategy()
_MOMENTUM = MomentumV1Strategy()

_STRATEGY_BY_NAME: dict[str, SeeStrategyConfig] = {
    RANKING_STRATEGY_BREAKOUT_V1: SeeStrategyConfig(
        RANKING_STRATEGY_BREAKOUT_V1,
        _BREAKOUT.factor_names(),
        _BREAKOUT,
    ),
    RANKING_STRATEGY_MOMENTUM_V1: SeeStrategyConfig(
        RANKING_STRATEGY_MOMENTUM_V1,
        _MOMENTUM.factor_names(),
        _MOMENTUM,
    ),
}


def resolve_see_strategy(strategy_name: str) -> SeeStrategyConfig:
    config = _STRATEGY_BY_NAME.get(strategy_name)
    if config is None:
        raise ValueError(f"Unsupported strategy for SEE: {strategy_name}")
    return config
