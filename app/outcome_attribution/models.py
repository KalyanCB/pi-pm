from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class OutcomeAttributionConfig:
    universe_code: str
    start_date: date
    end_date: date
    strategy_names: tuple[str, ...] = ("breakout_v1", "momentum_v1")
    strategy_version: str | None = None


@dataclass(frozen=True)
class StockObservation:
    run_id: UUID
    as_of_date: date
    strategy_name: str
    regime_label: str | None
    rank: int
    returns: dict[int, float | None]


@dataclass(frozen=True)
class RunBenchmark:
    run_id: UUID
    as_of_date: date
    benchmark_symbol: str
    returns: dict[int, float | None]


@dataclass(frozen=True)
class BucketMetrics:
    bucket: str
    horizon: int
    hit_rate: float | None
    average_return: float | None
    alpha: float | None
    sharpe: float | None
    max_drawdown: float | None
    run_count: int
    observation_count: int
    status: str


@dataclass(frozen=True)
class SegmentMetrics:
    strategy_name: str
    regime_label: str
    horizons: dict[int, dict[str, BucketMetrics]] = field(default_factory=dict)
    rank_bands: dict[int, dict[str, BucketMetrics]] = field(default_factory=dict)


@dataclass(frozen=True)
class OutcomeAttributionReport:
    config: OutcomeAttributionConfig
    ranked_run_count: int
    runs_with_forward_data: int
    segments: tuple[SegmentMetrics, ...]
    verdict: str
    verdict_summary: str
