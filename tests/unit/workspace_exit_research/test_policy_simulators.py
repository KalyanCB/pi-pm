from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.ranking.math_utils import PriceBar
from app.workspace_exit_research.constants import (
    MIN_EXIT_SAMPLE_SIZE,
    POLICY_FAMILY_FIXED_HOLD,
    POLICY_FAMILY_TREND_FAILURE,
)
from app.workspace_exit_research.models import ExitSimulationResult, SignalEntry
from app.workspace_exit_research.policy_simulators import (
    ExitMetricsEngine,
    _return_between,
    alpha_decay_returns,
    bootstrap_ci,
    simulate_fixed_hold,
    simulate_trend_failure,
)


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


def _bars_from_closes(start: date, closes: list[str | Decimal]) -> list[PriceBar]:
    bars: list[PriceBar] = []
    for offset, close in enumerate(closes):
        bars.append(
            PriceBar(
                date=start + timedelta(days=offset),
                close=Decimal(str(close)),
                volume=1_000_000,
            )
        )
    return bars


def test_simulate_fixed_hold_uses_snapshot():
    entry = _entry(return_20d=Decimal("0.08"))
    result = simulate_fixed_hold(entry, 20, [])
    assert result.period_return == Decimal("0.08")
    assert result.policy_variant == "FIXED_HOLD_20"


def test_return_between_uses_decimal_prices():
    start = date(2024, 1, 1)
    bars = _bars_from_closes(start, ["100.00", "105.50"])
    ret = _return_between(bars, start, start + timedelta(days=1))
    assert ret == Decimal("0.055")


def test_simulate_trend_failure_atr_trail_with_decimal_atr():
    start = date(2024, 1, 1)
    # 16+ bars before entry for ATR(14); then a drop that breaches 2x ATR trail.
    pre_entry = [Decimal("100")] * 15 + [Decimal("102")]
    post_entry = [Decimal("103"), Decimal("104"), Decimal("95")]
    closes = [str(v) for v in pre_entry + post_entry]
    entry_date = start + timedelta(days=15)
    bars = _bars_from_closes(start, closes)
    entry = _entry(entry_date=entry_date)

    result = simulate_trend_failure(entry, "TREND_ATR_TRAIL", bars)

    assert result.policy_family == POLICY_FAMILY_TREND_FAILURE
    assert result.policy_variant == "TREND_ATR_TRAIL"
    assert result.exit_reason == "TREND_ATR_TRAIL"
    assert result.period_return is not None
    assert isinstance(result.period_return, Decimal)


def test_alpha_decay_returns_decimal_values():
    start = date(2024, 1, 1)
    bars = _bars_from_closes(start, ["100", "101", "102", "103", "104"])
    entry = _entry(entry_date=start)
    decay = alpha_decay_returns(entry, bars)
    assert decay[1] == Decimal("0.01")
    assert decay[4] == Decimal("0.04")
    assert all(ret is None or isinstance(ret, Decimal) for ret in decay.values())


def test_aggregate_policy_insufficient_sample():
    engine = ExitMetricsEngine()
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


def test_aggregate_policy_decimal_returns():
    engine = ExitMetricsEngine()
    returns = [Decimal("0.01"), Decimal("0.02"), Decimal("-0.01"), Decimal("0.03")]
    results = [
        ExitSimulationResult(POLICY_FAMILY_FIXED_HOLD, "FIXED_HOLD_5", ret, 5, "TIME")
        for ret in returns
    ] * (MIN_EXIT_SAMPLE_SIZE // len(returns) + 1)
    results = results[:MIN_EXIT_SAMPLE_SIZE]
    expected_hit_rate = sum(1 for result in results if result.period_return > 0) / len(results)

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
    assert metric.conclusion_status == "ok"
    assert metric.mean_return is not None
    assert metric.hit_rate == pytest.approx(expected_hit_rate, rel=1e-6)


def test_aggregate_alpha_decay_decimal_returns():
    engine = ExitMetricsEngine()
    day_returns = {
        1: [Decimal("0.01")] * MIN_EXIT_SAMPLE_SIZE,
        2: [Decimal("0.02")] * MIN_EXIT_SAMPLE_SIZE,
    }
    points = engine.aggregate_alpha_decay(day_returns, regime_label="ALL", dataset_split="TRAIN")
    assert points[0].mean_return == 0.01
    assert points[1].mean_return == 0.02
    assert points[1].cumulative_mean_return == 0.015


def test_bootstrap_ci_returns_bounds():
    values = [
        Decimal("0.01"),
        Decimal("0.02"),
        Decimal("0.03"),
        Decimal("0.04"),
        Decimal("0.05"),
    ] * 10
    lower, upper = bootstrap_ci(values)
    assert lower is not None and upper is not None
    assert lower <= upper
