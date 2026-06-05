"""Portfolio analytics tests — AC-PE-06, 07, 09, 11, 13."""
import math
from datetime import date

import pytest

from app.portfolio.analytics.performance import NavPoint, compute_performance
from app.portfolio.analytics.risk import compute_risk
from app.portfolio.analytics.attribution import compute_attribution
from app.portfolio.analytics.benchmark import SeriesPoint, compute_benchmark_comparison


# ── Performance (AC-PE-06, 07, 13) ────────────────────────────────────────────

def _nav_series(values: list[float], start=date(2026, 1, 1)) -> list[NavPoint]:
    from datetime import timedelta
    return [NavPoint(date=start + timedelta(days=i), nav=v) for i, v in enumerate(values)]


def test_total_return():
    nav = _nav_series([1_000_000, 1_050_000, 1_100_000])
    m = compute_performance(nav, [])
    assert m.total_return_pct == pytest.approx(10.0)


def test_max_drawdown(): # AC-PE-07
    # peak 1.1M then trough 0.9M → 18.18% drawdown
    nav = _nav_series([1_000_000, 1_100_000, 900_000, 950_000])
    m = compute_performance(nav, [])
    assert m.max_drawdown_pct == pytest.approx(18.1818, abs=0.01)


def test_no_drawdown_when_monotonic():
    nav = _nav_series([1_000_000, 1_050_000, 1_100_000])
    m = compute_performance(nav, [])
    assert m.max_drawdown_pct is None or m.max_drawdown_pct == 0.0


def test_win_rate_and_profit_factor():
    outcomes = [
        {"pnl_pct": 5.0, "days_held": 10},
        {"pnl_pct": 8.0, "days_held": 12},
        {"pnl_pct": -3.0, "days_held": 8},
    ]
    nav = _nav_series([1_000_000, 1_100_000])
    m = compute_performance(nav, outcomes)
    assert m.win_rate == pytest.approx(66.6667, abs=0.01)
    assert m.profit_factor == pytest.approx(13.0 / 3.0, abs=1e-3)


def test_sharpe_computed():
    nav = _nav_series([1_000_000, 1_010_000, 1_005_000, 1_020_000, 1_030_000])
    m = compute_performance(nav, [])
    assert m.sharpe_ratio is not None


def test_deterministic_replay():  # AC-PE-13
    nav = _nav_series([1_000_000, 1_050_000, 980_000, 1_100_000])
    outcomes = [{"pnl_pct": 5.0, "days_held": 10}]
    m1 = compute_performance(nav, outcomes)
    m2 = compute_performance(nav, outcomes)
    assert m1.total_return_pct == m2.total_return_pct
    assert m1.max_drawdown_pct == m2.max_drawdown_pct
    assert m1.sharpe_ratio == m2.sharpe_ratio


def test_empty_series():
    m = compute_performance([], [])
    assert m.total_return_pct is None
    assert m.trading_days == 0


# ── Risk (AC-PE-08) ───────────────────────────────────────────────────────────

def test_risk_low_when_clean():
    positions = [
        {"symbol": "A", "market_value": 100_000, "weight_pct": 10.0, "sector": "IT", "unrealized_pnl_pct": 2.0},
        {"symbol": "B", "market_value": 100_000, "weight_pct": 10.0, "sector": "Pharma", "unrealized_pnl_pct": 1.0},
    ]
    r = compute_risk(positions, total_equity=1_000_000, cash_balance=800_000)
    assert r.risk_level == "LOW"
    assert r.alerts == []


def test_low_cash_alert():
    positions = [{"symbol": "A", "market_value": 900_000, "weight_pct": 90.0, "sector": "IT"}]
    r = compute_risk(positions, total_equity=1_000_000, cash_balance=50_000, cash_floor_pct=15.0)
    codes = [a.code for a in r.alerts]
    assert "LOW_CASH" in codes


def test_concentration_alert():
    positions = [{"symbol": "A", "market_value": 250_000, "weight_pct": 25.0, "sector": "IT"}]
    r = compute_risk(positions, total_equity=1_000_000, cash_balance=750_000, single_name_cap_pct=18.0)
    codes = [a.code for a in r.alerts]
    assert "CONCENTRATION_RISK" in codes


def test_sector_limit_alert():
    positions = [
        {"symbol": "A", "market_value": 200_000, "weight_pct": 20.0, "sector": "IT"},
        {"symbol": "B", "market_value": 200_000, "weight_pct": 20.0, "sector": "IT"},
    ]
    r = compute_risk(positions, total_equity=1_000_000, cash_balance=600_000, sector_cap_pct=30.0)
    codes = [a.code for a in r.alerts]
    assert "SECTOR_LIMIT_BREACH" in codes


def test_drawdown_alert():
    positions = [{"symbol": "A", "market_value": 100_000, "weight_pct": 10.0, "sector": "IT"}]
    r = compute_risk(positions, total_equity=1_000_000, cash_balance=900_000, current_drawdown_pct=12.0)
    codes = [a.code for a in r.alerts]
    assert "DRAWDOWN_ALERT" in codes


# ── Attribution (AC-PE-09) ────────────────────────────────────────────────────

def test_attribution_by_strategy():
    outcomes = [
        {"strategy_name": "momentum_v1", "pnl_pct": 4.0, "alpha_pct": 2.0, "outcome_status": "WIN", "days_held": 10},
        {"strategy_name": "breakout_v1", "pnl_pct": 2.0, "alpha_pct": 1.0, "outcome_status": "WIN", "days_held": 12},
        {"strategy_name": "momentum_v1", "pnl_pct": -1.0, "alpha_pct": -0.5, "outcome_status": "LOSS", "days_held": 8},
    ]
    report = compute_attribution(outcomes)
    strat = {b.label: b for b in report.by_strategy}
    assert "momentum_v1" in strat
    assert strat["momentum_v1"].count == 2
    assert report.total_alpha_pct == pytest.approx(2.5)


def test_attribution_by_conviction():
    outcomes = [
        {"conviction_band": "HIGH", "pnl_pct": 5.0, "alpha_pct": 3.0, "outcome_status": "WIN", "days_held": 10},
        {"conviction_band": "MEDIUM", "pnl_pct": -2.0, "alpha_pct": -1.0, "outcome_status": "LOSS", "days_held": 7},
    ]
    report = compute_attribution(outcomes)
    bands = {b.label: b for b in report.by_conviction_band}
    assert bands["HIGH"].win_rate == pytest.approx(100.0)
    assert bands["MEDIUM"].win_rate == pytest.approx(0.0)


# ── Benchmark (AC-PE-11) ──────────────────────────────────────────────────────

def test_benchmark_comparison():
    from datetime import timedelta
    start = date(2026, 1, 1)
    port = [SeriesPoint(start + timedelta(days=i), v) for i, v in enumerate([100, 105, 110])]
    bench = [SeriesPoint(start + timedelta(days=i), v) for i, v in enumerate([100, 102, 104])]
    cmp = compute_benchmark_comparison(port, bench, "^CRSLDX")
    assert cmp.portfolio_return_pct == pytest.approx(10.0)
    assert cmp.benchmark_return_pct == pytest.approx(4.0)
    assert cmp.alpha_pct == pytest.approx(6.0)


def test_benchmark_insufficient_data():
    cmp = compute_benchmark_comparison([], [], "^NSEI")
    assert cmp.alpha_pct is None
    assert cmp.periods == 0


def test_benchmark_deterministic():
    from datetime import timedelta
    start = date(2026, 1, 1)
    port = [SeriesPoint(start + timedelta(days=i), v) for i, v in enumerate([100, 103, 108])]
    bench = [SeriesPoint(start + timedelta(days=i), v) for i, v in enumerate([100, 101, 103])]
    c1 = compute_benchmark_comparison(port, bench)
    c2 = compute_benchmark_comparison(port, bench)
    assert c1.alpha_pct == c2.alpha_pct
    assert c1.tracking_error_pct == c2.tracking_error_pct
