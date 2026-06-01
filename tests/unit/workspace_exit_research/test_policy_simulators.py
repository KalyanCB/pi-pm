from decimal import Decimal

from app.ranking.math_utils import PriceBar
from app.workspace_exit_research.constants import MIN_EXIT_SAMPLE_SIZE
from app.workspace_exit_research.policy_simulators import (
    ExitMetricsEngine,
    bootstrap_ci,
    simulate_fixed_hold,
)
from app.workspace_exit_research.models import SignalEntry
from datetime import date
from uuid import uuid4


def _entry(**kwargs) -> SignalEntry:
    defaults = dict(
        ranking_run_id=uuid4(),
        stock_id=uuid4(),
        symbol="TST.NS",
        entry_date=date(2024, 6, 3),
        entry_rank=1,
        entry_score=Decimal("10"),
        entry_close=Decimal("100"),
        regime_label="BULL_LOW_VOL",
        sector="IT",
        dataset_split="TRAIN",
        return_20d=Decimal("0.05"),
    )
    defaults.update(kwargs)
    return SignalEntry(**defaults)


def test_simulate_fixed_hold_uses_snapshot():
    entry = _entry(return_20d=Decimal("0.08"))
    result = simulate_fixed_hold(entry, 20, [])
    assert result.period_return == Decimal("0.08")
    assert result.policy_variant == "FIXED_HOLD_20"


def test_aggregate_policy_insufficient_sample():
    engine = ExitMetricsEngine()
    from app.workspace_exit_research.models import ExitSimulationResult
    from app.workspace_exit_research.constants import POLICY_FAMILY_FIXED_HOLD

    results = [
        ExitSimulationResult(
            POLICY_FAMILY_FIXED_HOLD,
            "FIXED_HOLD_5",
            Decimal("0.01"),
            5,
            "TIME",
        )
    ] * 10
    metric = engine.aggregate_policy(
        results,
        strategy_name="breakout_v1",
        strategy_version="1.0.0",
        universe_code="NIFTY_500",
        regime_label="ALL",
        dataset_split="TRAIN",
        horizon=20,
        holdout_start_date=date(2025, 1, 1),
        as_of_date_start=date(2024, 1, 1),
        as_of_date_end=date(2024, 12, 31),
    )
    assert metric is not None
    assert metric.conclusion_status == "INSUFFICIENT_SAMPLE_SIZE"


def test_bootstrap_ci_returns_bounds():
    values = [0.01, 0.02, 0.03, 0.04, 0.05] * 10
    lower, upper = bootstrap_ci(values)
    assert lower is not None and upper is not None
    assert lower <= upper
