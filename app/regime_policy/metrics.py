from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal

from app.regime_policy.models import MetricWithSignificance
from app.validation.constants import MIN_IC_SAMPLE_SIZE
from app.validation.statistics import (
    _ScoredReturn,
    assign_deciles,
    compute_deciles,
    compute_full_horizon_metrics,
    spearman_ic,
)


@dataclass(frozen=True)
class DrawdownResult:
    max_drawdown: float | None
    cumulative_returns: list[float]


def compute_max_drawdown(daily_returns: list[float]) -> DrawdownResult:
    if not daily_returns:
        return DrawdownResult(max_drawdown=None, cumulative_returns=[])
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    series: list[float] = []
    for daily in daily_returns:
        cumulative += daily
        series.append(cumulative)
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > max_dd:
            max_dd = drawdown
    return DrawdownResult(max_drawdown=max_dd if daily_returns else None, cumulative_returns=series)


def compute_daily_portfolio_return(
    scored_returns: list[_ScoredReturn],
    size_multiplier: Decimal,
) -> Decimal | None:
    if not scored_returns:
        return None
    buckets = assign_deciles(scored_returns)
    top_items = buckets.get(1, [])
    if not top_items:
        return None
    avg = sum((item.forward_return for item in top_items), Decimal("0")) / Decimal(len(top_items))
    return avg * size_multiplier


def metrics_from_scored_returns(
    scored_returns: list[_ScoredReturn],
    *,
    horizon: int,
    ranked_days: int,
) -> dict:
    """Per-day metrics (small n). Uses full validation statistics."""
    full = compute_full_horizon_metrics(horizon, scored_returns, ranked_days=ranked_days)
    return {
        "ic_spearman": _decimal_to_float(full.rank_ic_spearman),
        "spread": _decimal_to_float(full.spread),
        "hit_rate": _decimal_to_float(full.hit_rate),
        "sample_count": full.sample_size,
        "ranked_days": full.ranked_days,
        "status": full.status,
    }


def compute_pooled_period_metrics(
    scored_returns: list[_ScoredReturn],
    *,
    horizon: int,
    ranked_days: int,
    daily_returns: list[float],
) -> dict:
    """Pooled train/holdout metrics without O(n²) directional hit rate.

    Used when aggregating many days × universe stocks. Skips rank_directional_hit_rate
    which would hang on large pooled samples (~200k+ rows).
    """
    if len(scored_returns) < MIN_IC_SAMPLE_SIZE:
        return {
            "ic_spearman": None,
            "spread": None,
            "hit_rate": None,
            "sample_count": len(scored_returns),
            "ranked_days": ranked_days,
            "status": "insufficient_data",
        }

    scores = [item.score for item in scored_returns]
    returns = [item.forward_return for item in scored_returns]
    rank_ic = spearman_ic(scores, returns)
    deciles = compute_deciles(scored_returns)
    top_decile = deciles[0].mean_return if deciles else None
    bottom_decile = deciles[-1].mean_return if deciles else None
    spread = None
    if top_decile is not None and bottom_decile is not None:
        spread = _decimal_to_float(top_decile - bottom_decile)

    hit_rate = _top_vs_median_hit_rate(scored_returns)

    return {
        "ic_spearman": _decimal_to_float(rank_ic),
        "spread": spread,
        "hit_rate": hit_rate,
        "sample_count": len(scored_returns),
        "ranked_days": ranked_days,
        "status": "ok" if rank_ic is not None or spread is not None else "insufficient_data",
    }


def _top_vs_median_hit_rate(scored_returns: list[_ScoredReturn]) -> float | None:
    if not scored_returns:
        return None
    buckets = assign_deciles(scored_returns)
    top_items = buckets.get(1, [])
    if not top_items:
        return None
    all_returns = [item.forward_return for item in scored_returns]
    sorted_returns = sorted(all_returns)
    mid = len(sorted_returns) // 2
    if len(sorted_returns) % 2 == 0:
        cross_median = (sorted_returns[mid - 1] + sorted_returns[mid]) / 2
    else:
        cross_median = sorted_returns[mid]
    hits = sum(1 for item in top_items if item.forward_return > cross_median)
    return float(Decimal(hits) / Decimal(len(top_items)))


def bootstrap_metric_ci(
    values: list[float],
    *,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> MetricWithSignificance:
    if not values:
        return MetricWithSignificance(value=None)
    rng = random.Random(seed)
    n = len(values)
    means: list[float] = []
    for _ in range(n_bootstrap):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / len(sample))
    means.sort()
    alpha = 1.0 - confidence
    lower_idx = int((alpha / 2) * n_bootstrap)
    upper_idx = int((1 - alpha / 2) * n_bootstrap) - 1
    lower_idx = max(0, min(lower_idx, n_bootstrap - 1))
    upper_idx = max(0, min(upper_idx, n_bootstrap - 1))
    point = sum(values) / len(values)
    return MetricWithSignificance(
        value=point,
        ci_lower=means[lower_idx],
        ci_upper=means[upper_idx],
    )


def compare_spread_significance(
    policy_daily_spreads: list[float],
    baseline_daily_spreads: list[float],
    *,
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> MetricWithSignificance:
    if not policy_daily_spreads or not baseline_daily_spreads:
        return MetricWithSignificance(value=None)
    paired_len = min(len(policy_daily_spreads), len(baseline_daily_spreads))
    if paired_len == 0:
        return MetricWithSignificance(value=None)
    diffs = [
        policy_daily_spreads[i] - baseline_daily_spreads[i]
        for i in range(paired_len)
    ]
    point = sum(diffs) / len(diffs)
    rng = random.Random(seed)
    boot_diffs: list[float] = []
    for _ in range(n_bootstrap):
        sample = [diffs[rng.randrange(len(diffs))] for _ in range(len(diffs))]
        boot_diffs.append(sum(sample) / len(sample))
    boot_diffs.sort()
    lower_idx = int(0.025 * n_bootstrap)
    upper_idx = int(0.975 * n_bootstrap) - 1
    p_value = sum(1 for d in boot_diffs if d <= 0) / n_bootstrap
    significant = p_value < 0.05 and point > 0
    return MetricWithSignificance(
        value=point,
        ci_lower=boot_diffs[max(0, lower_idx)],
        ci_upper=boot_diffs[min(n_bootstrap - 1, upper_idx)],
        p_value=round(p_value, 6),
        is_statistically_significant=significant,
    )


def confidence_label(
    *,
    sample_count: int,
    is_significant: bool | None,
    ranked_days: int,
) -> str:
    if sample_count < 30 or ranked_days < 10:
        return "low"
    if is_significant and sample_count >= 50 and ranked_days >= 20:
        return "high"
    if is_significant:
        return "medium"
    return "low"


def build_research_findings(
    *,
    policy_type: str,
    baseline_spread: float | None,
    policy_spread: float | None,
    sample_count: int,
    ranked_days: int,
    spread_significance: MetricWithSignificance | None,
) -> dict:
    improvement = None
    if baseline_spread is not None and policy_spread is not None:
        improvement = round(policy_spread - baseline_spread, 8)
    is_sig = spread_significance.is_statistically_significant if spread_significance else False
    confidence = confidence_label(
        sample_count=sample_count,
        is_significant=is_sig,
        ranked_days=ranked_days,
    )
    recommendation = "continue_research"
    if (
        is_sig
        and improvement is not None
        and improvement > 0
        and confidence in {"medium", "high"}
    ):
        recommendation = "promote_to_next_research_stage"
    elif improvement is not None and improvement <= 0:
        recommendation = "reject_policy"
    return {
        "policy": policy_type,
        "baseline_spread": baseline_spread,
        "policy_spread": policy_spread,
        "improvement": improvement,
        "sample_count": sample_count,
        "ranked_days": ranked_days,
        "confidence": confidence,
        "recommendation": recommendation,
        "is_statistically_significant": is_sig,
        "spread_p_value": spread_significance.p_value if spread_significance else None,
        "spread_ci_lower": spread_significance.ci_lower if spread_significance else None,
        "spread_ci_upper": spread_significance.ci_upper if spread_significance else None,
    }


def _decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)
