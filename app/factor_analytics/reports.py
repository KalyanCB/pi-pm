from __future__ import annotations

from app.factor_analytics.constants import (
    DATASET_SPLIT_HOLDOUT,
    DRIFT_OVERFIT_HOLDOUT_IC,
    DRIFT_OVERFIT_TRAIN_IC,
)
from app.factor_analytics.models import FactorMetricResult, TrainHoldoutDriftEntry
from app.models.factor_analytics import FactorPerformanceMetric


def metric_to_dict(metric: FactorPerformanceMetric) -> dict:
    return {
        "id": str(metric.id),
        "factor_name": metric.factor_name,
        "strategy_name": metric.strategy_name,
        "strategy_version": metric.strategy_version,
        "universe_code": metric.universe_code,
        "horizon": metric.horizon,
        "regime_label": metric.regime_label,
        "dataset_split": metric.dataset_split,
        "ic_spearman": float(metric.ic_spearman) if metric.ic_spearman is not None else None,
        "ic_pearson": float(metric.ic_pearson) if metric.ic_pearson is not None else None,
        "hit_rate": float(metric.hit_rate) if metric.hit_rate is not None else None,
        "spread_contribution": (
            float(metric.spread_contribution) if metric.spread_contribution is not None else None
        ),
        "sample_size": metric.sample_size,
        "ranked_days": metric.ranked_days,
        "regime_coverage_pct": (
            float(metric.regime_coverage_pct) if metric.regime_coverage_pct is not None else None
        ),
        "stability_score": float(metric.stability_score) if metric.stability_score is not None else None,
        "stability_label": metric.stability_label,
        "coverage_label": metric.coverage_label,
        "bootstrap_ci_lower": (
            float(metric.bootstrap_ci_lower) if metric.bootstrap_ci_lower is not None else None
        ),
        "bootstrap_ci_upper": (
            float(metric.bootstrap_ci_upper) if metric.bootstrap_ci_upper is not None else None
        ),
        "p_value": float(metric.p_value) if metric.p_value is not None else None,
        "is_statistically_significant": metric.is_statistically_significant,
        "confidence": metric.confidence,
        "bootstrap_sample_count": metric.bootstrap_sample_count,
        "bootstrap_method": metric.bootstrap_method,
        "holdout_start_date": metric.holdout_start_date.isoformat(),
        "as_of_date_start": metric.as_of_date_start.isoformat(),
        "as_of_date_end": metric.as_of_date_end.isoformat(),
        "computed_at": metric.computed_at.isoformat(),
    }


def build_leaderboard(
    metrics: list[FactorPerformanceMetric],
    *,
    weights: dict[str, float],
    train_by_factor: dict[str, FactorPerformanceMetric],
    sort_by: str = "ic_spearman",
) -> dict:
    entries = []
    for metric in metrics:
        train = train_by_factor.get(metric.factor_name)
        train_ic = float(train.ic_spearman) if train and train.ic_spearman is not None else None
        holdout_ic = float(metric.ic_spearman) if metric.ic_spearman is not None else None
        drift = None
        if train_ic is not None and holdout_ic is not None:
            drift = round(train_ic - holdout_ic, 8)
        entries.append(
            {
                "factor_name": metric.factor_name,
                "current_weight": weights.get(metric.factor_name),
                "train_ic": train_ic,
                "holdout_ic": holdout_ic,
                "ic_drift": drift,
                "ic_spearman": holdout_ic,
                "ic_pearson": float(metric.ic_pearson) if metric.ic_pearson is not None else None,
                "hit_rate": float(metric.hit_rate) if metric.hit_rate is not None else None,
                "sample_size": metric.sample_size,
                "ranked_days": metric.ranked_days,
                "stability_score": (
                    float(metric.stability_score) if metric.stability_score is not None else None
                ),
                "stability_label": metric.stability_label,
                "regime_coverage_pct": (
                    float(metric.regime_coverage_pct)
                    if metric.regime_coverage_pct is not None
                    else None
                ),
                "coverage_label": metric.coverage_label,
                "is_statistically_significant": metric.is_statistically_significant,
                "confidence": metric.confidence,
                "p_value": float(metric.p_value) if metric.p_value is not None else None,
            }
        )
    reverse = sort_by in {"ic_spearman", "spread_contribution", "hit_rate"}
    entries.sort(
        key=lambda item: item.get(sort_by) if item.get(sort_by) is not None else float("-inf"),
        reverse=reverse,
    )
    return {"entries": entries}


def build_regime_matrix(
    metrics: list[FactorPerformanceMetric],
    *,
    horizon: int,
    dataset_split: str,
) -> dict:
    matrix: dict[str, dict[str, float | None]] = {}
    for metric in metrics:
        if metric.horizon != horizon or metric.dataset_split != dataset_split:
            continue
        matrix.setdefault(metric.factor_name, {})[metric.regime_label] = (
            float(metric.ic_spearman) if metric.ic_spearman is not None else None
        )
    return {"horizon": horizon, "dataset_split": dataset_split, "matrix": matrix}


def build_horizon_stability(
    metrics: list[FactorPerformanceMetric],
    *,
    regime_label: str,
    dataset_split: str,
) -> dict:
    table: dict[str, dict[int, float | None]] = {}
    for metric in metrics:
        if metric.regime_label != regime_label or metric.dataset_split != dataset_split:
            continue
        table.setdefault(metric.factor_name, {})[metric.horizon] = (
            float(metric.ic_spearman) if metric.ic_spearman is not None else None
        )
    return {"regime_label": regime_label, "dataset_split": dataset_split, "table": table}


def build_weight_alignment(
    metrics: list[FactorPerformanceMetric],
    *,
    weights: dict[str, float],
) -> dict:
    rows = []
    for metric in metrics:
        weight = weights.get(metric.factor_name, 0.0)
        ic = float(metric.ic_spearman) if metric.ic_spearman is not None else 0.0
        rows.append(
            {
                "factor_name": metric.factor_name,
                "current_weight": weight,
                "ic_spearman": float(metric.ic_spearman) if metric.ic_spearman is not None else None,
                "ic_x_weight": round(ic * weight, 8),
                "recommendation": _weight_recommendation(ic, weight, metric),
            }
        )
    rows.sort(key=lambda item: item["ic_x_weight"], reverse=True)
    return {"entries": rows}


def _weight_recommendation(ic: float, weight: float, metric: FactorPerformanceMetric) -> str:
    if metric.coverage_label == "sparse_regime":
        return "investigate"
    if ic > 0.03 and metric.is_statistically_significant:
        return "keep"
    if weight > 0.10 and abs(ic) < 0.01:
        return "investigate"
    if ic < 0:
        return "reduce"
    if abs(ic) < 0.01 and not metric.is_statistically_significant:
        return "remove_candidate"
    return "investigate"


def build_train_holdout_drift(
    train_metrics: list[FactorPerformanceMetric],
    holdout_metrics: list[FactorPerformanceMetric],
    *,
    min_train_ic: float = DRIFT_OVERFIT_TRAIN_IC,
) -> list[TrainHoldoutDriftEntry]:
    holdout_by_factor = {m.factor_name: m for m in holdout_metrics}
    entries: list[TrainHoldoutDriftEntry] = []
    for train in train_metrics:
        holdout = holdout_by_factor.get(train.factor_name)
        train_ic = float(train.ic_spearman) if train.ic_spearman is not None else None
        holdout_ic = float(holdout.ic_spearman) if holdout and holdout.ic_spearman is not None else None
        drift = None
        if train_ic is not None and holdout_ic is not None:
            drift = round(train_ic - holdout_ic, 8)
        verdict = _drift_verdict(train_ic, holdout_ic, holdout)
        entries.append(
            TrainHoldoutDriftEntry(
                factor_name=train.factor_name,
                train_ic_spearman=train_ic,
                holdout_ic_spearman=holdout_ic,
                ic_drift=drift,
                stability_score=(
                    float(holdout.stability_score)
                    if holdout and holdout.stability_score is not None
                    else None
                ),
                regime_coverage_pct=(
                    float(holdout.regime_coverage_pct)
                    if holdout and holdout.regime_coverage_pct is not None
                    else None
                ),
                verdict=verdict,
            )
        )
    entries.sort(
        key=lambda item: item.train_ic_spearman if item.train_ic_spearman is not None else -999,
        reverse=True,
    )
    return [e for e in entries if e.train_ic_spearman is not None and e.train_ic_spearman >= min_train_ic]


def _drift_verdict(
    train_ic: float | None,
    holdout_ic: float | None,
    holdout: FactorPerformanceMetric | None,
) -> str:
    if holdout is None or holdout.sample_size < 30:
        return "insufficient_holdout_data"
    if train_ic is None or train_ic <= DRIFT_OVERFIT_TRAIN_IC:
        return "insufficient_train_edge"
    if holdout_ic is not None and holdout_ic > DRIFT_OVERFIT_TRAIN_IC:
        return "holdout_confirmed"
    if holdout_ic is not None and holdout_ic <= DRIFT_OVERFIT_HOLDOUT_IC:
        return "overfit_suspect"
    return "investigate"
