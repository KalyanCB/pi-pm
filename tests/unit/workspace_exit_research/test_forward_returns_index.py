import random
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.ranking.math_utils import PriceBar
from app.validation.forward_returns import compute_forward_return
from app.workspace_exit_research.constants import ALPHA_DECAY_MAX_DAYS
from app.workspace_exit_research.forward_returns_index import (
    BarForwardReturnIndex,
    alpha_decay_returns_indexed,
    alpha_decay_returns_matches_reference,
)
from app.workspace_exit_research.models import SignalEntry
from app.workspace_exit_research.policy_simulators import alpha_decay_returns


def _bars_from_closes(start: date, closes: list[str]) -> list[PriceBar]:
    return [
        PriceBar(date=start + timedelta(days=offset), close=Decimal(close), volume=1_000_000)
        for offset, close in enumerate(closes)
    ]


def _entry(entry_date: date) -> SignalEntry:
    return SignalEntry(
        ranking_run_id=uuid4(),
        stock_id=uuid4(),
        symbol="TST.NS",
        entry_date=entry_date,
        entry_rank=1,
        entry_score=Decimal("10"),
        entry_close=Decimal("100"),
        regime_label="BULL_LOW_VOL",
        sector="IT",
        dataset_split="TRAIN",
        return_20d=None,
    )


@pytest.mark.parametrize("max_days", [1, 5, 20, 60])
def test_forward_return_index_matches_validation_helper(max_days: int):
    start = date(2024, 1, 1)
    closes = [f"{100 + i * 0.5:.2f}" for i in range(120)]
    bars = _bars_from_closes(start, closes)
    as_of = start + timedelta(days=10)
    index = BarForwardReturnIndex(bars, as_of)
    for day in range(1, max_days + 1):
        assert index.forward_return(day) == compute_forward_return(bars, as_of, day)


def test_alpha_decay_returns_indexed_matches_per_day_calls():
    start = date(2024, 1, 1)
    closes = [f"{100 + i:.4f}" for i in range(90)]
    bars = _bars_from_closes(start, closes)
    as_of = start + timedelta(days=5)
    index = BarForwardReturnIndex(bars, as_of)
    indexed = alpha_decay_returns_indexed(index, max_days=ALPHA_DECAY_MAX_DAYS)
    reference = {
        day: compute_forward_return(bars, as_of, day) for day in range(1, ALPHA_DECAY_MAX_DAYS + 1)
    }
    assert indexed == reference


def test_alpha_decay_returns_policy_simulator_unchanged():
    start = date(2024, 1, 1)
    bars = _bars_from_closes(start, ["100", "101", "102", "103", "104"])
    entry = _entry(start)
    decay = alpha_decay_returns(entry, bars)
    assert decay[1] == Decimal("0.01")
    assert decay[4] == Decimal("0.04")


def test_alpha_decay_returns_matches_reference_property():
    rng = random.Random(42)
    start = date(2020, 1, 1)
    for trial in range(20):
        length = rng.randint(30, 200)
        closes = [f"{100 + rng.uniform(-2, 2) * i:.6f}" for i in range(length)]
        bars = _bars_from_closes(start, closes)
        as_of = start + timedelta(days=rng.randint(5, length - 25))
        assert alpha_decay_returns_matches_reference(bars, as_of, max_days=ALPHA_DECAY_MAX_DAYS)


def test_forward_return_index_handles_unsorted_bars():
    start = date(2024, 1, 1)
    bars = _bars_from_closes(start, ["100", "101", "102", "103"])
    shuffled = [bars[2], bars[0], bars[3], bars[1]]
    as_of = start + timedelta(days=1)
    assert BarForwardReturnIndex(shuffled, as_of).forward_return(2) == compute_forward_return(
        shuffled, as_of, 2
    )


def test_forward_return_index_insufficient_future():
    start = date(2024, 1, 1)
    bars = _bars_from_closes(start, ["100", "101"])
    index = BarForwardReturnIndex(bars, start)
    assert index.forward_return(5) is None
    assert index.forward_returns_through(5)[5] is None
