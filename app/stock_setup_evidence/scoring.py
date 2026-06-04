from __future__ import annotations

import math

from app.stock_setup_evidence.constants import REGIME_LABEL_ALL_REGIMES
from app.stock_setup_evidence.outcomes import RegimeAggregateMetrics

_REGIME_BUCKETS: tuple[str, ...] = (
    "BULL_LOW_VOL",
    "BULL_HIGH_VOL",
    "BEAR_LOW_VOL",
    "BEAR_HIGH_VOL",
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _ci_width_score(agg: RegimeAggregateMetrics) -> float:
    lower = agg.confidence_interval_95_lower_20d
    upper = agg.confidence_interval_95_upper_20d
    if lower is None or upper is None:
        return 0.5
    width = upper - lower
    return _clamp(1.0 - width / 0.50, 0.0, 1.0)


def _return_score(avg_return: float | None) -> float:
    if avg_return is None:
        return 0.0
    # Map roughly -15% .. +25% into 0..1
    return _clamp((avg_return + 0.15) / 0.40, 0.0, 1.0)


def _regime_consistency_score(by_regime: dict[str, RegimeAggregateMetrics]) -> float:
    win_rates: list[float] = []
    for label in _REGIME_BUCKETS:
        agg = by_regime.get(label)
        if agg is None or agg.sample_size < 3:
            continue
        if agg.win_rate_20d is None:
            continue
        win_rates.append(agg.win_rate_20d)
    if len(win_rates) < 2:
        return 0.5
    mean_wr = sum(win_rates) / len(win_rates)
    variance = sum((wr - mean_wr) ** 2 for wr in win_rates) / len(win_rates)
    spread = math.sqrt(variance)
    return _clamp(1.0 - spread / 0.45, 0.0, 1.0)


def compute_setup_evidence_score(
    metrics_by_regime: dict[str, RegimeAggregateMetrics],
    *,
    qualifying_matches: int,
) -> float:
    """
    Deterministic 0–100 evidence quality score (no LLM).

    Higher scores require adequate sample size, favorable win rate / return,
    narrow confidence intervals, and consistent performance across regimes.
    """
    if qualifying_matches <= 0:
        return 0.0

    all_agg = metrics_by_regime.get(REGIME_LABEL_ALL_REGIMES)
    if all_agg is None or all_agg.sample_size == 0:
        return _clamp(qualifying_matches * 1.5, 0.0, 15.0)

    n = all_agg.sample_size
    sample_score = _clamp(n / 25.0, 0.0, 1.0)
    win_score = all_agg.win_rate_20d if all_agg.win_rate_20d is not None else 0.0
    return_score = _return_score(all_agg.average_return_20d)
    ci_score = _ci_width_score(all_agg)
    consistency_score = _regime_consistency_score(metrics_by_regime)

    composite = (
        0.20 * sample_score
        + 0.25 * win_score
        + 0.25 * return_score
        + 0.15 * ci_score
        + 0.15 * consistency_score
    )

    # Penalize very small qualifying pools even if ALL_REGIMES looks ok.
    if qualifying_matches < 5:
        composite *= qualifying_matches / 5.0

    return round(_clamp(composite, 0.0, 1.0) * 100.0, 2)
