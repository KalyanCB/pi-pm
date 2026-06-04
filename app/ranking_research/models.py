from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID

from app.outcome_attribution.models import BucketMetrics, OutcomeAttributionConfig


@dataclass(frozen=True)
class RankingResearchConfig(OutcomeAttributionConfig):
    """Same scope as outcome attribution; research-only analytics."""


@dataclass(frozen=True)
class EnrichedStockObservation:
    run_id: UUID
    as_of_date: date
    strategy_name: str
    regime_label: str | None
    stock_id: UUID
    rank: int
    score: float
    score_components: dict[str, Any] | None
    returns: dict[int, float | None]


@dataclass(frozen=True)
class PerRankMetrics:
    rank: int
    horizon: int
    metrics: BucketMetrics


@dataclass(frozen=True)
class MonotonicitySummary:
    horizon: int
    spearman_correlation: float | None
    inversion_count: int
    monotonic: bool
    top5_overconfident: bool
    notes: str


@dataclass(frozen=True)
class DecileMonotonicitySummary:
    horizon: int
    decile_alphas: dict[int, float]
    spearman_correlation: float | None
    inversion_count: int
    monotonic: bool


@dataclass(frozen=True)
class ScoreQuintileMetrics:
    quintile: int
    horizon: int
    hit_rate: float | None
    average_return: float | None
    alpha: float | None
    observation_count: int


@dataclass(frozen=True)
class CliffEvent:
    rank_from: int
    rank_to: int
    horizon: int
    alpha_jump: float


@dataclass(frozen=True)
class FactorReliabilityRow:
    factor_name: str
    horizon: int
    winner_mean_normalized: float | None
    loser_mean_normalized: float | None
    spread: float | None
    winner_count: int
    loser_count: int
    reliability_score: float | None


@dataclass(frozen=True)
class StrategyRankReliability:
    strategy_name: str
    regime_label: str
    per_rank: dict[int, dict[int, BucketMetrics]]
    monotonicity: dict[int, MonotonicitySummary]
    decile_monotonicity: dict[int, DecileMonotonicitySummary]
    score_quintiles: dict[int, tuple[ScoreQuintileMetrics, ...]]
    cliffs: tuple[CliffEvent, ...]
    noisy_ranks: tuple[int, ...]


@dataclass(frozen=True)
class FactorReliabilitySegment:
    strategy_name: str
    regime_label: str
    horizon: int
    rows: tuple[FactorReliabilityRow, ...]


@dataclass(frozen=True)
class RankReliabilityReport:
    config: RankingResearchConfig
    ranked_run_count: int
    runs_with_forward_data: int
    strategies: tuple[StrategyRankReliability, ...]
    regime_segments: tuple[StrategyRankReliability, ...]
    factor_segments: tuple[FactorReliabilitySegment, ...]


@dataclass(frozen=True)
class ScoreCompressionSegment:
    strategy_name: str
    regime_label: str
    per_bucket: dict[str, dict[int, BucketMetrics]]


@dataclass(frozen=True)
class ScoreCompressionBucket:
    horizon: int
    high_bucket: str
    low_bucket: str
    high_alpha: float
    low_alpha: float
    alpha_spread: float
    high_outperforms: bool


@dataclass(frozen=True)
class ScoreCompressionReport:
    segments: tuple[ScoreCompressionSegment, ...]


@dataclass(frozen=True)
class RootCauseHeadlines:
    why_top20_works: tuple[str, ...]
    why_rank_fails: tuple[str, ...]
    root_causes: tuple[str, ...]
    simplest_fix: tuple[str, ...]


@dataclass(frozen=True)
class PortfolioBacktestMetrics:
    label: str
    horizon: int
    hit_rate: float | None
    average_return: float | None
    alpha: float | None
    sharpe: float | None
    max_drawdown: float | None
    rank_return_correlation: float | None
    run_count: int
    observation_count: int


@dataclass(frozen=True)
class CalibratedRankingBacktestReport:
    config: RankingResearchConfig
    ranked_run_count: int
    production: tuple[PortfolioBacktestMetrics, ...]
    calibrated: tuple[PortfolioBacktestMetrics, ...]
    meets_monotonicity: bool
    meets_top5_alpha: bool
    meets_top10_alpha: bool
    meets_sharpe: bool
    verdict: str
    verdict_summary: str
