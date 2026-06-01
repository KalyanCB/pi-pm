from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.factor_analytics.constants import DATASET_SPLIT_HOLDOUT
from app.workspace_exit_research.aggregation_index import build_policy_metric_buckets
from app.workspace_exit_research.constants import REGIME_LABEL_ALL
from app.workspace_exit_research.models import ExitSimulationResult, SignalEntry
from app.workspace_exit_research.policy_simulators import filter_entries


def _entry(regime: str = "BULL_LOW_VOL", entry_date: date = date(2024, 6, 3)) -> SignalEntry:
    return SignalEntry(
        ranking_run_id=uuid4(),
        stock_id=uuid4(),
        symbol="TST.NS",
        entry_date=entry_date,
        entry_rank=1,
        entry_score=Decimal("10"),
        entry_close=Decimal("100"),
        regime_label=regime,
        sector="IT",
        dataset_split="TRAIN",
    )


def _sim(family: str, variant: str, ret: str = "0.05") -> ExitSimulationResult:
    return ExitSimulationResult(family, variant, Decimal(ret), 10, "TIME")


def _legacy_matching(
    entries: list[SignalEntry],
    entry_sims: dict,
    *,
    family: str,
    variant: str,
    regime_label: str,
    dataset_split: str,
    holdout_start_date: date,
) -> list[ExitSimulationResult]:
    matching = []
    for entry in filter_entries(
        entries,
        regime_label=regime_label,
        dataset_split=dataset_split,
        holdout_start_date=holdout_start_date,
    ):
        sims = entry_sims.get((entry.ranking_run_id, entry.stock_id), [])
        for sim in sims:
            if sim.policy_family == family and sim.policy_variant == variant:
                matching.append(sim)
                break
    return matching


def test_aggregation_index_matches_legacy_buckets():
    holdout = date(2025, 1, 1)
    entries = [
        _entry("BULL_LOW_VOL", date(2024, 3, 1)),
        _entry("BEAR_HIGH_VOL", date(2024, 8, 1)),
    ]
    entry_sims = {}
    for entry in entries:
        entry_sims[(entry.ranking_run_id, entry.stock_id)] = [
            _sim("FIXED_HOLD", "FIXED_HOLD_20", "0.02"),
            _sim("FIXED_HOLD", "FIXED_HOLD_10", "0.03"),
            _sim("RANK_DETERIORATION", "RANK_EXIT_50", "0.04"),
        ]

    buckets = build_policy_metric_buckets(entries, entry_sims, holdout_start_date=holdout)

    for key, matching in buckets.items():
        family, variant, regime_label, dataset_split = key
        legacy = _legacy_matching(
            entries,
            entry_sims,
            family=family,
            variant=variant,
            regime_label=regime_label,
            dataset_split=dataset_split,
            holdout_start_date=holdout,
        )
        assert [s.policy_variant for s in matching] == [s.policy_variant for s in legacy]
        assert [s.period_return for s in matching] == [s.period_return for s in legacy]

    for entry in entries:
        for regime in (REGIME_LABEL_ALL, entry.regime_label):
            for split in (DATASET_SPLIT_HOLDOUT,):
                for sim in entry_sims[(entry.ranking_run_id, entry.stock_id)]:
                    key = (sim.policy_family, sim.policy_variant, regime, split)
                    if filter_entries(
                        [entry],
                        regime_label=regime,
                        dataset_split=split,
                        holdout_start_date=holdout,
                    ):
                        assert key in buckets
