"""Tests for Regime Conditional Edge Engine (ADR-032 Phase 2)."""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from app.recommendation.regime_edge_engine import (
    EdgeState,
    RCEEConfig,
    RegimeFit,
    evaluate,
)


def _mock_row(
    strategy_name: str = "breakout_v1",
    regime_label: str = "BULL_LOW_VOL",
    avg_ic: float | None = 0.028,
    ic_lower_95: float | None = 0.019,
    hit_rate: float | None = 0.60,
    expectancy: float | None = 0.015,
    expectancy_after_costs: float | None = 0.014,
    sample_count: int = 100,
    ic_std: float | None = 0.05,
) -> MagicMock:
    row = MagicMock()
    row.strategy_name = strategy_name
    row.regime_label = regime_label
    row.avg_ic = avg_ic
    row.ic_lower_95 = ic_lower_95
    row.hit_rate = hit_rate
    row.expectancy = expectancy
    row.expectancy_after_costs = expectancy_after_costs
    row.sample_count = sample_count
    row.ic_std = ic_std
    return row


def test_edge_present_all_gates_pass():
    """ic_lower_95=0.02, hit_rate=0.60, sample_days=100 → EDGE_PRESENT."""
    row = _mock_row(ic_lower_95=0.02, hit_rate=0.60, sample_count=100)
    result = evaluate(strategy_regime_row=row, config=RCEEConfig())
    assert result.edge_state == EdgeState.EDGE_PRESENT


def test_no_edge_ic_below_threshold():
    """ic_lower_95=-0.05 AND no expectancy edge → NO_EDGE."""
    row = _mock_row(
        ic_lower_95=-0.05, hit_rate=0.60, sample_count=100, expectancy_after_costs=-0.01
    )
    result = evaluate(strategy_regime_row=row, config=RCEEConfig())
    assert result.edge_state == EdgeState.NO_EDGE


def test_edge_present_via_expectancy_route_when_ic_negative():
    """P-18: negative 20-day IC but positive expectancy-after-costs over an adequate
    sample → EDGE_PRESENT (the reversal_v1 BEAR_LOW_VOL case). The IC gate alone would
    have vetoed it; the expectancy route unblocks the short-horizon strategy."""
    row = _mock_row(
        strategy_name="reversal_v1", regime_label="BEAR_LOW_VOL",
        ic_lower_95=-0.034, hit_rate=0.36, sample_count=139,
        expectancy_after_costs=0.0423,
    )
    result = evaluate(strategy_regime_row=row, config=RCEEConfig())
    assert result.edge_state == EdgeState.EDGE_PRESENT
    assert result.gate_results["edge_present_expectancy"] is True
    assert result.gate_results["edge_present_ic"] is False


def test_no_edge_expectancy_route_needs_sample_floor():
    """P-18: positive expectancy but thin sample → not EDGE_PRESENT (floor still applies)."""
    row = _mock_row(
        ic_lower_95=-0.05, hit_rate=0.36, sample_count=10, expectancy_after_costs=0.05
    )
    result = evaluate(strategy_regime_row=row, config=RCEEConfig())
    assert result.edge_state != EdgeState.EDGE_PRESENT


def test_edge_provisional_early_window():
    """P-04: ic_lower_95=0.005, hit_rate=0.52, sample_count=40 (in the 25-60 early
    window) → EDGE_PROVISIONAL (tradeable, breaks the cold-start deadlock)."""
    row = _mock_row(ic_lower_95=0.005, hit_rate=0.52, sample_count=40,
                    expectancy_after_costs=-0.01)
    result = evaluate(strategy_regime_row=row, config=RCEEConfig())
    assert result.edge_state == EdgeState.EDGE_PROVISIONAL


def test_edge_weak_after_window_closes():
    """Same marginal IC but past the provisional window (n>=60) and below the
    EDGE_PRESENT floor → EDGE_WEAK (provisional no longer available)."""
    row = _mock_row(ic_lower_95=0.005, hit_rate=0.52, sample_count=75,
                    expectancy_after_costs=-0.01)
    result = evaluate(strategy_regime_row=row, config=RCEEConfig())
    assert result.edge_state == EdgeState.EDGE_WEAK


def test_provisional_disabled_falls_to_weak():
    """provisional_allowed=False (live mode) → early window reverts to EDGE_WEAK."""
    from app.recommendation.regime_edge_engine import RCEEConfig as _Cfg
    row = _mock_row(ic_lower_95=0.005, hit_rate=0.52, sample_count=40,
                    expectancy_after_costs=-0.01)
    result = evaluate(strategy_regime_row=row, config=_Cfg(provisional_allowed=False))
    assert result.edge_state == EdgeState.EDGE_WEAK


def test_no_edge_insufficient_samples():
    """Good IC but only 10 days of data → NO_EDGE (below even EDGE_WEAK threshold)."""
    row = _mock_row(ic_lower_95=0.02, hit_rate=0.60, sample_count=10)
    result = evaluate(strategy_regime_row=row, config=RCEEConfig())
    assert result.edge_state == EdgeState.NO_EDGE


def test_unknown_when_no_row():
    """None input → UNKNOWN edge state."""
    result = evaluate(strategy_regime_row=None, config=RCEEConfig())
    assert result.edge_state == EdgeState.UNKNOWN
    assert result.avg_ic is None
    assert result.ic_lower_95 is None
    assert result.sample_days == 0


def test_gate_results_audit_trail():
    """gate_results dict is populated with all expected gate names."""
    row = _mock_row(ic_lower_95=0.015, hit_rate=0.58, sample_count=80)
    result = evaluate(strategy_regime_row=row, config=RCEEConfig())
    expected_gates = {
        "edge_present_ic",
        "edge_present_hit_rate",
        "edge_present_sample_days",
        "edge_present_expectancy",
        "edge_provisional_ic",
        "edge_provisional_hit_rate",
        "edge_provisional_sample_window",
        "edge_weak_ic",
        "edge_weak_hit_rate",
        "edge_weak_sample_days",
    }
    assert set(result.gate_results.keys()) == expected_gates
    # All values are bool
    for v in result.gate_results.values():
        assert isinstance(v, bool)


def test_threshold_config_captured():
    """threshold_config reflects the RCEEConfig values used."""
    config = RCEEConfig(
        edge_present_ic_lower_95=0.015,
        edge_present_hit_rate=0.58,
        edge_present_sample_days=90,
    )
    row = _mock_row()
    result = evaluate(strategy_regime_row=row, config=config)
    assert result.threshold_config["edge_present_ic_lower_95"] == 0.015
    assert result.threshold_config["edge_present_hit_rate"] == 0.58
    assert result.threshold_config["edge_present_sample_days"] == 90.0


def test_no_edge_when_hit_rate_too_low():
    """Good IC but hit_rate=0.40 and no expectancy edge → NO_EDGE."""
    row = _mock_row(
        ic_lower_95=0.02, hit_rate=0.40, sample_count=100, expectancy_after_costs=-0.01
    )
    result = evaluate(strategy_regime_row=row, config=RCEEConfig())
    assert result.edge_state == EdgeState.NO_EDGE
    assert result.gate_results["edge_present_hit_rate"] is False
    assert result.gate_results["edge_weak_hit_rate"] is False


def test_edge_present_gate_results_all_true():
    """EDGE_PRESENT → all three EDGE_PRESENT gates must be True."""
    row = _mock_row(ic_lower_95=0.02, hit_rate=0.60, sample_count=100)
    result = evaluate(strategy_regime_row=row, config=RCEEConfig())
    assert result.gate_results["edge_present_ic"] is True
    assert result.gate_results["edge_present_hit_rate"] is True
    assert result.gate_results["edge_present_sample_days"] is True


def test_unknown_returns_empty_gate_results():
    """None row → gate_results is empty dict (nothing to evaluate)."""
    result = evaluate(strategy_regime_row=None, config=RCEEConfig())
    assert result.gate_results == {}


def test_none_ic_lower_treated_as_negative_inf():
    """ic_lower_95=None and no expectancy edge → treated as -inf → NO_EDGE."""
    row = _mock_row(
        ic_lower_95=None, hit_rate=0.60, sample_count=100, expectancy_after_costs=-0.01
    )
    result = evaluate(strategy_regime_row=row, config=RCEEConfig())
    assert result.edge_state == EdgeState.NO_EDGE
