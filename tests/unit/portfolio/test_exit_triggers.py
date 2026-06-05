"""Exit trigger tests — AC-PE-10."""
from app.portfolio.exit_monitor.triggers import (
    check_alpha_decay,
    check_concentration,
    check_liquidity,
    check_rank_drop,
    check_regime_change,
    check_stop_loss,
    check_time_stop,
    check_trailing_stop,
)


def test_rank_drop_fires_above_threshold():
    r = check_rank_drop(current_rank=45, entry_rank=10, rank_deterioration_threshold=40)
    assert r.fired is True
    assert r.trigger_code == "EXIT_RANK_DROP"
    assert r.details["current_rank"] == 45


def test_rank_drop_no_fire_within_threshold():
    r = check_rank_drop(current_rank=15, entry_rank=10, rank_deterioration_threshold=40)
    assert r.fired is False


def test_rank_drop_none_rank():
    r = check_rank_drop(current_rank=None, entry_rank=10)
    assert r.fired is False


def test_alpha_decay_fires_negative_early():
    r = check_alpha_decay(cum_alpha_at_day=-2.0, days_held=10, decay_threshold_day=15)
    assert r.fired is True
    assert r.urgency == "HIGH"


def test_alpha_decay_no_fire_positive():
    r = check_alpha_decay(cum_alpha_at_day=3.0, days_held=10)
    assert r.fired is False


def test_alpha_decay_no_fire_after_window():
    r = check_alpha_decay(cum_alpha_at_day=-2.0, days_held=20, decay_threshold_day=15)
    assert r.fired is False


def test_regime_defensive_fires():
    r = check_regime_change(current_regime_posture="defensive", entry_regime_posture="risk_on")
    assert r.fired is True
    assert r.urgency == "HIGH"


def test_regime_crisis_critical():
    r = check_regime_change(current_regime_posture="crisis", entry_regime_posture="neutral")
    assert r.fired is True
    assert r.urgency == "CRITICAL"


def test_regime_risk_on_no_fire():
    r = check_regime_change(current_regime_posture="risk_on", entry_regime_posture="neutral")
    assert r.fired is False


def test_time_stop_fires():
    r = check_time_stop(days_held=30, max_holding_days=30)
    assert r.fired is True


def test_time_stop_no_fire():
    r = check_time_stop(days_held=20, max_holding_days=30)
    assert r.fired is False


def test_stop_loss_fires():
    r = check_stop_loss(unrealized_pnl_pct=-10.0, stop_loss_pct=-8.0)
    assert r.fired is True
    assert r.urgency in ("HIGH", "CRITICAL")


def test_stop_loss_critical():
    r = check_stop_loss(unrealized_pnl_pct=-15.0, stop_loss_pct=-8.0)
    assert r.fired is True
    assert r.urgency == "CRITICAL"


def test_stop_loss_no_fire():
    r = check_stop_loss(unrealized_pnl_pct=-3.0, stop_loss_pct=-8.0)
    assert r.fired is False


def test_trailing_stop_fires():
    # peaked at +12%, now +6% → 6% drawback ≥ 5% trailing
    r = check_trailing_stop(unrealized_pnl_pct=6.0, max_gain_pct=12.0, trailing_stop_pct=5.0)
    assert r.fired is True


def test_trailing_stop_no_fire_small_gain():
    # peaked at +3%, never reached trailing threshold
    r = check_trailing_stop(unrealized_pnl_pct=1.0, max_gain_pct=3.0, trailing_stop_pct=5.0)
    assert r.fired is False


def test_concentration_fires():
    r = check_concentration(weight_pct=22.0, single_name_cap_pct=18.0)
    assert r.fired is True


def test_concentration_no_fire():
    r = check_concentration(weight_pct=15.0, single_name_cap_pct=18.0)
    assert r.fired is False


def test_liquidity_fires_thin():
    # position worth 1M, ADV 100K → 10 days to unwind > 5 day threshold
    r = check_liquidity(avg_daily_volume=100_000, position_value=1_000_000, liquidity_days_threshold=5.0)
    assert r.fired is True


def test_liquidity_no_fire_liquid():
    r = check_liquidity(avg_daily_volume=10_000_000, position_value=1_000_000, liquidity_days_threshold=5.0)
    assert r.fired is False


def test_deterministic_replay():
    a = check_stop_loss(-10.0, -8.0)
    b = check_stop_loss(-10.0, -8.0)
    assert a.fired == b.fired and a.urgency == b.urgency
