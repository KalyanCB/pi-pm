from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from app.universe.models import FilterDecision


@dataclass(frozen=True)
class FactorDefinition:
    name: str
    weight: Decimal


@dataclass(frozen=True)
class FactorScore:
    factor_name: str
    raw_value: Decimal | None
    normalized_value: Decimal | None
    weight: Decimal
    weighted_contribution: Decimal


@dataclass(frozen=True)
class RankedStock:
    stock_id: UUID
    symbol: str
    rank: int
    composite_score: Decimal
    factor_scores: tuple[FactorScore, ...]


@dataclass(frozen=True)
class RankingOutput:
    strategy_name: str
    strategy_version: str
    as_of_date: date
    universe_code: str
    benchmark_symbol: str
    normalization_method: str
    inputs_hash: str
    filter_config_hash: str
    ranked_stocks: tuple[RankedStock, ...]
    ranking_exclusions: tuple[FilterDecision, ...]
    exclusion_summary: dict[str, int]
    metadata: dict


def quantize_score(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def quantize_component(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
