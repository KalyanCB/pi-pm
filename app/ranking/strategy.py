from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.ranking.math_utils import PriceBar
from app.ranking.models import FactorScore
from app.universe.models import StockSnapshot


@dataclass(frozen=True)
class StrategyRequirements:
    required_history_days: int


class RankingStrategy(Protocol):
    name: str
    version: str

    def requirements(self) -> StrategyRequirements: ...

    def compute_raw_factors(
        self,
        stock: StockSnapshot,
        price_series: list[PriceBar],
        benchmark_series: list[PriceBar] | None,
        as_of_date: date,
    ) -> dict[str, Decimal | None]: ...

    def base_weights(self) -> dict[str, Decimal]: ...

    def factor_names(self) -> tuple[str, ...]: ...

    def build_factor_scores(
        self,
        raw_factors: dict[str, Decimal | None],
        normalized_factors: dict[str, Decimal],
        effective_weights: dict[str, Decimal],
    ) -> list[FactorScore]: ...

    def composite_score(self, factor_scores: list[FactorScore]) -> Decimal: ...
