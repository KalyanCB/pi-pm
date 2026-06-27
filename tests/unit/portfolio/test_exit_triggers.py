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
    # P-20: defensive flip with no per-position signal → safe default exit
    r = check_regime_change(current_regime_posture="defensive", entry_regime_posture="risk_on")
    assert r.fired is True
    assert r.urgency == "HIGH"


def test_regime_defensive_holds_trending_winner():
    # P-20: defensive, but position in profit AND still ranked → held, not dumped
    r = check_regime_change(
        current_regime_posture="defensive", entry_regime_posture="risk_on",
        unrealized_pnl_pct=8.0, current_rank=5,
    )
    assert r.fired is False


def test_regime_defensive_exits_weak_position():
    # P-20: defensive + losing OR rank fallen out of pool → exit
    weak_pnl = check_regime_change("defensive", "risk_on", unrealized_pnl_pct=-2.0, current_rank=5)
    weak_rank = check_regime_change("defensive", "risk_on", unrealized_pnl_pct=8.0, current_rank=40)
    assert weak_pnl.fired is True
    assert weak_rank.fired is True


def test_regime_crisis_critical():
    # Crisis always exits, even a ranked winner
    r = check_regime_change(
        current_regime_posture="crisis", entry_regime_posture="neutral",
        unrealized_pnl_pct=8.0, current_rank=3,
    )
    assert r.fired is True
    assert r.urgency == "CRITICAL"


def test_regime_risk_on_no_fire():
    r = check_regime_change(current_regime_posture="risk_on", entry_regime_posture="neutral")
    assert r.fired is False


# ── intra_bear_hold guard tests (ec8f6bb): hold the dip, but DON'T over-suppress ──
def test_intra_bear_holds_dip_in_unchanged_regime():
    # entered defensive AND still defensive == no regime CHANGE → a transient dip
    # must NOT be cut (218 such cuts sold -0.9% then recovered +2.3%/10d).
    r = check_regime_change("defensive", "defensive", unrealized_pnl_pct=-0.9,
                            current_rank=5, intra_bear_hold=True)
    assert r.fired is False


def test_intra_bear_does_not_block_crisis():
    # GUARD: escalation to crisis still ALWAYS exits, even a bear-entered name.
    r = check_regime_change("crisis", "defensive", unrealized_pnl_pct=-0.9,
                            current_rank=5, intra_bear_hold=True)
    assert r.fired is True


def test_intra_bear_does_not_suppress_real_downgrade():
    # GUARD: a GENUINE regime change (bull-entered → defensive) still cuts a weak
    # name. The hold applies ONLY to bear-entered (entered_defensive) positions.
    r = check_regime_change("defensive", "risk_on", unrealized_pnl_pct=-2.0,
                            current_rank=5, intra_bear_hold=True)
    assert r.fired is True


def test_intra_bear_off_restores_legacy_cut():
    # Sanity: flag off → the bear-entered dip is cut again (old weak_pnl behavior),
    # proving the hold is gated solely by the flag and changes nothing else.
    r = check_regime_change("defensive", "defensive", unrealized_pnl_pct=-0.9,
                            current_rank=5, intra_bear_hold=False)
    assert r.fired is True


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
    # P-02 dynamic trail: max_gain 12% → 8% effective trail. Now +3% = 9% drawback ≥ 8% → fires.
    r = check_trailing_stop(unrealized_pnl_pct=3.0, max_gain_pct=12.0, trailing_stop_pct=5.0)
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
    # P-19: ₹1M position, ADV 10K shares @ ₹20 = ₹200K traded/day → 5 days to unwind.
    # >5 day threshold fires when daily traded value is small relative to position.
    r = check_liquidity(
        avg_daily_volume=2_000, position_value=1_000_000, last_price=20.0,
        liquidity_days_threshold=5.0,
    )
    assert r.fired is True  # 1_000_000 / (2_000 * 20) = 25 days


def test_liquidity_no_fire_liquid():
    # ₹1M position in a name trading 1M shares @ ₹50 = ₹50M/day → 0.02 days. Liquid.
    r = check_liquidity(
        avg_daily_volume=1_000_000, position_value=1_000_000, last_price=50.0,
        liquidity_days_threshold=5.0,
    )
    assert r.fired is False


def test_liquidity_price_invariant_for_rising_winner():
    # P-19 regression: a winner whose price triples must NOT become "more illiquid".
    # Same share count, ADV in shares constant; only price rose.
    low = check_liquidity(avg_daily_volume=50_000, position_value=300_000, last_price=100.0)
    high = check_liquidity(avg_daily_volume=50_000, position_value=900_000, last_price=300.0)
    # position_value scales with price, but so does daily traded value → days_to_unwind equal
    assert low.details["days_to_unwind"] == high.details["days_to_unwind"]


def test_liquidity_fallback_without_price():
    # Backward compat: no last_price → falls back to raw share-volume divisor.
    r = check_liquidity(avg_daily_volume=100_000, position_value=1_000_000)
    assert r.fired is True  # 10 > 5


def test_deterministic_replay():
    a = check_stop_loss(-10.0, -8.0)
    b = check_stop_loss(-10.0, -8.0)
    assert a.fired == b.fired and a.urgency == b.urgency
