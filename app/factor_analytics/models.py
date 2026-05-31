from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class FactorObservation:
    ranking_run_id: UUID
    stock_id: UUID
    factor_name: str
    normalized_factor_value: Decimal
    factor_percentile: float
    forward_return: Decimal
    regime_label: str
    as_of_date: date


@dataclass(frozen=True)
class DailyFactorIC:
    factor_name: str
    ranking_run_id: UUID
    as_of_date: date
    regime_label: str
    dataset_split: str
    horizon: int
    ic_spearman: float | None
    sample_size: int


@dataclass(frozen=True)
class FactorMetricResult:
    factor_name: str
    strategy_name: str
    strategy_version: str
    universe_code: str
    horizon: int
    regime_label: str
    dataset_split: str
    ic_spearman: float | None
    ic_pearson: float | None
    hit_rate: float | None
    spread_contribution: float | None
    sample_size: int
    ranked_days: int
    regime_coverage_pct: float | None
    stability_score: float | None
    stability_label: str | None
    coverage_label: str | None
    bootstrap_ci_lower: float | None
    bootstrap_ci_upper: float | None
    p_value: float | None
    is_statistically_significant: bool
    confidence: str
    bootstrap_sample_count: int
    bootstrap_method: str
    holdout_start_date: date
    as_of_date_start: date
    as_of_date_end: date


@dataclass(frozen=True)
class TrainHoldoutDriftEntry:
    factor_name: str
    train_ic_spearman: float | None
    holdout_ic_spearman: float | None
    ic_drift: float | None
    stability_score: float | None
    regime_coverage_pct: float | None
    verdict: str
