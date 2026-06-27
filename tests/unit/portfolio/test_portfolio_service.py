"""Portfolio Service unit tests — AC-PE-01..04."""

from unittest.mock import MagicMock

import pytest

from app.services.portfolio_service import (
    _CONVICTION_WEIGHTS,
    _DEFAULT_REGIME_SLOTS,
    PortfolioService,
)


def _mock_config(
    total_equity=1_000_000.0,
    deploy_pct=0.85,
    cash_floor_pct=0.15,
    reserve_pct=0.02,
    regime_slots=None,
    single_name_cap_pct=0.18,
    sector_cap_pct=0.30,
):
    cfg = MagicMock()
    cfg.total_equity = total_equity
    cfg.deploy_pct = deploy_pct
    cfg.cash_floor_pct = cash_floor_pct
    cfg.reserve_pct = reserve_pct
    cfg.regime_slots = regime_slots or _DEFAULT_REGIME_SLOTS
    cfg.single_name_cap_pct = single_name_cap_pct
    cfg.sector_cap_pct = sector_cap_pct
    return cfg


def _make_svc(positions=None, config=None, regime="neutral", nav_row=None):
    db = MagicMock()
    svc = PortfolioService(db)
    svc.get_config = MagicMock(return_value=config or _mock_config())
    svc._current_positions = MagicMock(return_value=positions or [])
    svc._resolve_regime_posture = MagicMock(return_value=regime)
    svc._latest_nav = MagicMock(return_value=nav_row)
    return svc


# ── Conviction weights ────────────────────────────────────────────────────────


def test_conviction_weights_ordering():
    assert _CONVICTION_WEIGHTS["EXCEPTIONAL"] > _CONVICTION_WEIGHTS["HIGH"]
    assert _CONVICTION_WEIGHTS["HIGH"] > _CONVICTION_WEIGHTS["MEDIUM"]
    assert _CONVICTION_WEIGHTS["MEDIUM"] > _CONVICTION_WEIGHTS["LOW"]
    assert _CONVICTION_WEIGHTS["LOW"] == 0.0


# ── Capital math (AC-PE-01) ───────────────────────────────────────────────────


def test_summary_uses_latest_nav_when_available():
    nav = MagicMock()
    nav.total_equity = 286_793.66
    nav.market_value = 0.0
    nav.unrealized_pnl = 0.0
    nav.cash_balance = 286_793.66
    nav.cash_pct = 1.0

    svc = _make_svc(nav_row=nav)
    summary = svc.get_summary()

    assert summary.total_equity == pytest.approx(286_793.66)
    assert summary.cash_available == pytest.approx(286_793.66)
    assert summary.deployable_capital == pytest.approx(286_793.66 * 0.85)


def test_summary_no_positions():
    svc = _make_svc()
    summary = svc.get_summary()
    assert summary.total_equity == 1_000_000.0
    assert summary.deployable_capital == pytest.approx(850_000.0)
    assert summary.cash_available == pytest.approx(1_000_000.0)
    assert summary.cash_pct == pytest.approx(1.0)
    assert summary.active_positions == 0


def test_summary_with_positions():
    pos = MagicMock()
    pos.market_value = 200_000.0
    pos.unrealized_pnl = 10_000.0
    pos.quantity = 100.0
    pos.avg_cost = 2000.0

    svc = _make_svc(positions=[pos])
    summary = svc.get_summary()

    assert summary.market_value == pytest.approx(200_000.0)
    assert summary.unrealized_pnl == pytest.approx(10_000.0)
    assert summary.cash_available == pytest.approx(800_000.0)
    assert summary.active_positions == 1


def test_equity_cash_market_value_reconciliation():
    """AC-PE-01: sum of positions + cash ≈ total_equity."""
    pos1, pos2 = MagicMock(), MagicMock()
    pos1.market_value = 150_000.0
    pos2.market_value = 100_000.0
    for p in [pos1, pos2]:
        p.unrealized_pnl = 0.0
        p.quantity = 100.0
        p.avg_cost = 1000.0

    svc = _make_svc(positions=[pos1, pos2])
    summary = svc.get_summary()

    reconstructed = summary.market_value + summary.cash_available
    assert abs(reconstructed - summary.total_equity) < summary.total_equity * 0.001  # within 0.1%


def test_summary_cash_pct_is_fraction_not_percent():
    """cash_pct is a 0–1 fraction; consumers (dashboard endpoint, frontend) ×100."""
    nav = MagicMock()
    nav.total_equity = 1_000_000.0
    nav.market_value = 250_000.0
    nav.unrealized_pnl = 0.0
    nav.cash_balance = 750_000.0
    nav.cash_pct = 0.75

    svc = _make_svc(nav_row=nav)
    summary = svc.get_summary()

    assert summary.cash_pct == pytest.approx(0.75)
    assert 0.0 <= summary.cash_pct <= 1.0


# ── Weight basis (nav_basis / _recompute_weights) ─────────────────────────────


def test_nav_basis_uses_latest_nav_not_seed_equity():
    nav = MagicMock()
    nav.total_equity = 24_200_000.0  # ₹2.42Cr current NAV
    svc = _make_svc(nav_row=nav)  # config seed = ₹10L
    assert svc.nav_basis() == pytest.approx(24_200_000.0)


def test_nav_basis_falls_back_to_config_when_no_nav():
    svc = _make_svc(nav_row=None)
    assert svc.nav_basis() == pytest.approx(1_000_000.0)


def test_nav_basis_falls_back_when_nav_zero():
    nav = MagicMock()
    nav.total_equity = 0.0
    svc = _make_svc(nav_row=nav)
    assert svc.nav_basis() == pytest.approx(1_000_000.0)


def test_recompute_weights_divides_by_nav_not_seed():
    """Regression: weight_pct must use current NAV, not the ₹10L seed equity.

    A ₹24.3L position against a ₹2.42Cr NAV is ~10%, not 243%.
    """
    nav = MagicMock()
    nav.total_equity = 24_200_000.0
    pos = MagicMock()
    pos.market_value = 2_420_000.0

    svc = _make_svc(positions=[pos], nav_row=nav)
    svc._recompute_weights()

    assert pos.weight_pct == pytest.approx(10.0, rel=0.01)
    assert pos.weight_pct < 25.0  # below single-name cap → no phantom breach


def test_recompute_weights_seed_fallback_when_no_nav():
    pos = MagicMock()
    pos.market_value = 200_000.0

    svc = _make_svc(positions=[pos], nav_row=None)  # seed ₹10L
    svc._recompute_weights()

    assert pos.weight_pct == pytest.approx(20.0)


# ── Regime slot enforcement (AC-PE-02) ────────────────────────────────────────


def test_risk_on_allows_5_positions():
    # 5-name concentration: risk_on capped at 5 slots (was 8)
    svc = _make_svc(regime="risk_on")
    limits = svc.get_limits()
    assert limits.max_positions == 5
    assert limits.max_buy_per_day == 2


def test_neutral_allows_5_positions():
    # 5-name concentration: neutral capped at 5 slots (was 6)
    svc = _make_svc(regime="neutral")
    limits = svc.get_limits()
    assert limits.max_positions == 5
    assert limits.max_buy_per_day == 1


def test_defensive_blocks_new_buys():
    svc = _make_svc(regime="defensive")
    limits = svc.get_limits()
    assert limits.max_buy_per_day == 0
    assert limits.can_add_position is False
    assert "REGIME_BLOCK" in (limits.block_reason or "")


def test_portfolio_full_blocks_buy():
    # 6 positions in neutral = full
    positions = [MagicMock() for _ in range(6)]
    for p in positions:
        p.market_value = 100_000.0
        p.unrealized_pnl = 0.0
        p.quantity = 50.0
        p.avg_cost = 2000.0
    svc = _make_svc(positions=positions, regime="neutral")
    limits = svc.get_limits()
    assert limits.slots_available == 0
    assert limits.can_add_position is False
    assert "PORTFOLIO_FULL" in (limits.block_reason or "")


# ── Allocation math ───────────────────────────────────────────────────────────


def test_allocation_high_conviction():
    svc = _make_svc(regime="neutral")
    alloc = svc.compute_allocation("HIGH", last_price=1000.0)
    # deployable=850K, max_slots=5 (5-name concentration) → slot_budget=170,000
    # HIGH weight=1.0 → position_notional=170,000
    assert alloc.conviction_weight == pytest.approx(1.0)
    assert alloc.slot_budget == pytest.approx(850_000 / 5, rel=0.01)
    assert alloc.position_notional == pytest.approx(alloc.slot_budget)
    assert alloc.quantity_estimate == pytest.approx(alloc.position_notional / 1000.0, rel=0.01)


def test_allocation_exceptional_higher_than_high():
    svc = _make_svc(regime="risk_on")
    alloc_e = svc.compute_allocation("EXCEPTIONAL", last_price=1000.0)
    alloc_h = svc.compute_allocation("HIGH", last_price=1000.0)
    assert alloc_e.position_notional > alloc_h.position_notional


def test_allocation_low_conviction_zero():
    svc = _make_svc()
    alloc = svc.compute_allocation("LOW", last_price=1000.0)
    assert alloc.conviction_weight == 0.0
    assert alloc.position_notional == 0.0


def test_single_name_cap_check():
    # 18% of 1M = 180K cap
    svc = _make_svc(regime="neutral")
    alloc = svc.compute_allocation("HIGH", last_price=100.0)
    # slot_budget ~141K < 180K cap → within cap
    assert alloc.within_single_name_cap is True


# ── Regime slots default table ────────────────────────────────────────────────


def test_default_regime_slots_complete():
    for posture in ["risk_on", "neutral", "defensive", "crisis"]:
        assert posture in _DEFAULT_REGIME_SLOTS
        assert "max_positions" in _DEFAULT_REGIME_SLOTS[posture]
        assert "max_buy_per_day" in _DEFAULT_REGIME_SLOTS[posture]


def test_crisis_most_conservative():
    assert (
        _DEFAULT_REGIME_SLOTS["crisis"]["max_positions"]
        < _DEFAULT_REGIME_SLOTS["defensive"]["max_positions"]
    )
    assert _DEFAULT_REGIME_SLOTS["crisis"]["max_buy_per_day"] == 0


# ── No LLM in portfolio service ───────────────────────────────────────────────


def test_no_llm_imports():
    import ast
    import pathlib

    src = pathlib.Path(__file__).parents[3] / "app" / "services" / "portfolio_service.py"
    tree = ast.parse(src.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in getattr(node, "names", [])]
            module = getattr(node, "module", "") or ""
            combined = " ".join(names) + " " + module
            assert "openai" not in combined.lower()
            assert "anthropic" not in combined.lower()
