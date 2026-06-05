"""Tests for trust metrics: calibration, stability, reliability."""
import pytest
from datetime import date

from app.recommendation_analytics.calculator import OutcomeRow
from app.recommendation_analytics.dtos import OutcomeWindowDTO
from app.recommendation_analytics.trust_metrics import (
    _ActionHistory,
    compute_calibration,
    compute_reliability,
    compute_stability,
    compute_trust_metrics,
)


def _row(**kwargs) -> OutcomeRow:
    defaults = dict(
        outcome_status="WIN", alpha_pct=5.0, pnl_pct=5.0, benchmark_return_pct=2.0,
        target_hit=True, stop_hit=False, days_held=14,
        conviction_band="HIGH", regime_label="BULL_LOW_VOL",
        strategy_name="momentum_v1", committee_advisory="supportive", symbol="RELIANCE",
    )
    defaults.update(kwargs)
    return OutcomeRow(**defaults)


def _window() -> OutcomeWindowDTO:
    return OutcomeWindowDTO(from_date=None, to_date=None, strategy_name=None, window_sessions=0)


# ── Calibration ────────────────────────────────────────────────────────────────

def test_calibration_correctly_ordered():
    rows = [
        _row(conviction_band="EXCEPTIONAL", outcome_status="WIN"),
        _row(conviction_band="EXCEPTIONAL", outcome_status="WIN"),
        _row(conviction_band="HIGH", outcome_status="WIN"),
        _row(conviction_band="HIGH", outcome_status="LOSS"),
        _row(conviction_band="MEDIUM", outcome_status="LOSS"),
        _row(conviction_band="LOW", outcome_status="LOSS"),
        _row(conviction_band="LOW", outcome_status="LOSS"),
    ]
    cal = compute_calibration(rows)
    assert cal.is_calibrated is True
    assert cal.rank_correlation is not None and cal.rank_correlation > 0
    assert "EXCEPTIONAL" in cal.expected_order


def test_calibration_returns_actual_win_rates():
    rows = [
        _row(conviction_band="HIGH", outcome_status="WIN"),
        _row(conviction_band="HIGH", outcome_status="WIN"),
        _row(conviction_band="LOW", outcome_status="LOSS"),
    ]
    cal = compute_calibration(rows)
    assert "HIGH" in cal.actual_win_rates
    assert cal.actual_win_rates["HIGH"] == pytest.approx(1.0)


def test_calibration_none_when_single_band():
    rows = [_row(conviction_band="HIGH", outcome_status="WIN")]
    cal = compute_calibration(rows)
    assert cal.is_calibrated is None


# ── Stability ──────────────────────────────────────────────────────────────────

def test_stability_no_churn():
    history = [
        _ActionHistory("RELIANCE", [(date(2026, 6, 1), "BUY"), (date(2026, 6, 2), "BUY"), (date(2026, 6, 3), "BUY")]),
    ]
    s = compute_stability(history)
    assert s.daily_action_changes == 0
    assert s.churn_rate == pytest.approx(0.0)
    assert s.stability_score == pytest.approx(1.0)


def test_stability_full_churn():
    history = [
        _ActionHistory("RELIANCE", [
            (date(2026, 6, 1), "BUY"),
            (date(2026, 6, 2), "WATCH"),
            (date(2026, 6, 3), "BUY"),
            (date(2026, 6, 4), "WATCH"),
        ]),
    ]
    s = compute_stability(history)
    assert s.daily_action_changes == 3
    # 3 changes / 4 evaluations
    assert s.churn_rate == pytest.approx(3 / 4)


def test_stability_reversal_detected():
    history = [
        _ActionHistory("RELIANCE", [
            (date(2026, 6, 1), "BUY"),
            (date(2026, 6, 2), "WATCH"),
            (date(2026, 6, 3), "BUY"),
        ]),
    ]
    s = compute_stability(history)
    assert s.reversal_count == 1


def test_stability_empty_history():
    s = compute_stability([])
    assert s.total_symbols_evaluated == 0
    assert s.churn_rate is None


# ── Reliability ────────────────────────────────────────────────────────────────

def test_reliability_full():
    r = compute_reliability(100, 100, 0)
    assert r.reliability_rate == pytest.approx(1.0)


def test_reliability_partial():
    r = compute_reliability(100, 80, 20)
    assert r.reliability_rate == pytest.approx(0.8)


def test_reliability_zero_total():
    r = compute_reliability(0, 0, 0)
    assert r.reliability_rate is None


# ── Composite trust score ──────────────────────────────────────────────────────

def test_trust_score_computed():
    rows = [
        _row(conviction_band="EXCEPTIONAL", outcome_status="WIN"),
        _row(conviction_band="HIGH", outcome_status="WIN"),
        _row(conviction_band="MEDIUM", outcome_status="LOSS"),
        _row(conviction_band="LOW", outcome_status="LOSS"),
    ]
    history = [_ActionHistory("X", [(date(2026, 6, 1), "BUY"), (date(2026, 6, 2), "BUY")])]
    t = compute_trust_metrics(
        window=_window(),
        outcome_rows=rows,
        action_history=history,
        total_recommendations=10,
        completed_validation_count=8,
        insufficient_data_count=2,
    )
    assert t.overall_trust_score is not None
    assert 0.0 <= t.overall_trust_score <= 1.0


def test_trust_score_deterministic():
    rows = [_row(conviction_band="HIGH", outcome_status="WIN")] * 5
    history = [_ActionHistory("X", [(date(2026, 6, i), "BUY") for i in range(1, 4)])]
    kwargs = dict(window=_window(), outcome_rows=rows, action_history=history,
                  total_recommendations=10, completed_validation_count=10, insufficient_data_count=0)
    t1 = compute_trust_metrics(**kwargs)
    t2 = compute_trust_metrics(**kwargs)
    assert t1.overall_trust_score == t2.overall_trust_score
