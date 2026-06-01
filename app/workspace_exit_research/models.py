from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class SignalEntry:
    ranking_run_id: UUID
    stock_id: UUID
    symbol: str
    entry_date: date
    entry_rank: int
    entry_score: Decimal
    entry_close: Decimal
    regime_label: str
    sector: str | None
    dataset_split: str
    return_5d: Decimal | None = None
    return_10d: Decimal | None = None
    return_20d: Decimal | None = None
    return_60d: Decimal | None = None


@dataclass(frozen=True)
class ExitSimulationResult:
    policy_family: str
    policy_variant: str
    period_return: Decimal | None
    holding_days: int
    exit_reason: str
    censored: bool = False


@dataclass(frozen=True)
class PolicyMetricResult:
    policy_family: str
    policy_variant: str
    strategy_name: str
    strategy_version: str
    universe_code: str
    regime_label: str
    dataset_split: str
    horizon: int
    sample_size: int
    mean_return: float | None
    median_return: float | None
    std_dev: float | None
    hit_rate: float | None
    avg_holding_days: float | None
    ci_lower: float | None
    ci_upper: float | None
    conclusion_status: str
    holdout_start_date: date
    as_of_date_start: date
    as_of_date_end: date


@dataclass(frozen=True)
class AlphaDecayPointResult:
    trading_day: int
    regime_label: str
    dataset_split: str
    sample_size: int
    mean_return: float | None
    cumulative_mean_return: float | None
    conclusion_status: str
