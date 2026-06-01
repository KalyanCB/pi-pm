from __future__ import annotations

from collections import defaultdict

from app.factor_analytics.constants import DATASET_SPLITS
from app.workspace_exit_research.constants import REGIME_LABEL_ALL
from app.workspace_exit_research.models import ExitSimulationResult, SignalEntry
from app.workspace_exit_research.policy_simulators import filter_entries

PolicyBucketKey = tuple[str, str, str, str]


def build_policy_metric_buckets(
    entries: list[SignalEntry],
    entry_sims: dict[tuple, list[ExitSimulationResult]],
    *,
    holdout_start_date,
) -> dict[PolicyBucketKey, list[ExitSimulationResult]]:
    """Index simulations by (family, variant, regime_label, dataset_split).

    Matches legacy behavior: at most one simulation per entry per bucket (first
    matching family/variant in simulator output order).
    """
    buckets: dict[PolicyBucketKey, list[ExitSimulationResult]] = defaultdict(list)

    for entry in entries:
        sims = entry_sims.get((entry.ranking_run_id, entry.stock_id))
        if not sims:
            continue

        first_by_family_variant: dict[tuple[str, str], ExitSimulationResult] = {}
        for sim in sims:
            fv_key = (sim.policy_family, sim.policy_variant)
            if fv_key not in first_by_family_variant:
                first_by_family_variant[fv_key] = sim

        for regime_label in (REGIME_LABEL_ALL, entry.regime_label):
            for dataset_split in DATASET_SPLITS:
                if not filter_entries(
                    [entry],
                    regime_label=regime_label,
                    dataset_split=dataset_split,
                    holdout_start_date=holdout_start_date,
                ):
                    continue
                for (family, variant), sim in first_by_family_variant.items():
                    buckets[(family, variant, regime_label, dataset_split)].append(sim)

    return dict(buckets)


def count_policy_persist_items(buckets: dict[PolicyBucketKey, list[ExitSimulationResult]]) -> int:
    return sum(1 for sims in buckets.values() if sims)


def count_alpha_persist_items(stratum_count: int, *, trading_days: int = 60) -> int:
    return stratum_count * trading_days
