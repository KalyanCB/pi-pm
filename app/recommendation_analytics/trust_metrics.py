"""Trust metrics — observation only, no feedback into conviction or engine.

Three dimensions:
1. Conviction Calibration  — do HIGH bands actually outperform LOW?
2. Recommendation Stability — how often do actions churn day-to-day?
3. Recommendation Reliability — how often are recommendations data-complete?
"""
from __future__ import annotations

from dataclasses import dataclass

from app.recommendation_analytics.calculator import (
    OutcomeRow,
    _safe_div,
    check_conviction_calibration,
    compute_conviction_breakdown,
)
from app.recommendation_analytics.dtos import (
    ConvictionCalibrationDTO,
    ReliabilityDTO,
    StabilityDTO,
    TrustMetricsDTO,
    OutcomeWindowDTO,
)


def compute_calibration(rows: list[OutcomeRow]) -> ConvictionCalibrationDTO:
    band_metrics = compute_conviction_breakdown(rows)
    is_calibrated, rho = check_conviction_calibration(band_metrics)

    actual_rates = {
        m.band: round(m.win_rate, 4) if m.win_rate is not None else None
        for m in band_metrics
        if m.band in ("EXCEPTIONAL", "HIGH", "MEDIUM", "LOW")
    }
    return ConvictionCalibrationDTO(
        expected_order=["EXCEPTIONAL", "HIGH", "MEDIUM", "LOW"],
        actual_win_rates={k: v for k, v in actual_rates.items() if v is not None},
        rank_correlation=rho,
        is_calibrated=is_calibrated,
    )


@dataclass
class _ActionHistory:
    symbol: str
    dates_actions: list[tuple]   # [(date, action), ...] sorted ascending


def compute_stability(action_history: list[_ActionHistory]) -> StabilityDTO:
    """Compute churn from daily action sequences per symbol.

    action_history: list of per-symbol sorted (date, action) pairs.
    """
    total_evaluated = 0
    total_changes = 0
    reversal_count = 0

    for entry in action_history:
        seq = entry.dates_actions
        if len(seq) < 2:
            total_evaluated += len(seq)
            continue
        total_evaluated += len(seq)
        actions = [a for _, a in seq]
        for i in range(1, len(actions)):
            if actions[i] != actions[i - 1]:
                total_changes += 1
        # Reversal: BUY → WATCH/REJECT → BUY within 3 sessions
        for i in range(len(actions) - 2):
            if (
                actions[i] == "BUY"
                and actions[i + 1] in ("WATCH", "REJECT")
                and actions[i + 2] == "BUY"
            ):
                reversal_count += 1

    churn_rate = _safe_div(total_changes, total_evaluated)
    stability_score = (1.0 - churn_rate) if churn_rate is not None else None

    return StabilityDTO(
        total_symbols_evaluated=total_evaluated,
        daily_action_changes=total_changes,
        churn_rate=round(churn_rate, 4) if churn_rate is not None else None,
        reversal_count=reversal_count,
        stability_score=round(stability_score, 4) if stability_score is not None else None,
    )


def compute_reliability(
    total_recommendations: int,
    completed_validation_count: int,
    insufficient_data_count: int,
) -> ReliabilityDTO:
    rate = _safe_div(completed_validation_count, total_recommendations)
    return ReliabilityDTO(
        total_recommendations=total_recommendations,
        with_completed_validation=completed_validation_count,
        with_insufficient_data=insufficient_data_count,
        reliability_rate=round(rate, 4) if rate is not None else None,
    )


def compute_trust_metrics(
    window: OutcomeWindowDTO,
    outcome_rows: list[OutcomeRow],
    action_history: list[_ActionHistory],
    total_recommendations: int,
    completed_validation_count: int,
    insufficient_data_count: int,
) -> TrustMetricsDTO:
    calibration = compute_calibration(outcome_rows)
    stability = compute_stability(action_history)
    reliability = compute_reliability(
        total_recommendations, completed_validation_count, insufficient_data_count
    )

    # Simple composite trust score (0–1): average of three normalised dimensions
    components = []
    if calibration.rank_correlation is not None:
        components.append(max(0.0, (calibration.rank_correlation + 1) / 2))  # -1..1 → 0..1
    if stability.stability_score is not None:
        components.append(stability.stability_score)
    if reliability.reliability_rate is not None:
        components.append(reliability.reliability_rate)

    overall = sum(components) / len(components) if components else None

    return TrustMetricsDTO(
        window=window,
        calibration=calibration,
        stability=stability,
        reliability=reliability,
        overall_trust_score=round(overall, 4) if overall is not None else None,
    )
