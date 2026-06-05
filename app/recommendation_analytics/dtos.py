"""Analytics DTOs — used by REST API responses and mobile layer (M4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class OutcomeWindowDTO:
    """Date range and filter context for an analytics computation."""

    from_date: date | None
    to_date: date | None
    strategy_name: str | None
    window_sessions: int  # actual closed outcomes counted


@dataclass
class QualityMetricsDTO:
    recommendation_count: int
    closed_count: int
    open_count: int
    win_count: int
    loss_count: int
    breakeven_count: int
    win_rate: float | None  # closed only
    avg_gain_pct: float | None
    avg_loss_pct: float | None
    profit_factor: float | None
    avg_alpha_pct: float | None
    median_alpha_pct: float | None
    target_hit_rate: float | None
    stop_hit_rate: float | None
    avg_days_held: float | None


@dataclass
class ConvictionBandMetricsDTO:
    band: str
    count: int
    closed_count: int
    win_rate: float | None
    avg_alpha_pct: float | None
    profit_factor: float | None
    target_hit_rate: float | None


@dataclass
class ConvictionPerformanceDTO:
    window: OutcomeWindowDTO
    bands: list[ConvictionBandMetricsDTO]
    calibration_rank_correct: bool | None  # True if EXCEPTIONAL>HIGH>MEDIUM>LOW alpha
    calibration_note: str


@dataclass
class RegimeMetricsDTO:
    regime_label: str
    regime_posture: str | None
    recommendation_count: int
    closed_count: int
    win_rate: float | None
    avg_alpha_pct: float | None
    avg_return_pct: float | None


@dataclass
class RegimePerformanceDTO:
    window: OutcomeWindowDTO
    regimes: list[RegimeMetricsDTO]


@dataclass
class CommitteeAdvisoryMetricsDTO:
    advisory: str  # supportive / neutral / cautious / HIGH_CONCERN / unknown
    count: int
    win_rate: float | None
    avg_alpha_pct: float | None
    agreement_with_machine: float | None  # fraction where advisory matched machine BUY


@dataclass
class CommitteePerformanceDTO:
    window: OutcomeWindowDTO
    advisories: list[CommitteeAdvisoryMetricsDTO]
    note: str  # reminder that committee is advisory only


@dataclass
class ConvictionCalibrationDTO:
    expected_order: list[str]  # [EXCEPTIONAL, HIGH, MEDIUM, LOW]
    actual_win_rates: dict[str, float]  # band → win_rate
    rank_correlation: float | None  # Spearman rank corr of expected vs actual
    is_calibrated: bool | None  # rank_correlation >= 0.6


@dataclass
class StabilityDTO:
    total_symbols_evaluated: int
    daily_action_changes: int
    churn_rate: float | None  # changes / evaluations
    reversal_count: int  # BUY→WATCH→BUY in ≤3 sessions
    stability_score: float | None  # 1 - churn_rate


@dataclass
class ReliabilityDTO:
    total_recommendations: int
    with_completed_validation: int
    with_insufficient_data: int
    reliability_rate: float | None  # completed / total


@dataclass
class TrustMetricsDTO:
    window: OutcomeWindowDTO
    calibration: ConvictionCalibrationDTO
    stability: StabilityDTO
    reliability: ReliabilityDTO
    overall_trust_score: float | None  # simple composite 0-1


@dataclass
class SymbolAnalyticsDTO:
    symbol: str
    total_recommendations: int
    buy_count: int
    watch_count: int
    reject_count: int
    closed_outcomes: int
    win_rate: float | None
    avg_alpha_pct: float | None
    avg_conviction_score: float | None
    avg_days_held: float | None
    last_action: str | None
    last_recommendation_date: date | None
    why_not_recommended: list[str]  # latest reason_codes if not BUY


@dataclass
class RecommendationSummaryDTO:
    as_of_date: date | None
    window: OutcomeWindowDTO
    quality: QualityMetricsDTO
    top_conviction_buys: list[dict]  # [{symbol, conviction_score, band}, ...]
    exit_candidates: list[dict]  # [{symbol, exit_reason}, ...]
