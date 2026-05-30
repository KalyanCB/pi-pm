from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class RegimeClassification:
    trend_regime: str
    vol_regime: str
    regime_label: str


@dataclass(frozen=True)
class DecileBucket:
    decile: int
    count: int
    mean_return: Decimal | None
    median_return: Decimal | None


@dataclass(frozen=True)
class HitRateMetrics:
    top_vs_median_hit_rate: Decimal | None
    top_vs_bottom_hit_rate: Decimal | None
    rank_directional_hit_rate: Decimal | None


@dataclass(frozen=True)
class HorizonMetrics:
    horizon: int
    status: str
    ic_spearman: Decimal | None
    deciles: tuple[DecileBucket, ...]
    top_minus_bottom_spread: Decimal | None
    hit_rates: HitRateMetrics
    sample_size: int


@dataclass(frozen=True)
class StockForwardReturns:
    stock_id: UUID
    symbol: str
    score: Decimal
    rank: int
    returns: dict[int, Decimal | None]


@dataclass(frozen=True)
class ValidationReportData:
    ranking_run_id: UUID
    as_of_date: date
    status: str
    validation_hash: str | None
    regime: RegimeClassification | None
    horizon_metrics: dict[int, HorizonMetrics]
    sample_summary: dict[str, object]
