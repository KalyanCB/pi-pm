from __future__ import annotations

from app.models.exit_research import ExitResearchPolicyMetric
from app.workspace_exit_research.constants import (
    INSUFFICIENT_SAMPLE_STATUS,
    POLICY_FAMILY_ALPHA_DECAY,
    POLICY_FAMILY_FIXED_HOLD,
    POLICY_FAMILY_RANK_DETERIORATION,
    POLICY_FAMILY_REGIME_EXIT,
    POLICY_FAMILY_TREND_FAILURE,
)
from app.workspace_exit_research.models import PolicyMetricResult


def policy_metric_to_dict(row: ExitResearchPolicyMetric) -> dict:
    return {
        "policy_family": row.policy_family,
        "policy_variant": row.policy_variant,
        "strategy_name": row.strategy_name,
        "strategy_version": row.strategy_version,
        "universe_code": row.universe_code,
        "regime_label": row.regime_label,
        "dataset_split": row.dataset_split,
        "horizon": row.horizon,
        "sample_size": row.sample_size,
        "mean_return": float(row.mean_return) if row.mean_return is not None else None,
        "median_return": float(row.median_return) if row.median_return is not None else None,
        "std_dev": float(row.std_dev) if row.std_dev is not None else None,
        "hit_rate": float(row.hit_rate) if row.hit_rate is not None else None,
        "avg_holding_days": float(row.avg_holding_days) if row.avg_holding_days is not None else None,
        "ci_lower": float(row.ci_lower) if row.ci_lower is not None else None,
        "ci_upper": float(row.ci_upper) if row.ci_upper is not None else None,
        "conclusion_status": row.conclusion_status,
    }


def build_exit_policy_comparison(metrics: list[ExitResearchPolicyMetric]) -> dict:
    return {
        "report": "exit_policy_comparison",
        "entries": [policy_metric_to_dict(m) for m in metrics],
    }


def build_family_report(
    metrics: list[ExitResearchPolicyMetric],
    *,
    policy_family: str,
    report_name: str,
) -> dict:
    filtered = [m for m in metrics if m.policy_family == policy_family]
    return {"report": report_name, "entries": [policy_metric_to_dict(m) for m in filtered]}


def build_recommended_exit_policy(metrics: list[ExitResearchPolicyMetric], *, dataset_split: str) -> dict:
    candidates = [
        m
        for m in metrics
        if m.policy_family == POLICY_FAMILY_FIXED_HOLD
        and m.dataset_split == dataset_split
        and m.conclusion_status != INSUFFICIENT_SAMPLE_STATUS
        and m.mean_return is not None
    ]
    candidates.sort(key=lambda m: float(m.mean_return), reverse=True)
    top = candidates[0] if candidates else None
    return {
        "report": "recommended_exit_policy",
        "dataset_split": dataset_split,
        "recommended_variant": top.policy_variant if top else None,
        "mean_return": float(top.mean_return) if top and top.mean_return is not None else None,
        "sample_size": top.sample_size if top else 0,
        "note": "Research recommendation only — not for production deployment.",
        "alternatives": [policy_metric_to_dict(m) for m in candidates[:5]],
    }


FAMILY_REPORT_MAP = {
    POLICY_FAMILY_FIXED_HOLD: "exit_policy_comparison",
    POLICY_FAMILY_ALPHA_DECAY: "alpha_decay_analysis",
    POLICY_FAMILY_RANK_DETERIORATION: "rank_deterioration_analysis",
    POLICY_FAMILY_REGIME_EXIT: "regime_transition_analysis",
    POLICY_FAMILY_TREND_FAILURE: "trend_failure_analysis",
}
