"""Tests for recommendation analytics calculator (AC-RP-01..09)."""

import pytest

from app.recommendation_analytics.calculator import (
    OutcomeRow,
    check_conviction_calibration,
    compute_committee_breakdown,
    compute_conviction_breakdown,
    compute_quality_metrics,
    compute_regime_breakdown,
)


def _row(**kwargs) -> OutcomeRow:
    defaults = dict(
        outcome_status="WIN",
        alpha_pct=5.0,
        pnl_pct=5.0,
        benchmark_return_pct=2.0,
        target_hit=True,
        stop_hit=False,
        days_held=14,
        conviction_band="HIGH",
        regime_label="BULL_LOW_VOL",
        strategy_name="momentum_v1",
        committee_advisory="supportive",
        symbol="RELIANCE",
    )
    defaults.update(kwargs)
    return OutcomeRow(**defaults)


# ── AC-RP-01: Every closed outcome can produce metrics ────────────────────────


def test_quality_metrics_win():
    rows = [_row(outcome_status="WIN", alpha_pct=5.0)] * 3 + [
        _row(outcome_status="LOSS", alpha_pct=-2.0)
    ]
    m = compute_quality_metrics(rows)
    assert m.win_count == 3
    assert m.loss_count == 1
    assert m.closed_count == 4
    assert m.win_rate == pytest.approx(0.75)


# AC-RP-02: win rate
def test_win_rate_calculation():
    rows = [
        _row(outcome_status="WIN"),
        _row(outcome_status="WIN"),
        _row(outcome_status="LOSS"),
        _row(outcome_status="OPEN"),
    ]
    m = compute_quality_metrics(rows)
    # 2 wins / 3 closed = 0.666...
    assert m.win_rate == pytest.approx(2 / 3)
    assert m.open_count == 1


def test_win_rate_none_when_no_closed():
    rows = [_row(outcome_status="OPEN")]
    m = compute_quality_metrics(rows)
    assert m.win_rate is None


# AC-RP-03: alpha
def test_alpha_calculation():
    rows = [_row(outcome_status="WIN", alpha_pct=6.0), _row(outcome_status="LOSS", alpha_pct=-2.0)]
    m = compute_quality_metrics(rows)
    assert m.avg_alpha_pct == pytest.approx(2.0)  # (6 + -2) / 2
    assert m.median_alpha_pct == pytest.approx(2.0)


def test_profit_factor():
    rows = [
        _row(outcome_status="WIN", alpha_pct=10.0),
        _row(outcome_status="WIN", alpha_pct=5.0),
        _row(outcome_status="LOSS", alpha_pct=-3.0),
        _row(outcome_status="LOSS", alpha_pct=-2.0),
    ]
    m = compute_quality_metrics(rows)
    assert m.profit_factor == pytest.approx(15.0 / 5.0)  # 15 gain / 5 loss


def test_profit_factor_none_when_no_losses():
    rows = [_row(outcome_status="WIN", alpha_pct=5.0)]
    m = compute_quality_metrics(rows)
    assert m.profit_factor is None


# AC-RP-04: conviction band breakdown
def test_conviction_breakdown_grouping():
    rows = [
        _row(conviction_band="HIGH", outcome_status="WIN", alpha_pct=5.0),
        _row(conviction_band="HIGH", outcome_status="WIN", alpha_pct=4.0),
        _row(conviction_band="MEDIUM", outcome_status="LOSS", alpha_pct=-1.0),
    ]
    bands = compute_conviction_breakdown(rows)
    band_map = {b.band: b for b in bands}
    assert band_map["HIGH"].win_rate == pytest.approx(1.0)
    assert band_map["MEDIUM"].win_rate == pytest.approx(0.0)


# AC-RP-04: calibration check
def test_calibration_correct_when_exceptional_best():
    rows = [
        _row(conviction_band="EXCEPTIONAL", outcome_status="WIN", alpha_pct=10.0),
        _row(conviction_band="EXCEPTIONAL", outcome_status="WIN", alpha_pct=9.0),
        _row(conviction_band="HIGH", outcome_status="WIN", alpha_pct=5.0),
        _row(conviction_band="HIGH", outcome_status="LOSS", alpha_pct=-1.0),
        _row(conviction_band="MEDIUM", outcome_status="LOSS", alpha_pct=-2.0),
        _row(conviction_band="MEDIUM", outcome_status="LOSS", alpha_pct=-3.0),
        _row(conviction_band="LOW", outcome_status="LOSS", alpha_pct=-5.0),
    ]
    bands = compute_conviction_breakdown(rows)
    is_cal, rho = check_conviction_calibration(bands)
    assert is_cal is True
    assert rho is not None and rho > 0


def test_calibration_false_when_inverted():
    rows = [
        _row(conviction_band="EXCEPTIONAL", outcome_status="LOSS", alpha_pct=-5.0),
        _row(conviction_band="EXCEPTIONAL", outcome_status="LOSS", alpha_pct=-4.0),
        _row(conviction_band="LOW", outcome_status="WIN", alpha_pct=8.0),
        _row(conviction_band="LOW", outcome_status="WIN", alpha_pct=9.0),
    ]
    bands = compute_conviction_breakdown(rows)
    is_cal, rho = check_conviction_calibration(bands)
    assert is_cal is False


def test_calibration_none_when_insufficient():
    bands = compute_conviction_breakdown([_row(conviction_band="HIGH")])
    is_cal, rho = check_conviction_calibration(bands)
    assert is_cal is None


# AC-RP-05: regime breakdown
def test_regime_breakdown():
    rows = [
        _row(regime_label="BULL_LOW_VOL", outcome_status="WIN", alpha_pct=5.0),
        _row(regime_label="BULL_LOW_VOL", outcome_status="WIN", alpha_pct=4.0),
        _row(regime_label="BEAR_HIGH_VOL", outcome_status="LOSS", alpha_pct=-3.0),
    ]
    regimes = compute_regime_breakdown(rows)
    rm = {r.regime_label: r for r in regimes}
    assert rm["BULL_LOW_VOL"].win_rate == pytest.approx(1.0)
    assert rm["BULL_LOW_VOL"].regime_posture == "risk_on"
    assert rm["BEAR_HIGH_VOL"].win_rate == pytest.approx(0.0)
    assert rm["BEAR_HIGH_VOL"].regime_posture == "defensive"


# AC-RP-06: committee breakdown
def test_committee_breakdown():
    rows = [
        _row(committee_advisory="supportive", outcome_status="WIN", alpha_pct=6.0),
        _row(committee_advisory="supportive", outcome_status="WIN", alpha_pct=5.0),
        _row(committee_advisory="cautious", outcome_status="LOSS", alpha_pct=-2.0),
    ]
    advisories = compute_committee_breakdown(rows)
    am = {a.advisory: a for a in advisories}
    assert am["supportive"].win_rate == pytest.approx(1.0)
    assert am["cautious"].win_rate == pytest.approx(0.0)
    # Committee advisory — agreement value set correctly
    assert am["supportive"].agreement_with_machine == pytest.approx(1.0)


# AC-RP-08: deterministic replay
def test_deterministic_replay():
    rows = [
        _row(outcome_status="WIN", alpha_pct=5.0, conviction_band="HIGH"),
        _row(outcome_status="LOSS", alpha_pct=-2.0, conviction_band="MEDIUM"),
        _row(outcome_status="WIN", alpha_pct=3.0, conviction_band="HIGH"),
    ]
    m1 = compute_quality_metrics(rows)
    m2 = compute_quality_metrics(rows)
    assert m1.win_rate == m2.win_rate
    assert m1.avg_alpha_pct == m2.avg_alpha_pct
    assert m1.profit_factor == m2.profit_factor


# AC-RP-09: no LLM imports
def test_no_llm_imports_in_calculator():
    import ast
    import pathlib

    src = pathlib.Path(__file__).parents[3] / "app" / "recommendation_analytics" / "calculator.py"
    tree = ast.parse(src.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in getattr(node, "names", [])]
            module = getattr(node, "module", "") or ""
            combined = " ".join(names) + " " + module
            assert "openai" not in combined.lower()
            assert "anthropic" not in combined.lower()


def test_no_llm_imports_in_trust_metrics():
    import ast
    import pathlib

    src = (
        pathlib.Path(__file__).parents[3] / "app" / "recommendation_analytics" / "trust_metrics.py"
    )
    tree = ast.parse(src.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in getattr(node, "names", [])]
            module = getattr(node, "module", "") or ""
            combined = " ".join(names) + " " + module
            assert "openai" not in combined.lower()
            assert "anthropic" not in combined.lower()


# Target / stop metrics
def test_target_and_stop_rates():
    rows = [
        _row(outcome_status="WIN", target_hit=True, stop_hit=False),
        _row(outcome_status="WIN", target_hit=True, stop_hit=False),
        _row(outcome_status="LOSS", target_hit=False, stop_hit=True),
        _row(outcome_status="LOSS", target_hit=False, stop_hit=False),
    ]
    m = compute_quality_metrics(rows)
    assert m.target_hit_rate == pytest.approx(0.5)  # 2/4 closed
    assert m.stop_hit_rate == pytest.approx(0.25)  # 1/4 closed


def test_avg_days_held():
    rows = [
        _row(outcome_status="WIN", days_held=10),
        _row(outcome_status="LOSS", days_held=20),
    ]
    m = compute_quality_metrics(rows)
    assert m.avg_days_held == pytest.approx(15.0)
