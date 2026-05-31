from __future__ import annotations

import logging
import random
from decimal import Decimal
from uuid import UUID

from app.factor_analytics.constants import (
    BOOTSTRAP_CONFIDENCE,
    BOOTSTRAP_METHOD,
    BOOTSTRAP_SAMPLE_COUNT,
    BOOTSTRAP_SEED,
    CONFIDENCE_LOW_MAX_SAMPLE,
    CONFIDENCE_MEDIUM_MIN_SAMPLE,
    COVERAGE_LOW_THRESHOLD,
    COVERAGE_SPARSE_THRESHOLD,
    MIN_DAILY_IC_SAMPLE_SIZE,
    MIN_FACTOR_SAMPLE_SIZE,
    STABILITY_MODERATE_THRESHOLD,
    STABILITY_STABLE_THRESHOLD,
)
from app.factor_analytics.models import DailyFactorIC, FactorMetricResult, FactorObservation
from app.validation.statistics import _ScoredReturn, assign_deciles, pearson_ic, spearman_ic

logger = logging.getLogger(__name__)


def stability_label(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= STABILITY_STABLE_THRESHOLD:
        return "stable"
    if score >= STABILITY_MODERATE_THRESHOLD:
        return "moderate"
    return "unstable"


def coverage_label(pct: float | None) -> str | None:
    if pct is None:
        return None
    if pct < COVERAGE_SPARSE_THRESHOLD:
        return "sparse_regime"
    if pct <= COVERAGE_LOW_THRESHOLD:
        return "low_coverage"
    return "adequate_coverage"


def compute_stability_score(daily_ics: list[float]) -> float | None:
    if not daily_ics:
        return None
    positives = sum(1 for ic in daily_ics if ic > 0)
    return positives / len(daily_ics)


def compute_regime_coverage_pct(ranked_days_in_regime: int, total_ranked_days: int) -> float | None:
    if total_ranked_days <= 0:
        return None
    return ranked_days_in_regime / total_ranked_days


def bootstrap_ic_significance(
    daily_ics: list[float],
    *,
    n_bootstrap: int = BOOTSTRAP_SAMPLE_COUNT,
    confidence: float = BOOTSTRAP_CONFIDENCE,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float | None, float | None, float | None, float | None, bool]:
    if not daily_ics:
        return None, None, None, None, False
    rng = random.Random(seed)
    n = len(daily_ics)
    means: list[float] = []
    for _ in range(n_bootstrap):
        sample = [daily_ics[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / len(sample))
    means.sort()
    alpha = 1.0 - confidence
    lower_idx = int((alpha / 2) * n_bootstrap)
    upper_idx = int((1 - alpha / 2) * n_bootstrap) - 1
    lower_idx = max(0, min(lower_idx, n_bootstrap - 1))
    upper_idx = max(0, min(upper_idx, n_bootstrap - 1))
    point = sum(daily_ics) / len(daily_ics)
    p_value = sum(1 for m in means if m <= 0) / n_bootstrap
    significant = p_value < 0.05 and point > 0
    return point, means[lower_idx], means[upper_idx], p_value, significant


def _confidence_label(sample_size: int, is_significant: bool) -> str:
    if sample_size < MIN_FACTOR_SAMPLE_SIZE:
        return "low"
    if sample_size <= CONFIDENCE_LOW_MAX_SAMPLE:
        return "low"
    if is_significant and sample_size >= CONFIDENCE_MEDIUM_MIN_SAMPLE:
        return "high"
    if is_significant:
        return "medium"
    return "low"


def compute_daily_ic(
    observations: list[FactorObservation],
) -> float | None:
    if len(observations) < MIN_DAILY_IC_SAMPLE_SIZE:
        return None
    scores = [obs.normalized_factor_value for obs in observations]
    returns = [obs.forward_return for obs in observations]
    ic = spearman_ic(scores, returns)
    return float(ic) if ic is not None else None


def compute_hit_rate(observations: list[FactorObservation]) -> float | None:
    if len(observations) < MIN_FACTOR_SAMPLE_SIZE:
        return None
    scored = [
        _ScoredReturn(
            symbol=str(obs.stock_id),
            score=obs.normalized_factor_value,
            rank=0,
            forward_return=obs.forward_return,
        )
        for obs in observations
    ]
    buckets = assign_deciles(scored)
    top_items = buckets.get(1, [])
    if not top_items:
        return None
    all_returns = sorted(item.forward_return for item in scored)
    mid = len(all_returns) // 2
    if len(all_returns) % 2 == 0:
        cross_median = (all_returns[mid - 1] + all_returns[mid]) / 2
    else:
        cross_median = all_returns[mid]
    hits = sum(1 for item in top_items if item.forward_return > cross_median)
    return hits / len(top_items)


def compute_spread_contribution(observations: list[FactorObservation]) -> float | None:
    if len(observations) < MIN_FACTOR_SAMPLE_SIZE:
        return None
    scored = [
        _ScoredReturn(
            symbol=str(obs.stock_id),
            score=obs.normalized_factor_value,
            rank=0,
            forward_return=obs.forward_return,
        )
        for obs in observations
    ]
    buckets = assign_deciles(scored)
    top_items = buckets.get(1, [])
    bottom_items = buckets.get(max(buckets.keys()), [])
    if not top_items or not bottom_items:
        return None
    top_mean = sum((item.forward_return for item in top_items), Decimal("0")) / Decimal(
        len(top_items)
    )
    bottom_mean = sum((item.forward_return for item in bottom_items), Decimal("0")) / Decimal(
        len(bottom_items)
    )
    return float(top_mean - bottom_mean)


class FactorMetricsEngine:
    def build_daily_metrics(
        self,
        observations: list[FactorObservation],
        *,
        horizon: int,
        holdout_start_date,
    ) -> list[DailyFactorIC]:
        from app.factor_analytics.window import split_dataset

        grouped: dict[tuple[str, UUID, date, str], list[FactorObservation]] = {}
        for obs in observations:
            key = (obs.factor_name, obs.ranking_run_id, obs.as_of_date, obs.regime_label)
            grouped.setdefault(key, []).append(obs)

        daily_rows: list[DailyFactorIC] = []
        for (factor_name, run_id, as_of, regime), group in grouped.items():
            ic = compute_daily_ic(group)
            daily_rows.append(
                DailyFactorIC(
                    factor_name=factor_name,
                    ranking_run_id=run_id,
                    as_of_date=as_of,
                    regime_label=regime,
                    dataset_split=split_dataset(as_of, holdout_start_date),
                    horizon=horizon,
                    ic_spearman=ic,
                    sample_size=len(group),
                )
            )
        return daily_rows

    def aggregate_metric(
        self,
        *,
        factor_name: str,
        strategy_name: str,
        strategy_version: str,
        universe_code: str,
        horizon: int,
        regime_label: str,
        dataset_split: str,
        observations: list[FactorObservation],
        daily_ics: list[float],
        ranked_days_in_regime: int,
        total_ranked_days_in_split: int,
        holdout_start_date,
        as_of_date_start,
        as_of_date_end,
    ) -> FactorMetricResult | None:
        if len(observations) < MIN_FACTOR_SAMPLE_SIZE:
            return None

        scores = [obs.normalized_factor_value for obs in observations]
        returns = [obs.forward_return for obs in observations]
        ic_spearman = spearman_ic(scores, returns)
        ic_pearson = pearson_ic(scores, returns)

        stab_score = compute_stability_score(daily_ics)
        cov_pct = compute_regime_coverage_pct(ranked_days_in_regime, total_ranked_days_in_split)

        boot_point, ci_lower, ci_upper, p_value, is_sig = bootstrap_ic_significance(daily_ics)

        return FactorMetricResult(
            factor_name=factor_name,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            horizon=horizon,
            regime_label=regime_label,
            dataset_split=dataset_split,
            ic_spearman=float(ic_spearman) if ic_spearman is not None else None,
            ic_pearson=float(ic_pearson) if ic_pearson is not None else None,
            hit_rate=compute_hit_rate(observations),
            spread_contribution=compute_spread_contribution(observations),
            sample_size=len(observations),
            ranked_days=ranked_days_in_regime,
            regime_coverage_pct=cov_pct,
            stability_score=stab_score,
            stability_label=stability_label(stab_score),
            coverage_label=coverage_label(cov_pct),
            bootstrap_ci_lower=ci_lower,
            bootstrap_ci_upper=ci_upper,
            p_value=p_value,
            is_statistically_significant=is_sig,
            confidence=_confidence_label(len(observations), is_sig),
            bootstrap_sample_count=BOOTSTRAP_SAMPLE_COUNT,
            bootstrap_method=BOOTSTRAP_METHOD,
            holdout_start_date=holdout_start_date,
            as_of_date_start=as_of_date_start,
            as_of_date_end=as_of_date_end,
        )
