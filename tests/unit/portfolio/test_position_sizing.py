"""Position sizing v1/v2 tests — WS5."""
import pytest

from app.portfolio.position_sizing import SizingInputs, size_position


def test_v1_ignores_risk_factors():
    inputs = SizingInputs(
        conviction_band="HIGH", slot_budget=100_000, last_price=1000,
        atr_pct=8.0, avg_daily_value=10_000, regime_posture="defensive",
        target_position_value=100_000,
    )
    r = size_position(inputs, version="v1")
    assert r.volatility_factor == 1.0
    assert r.liquidity_factor == 1.0
    assert r.regime_factor == 1.0
    assert r.position_notional == pytest.approx(100_000)  # 100K × 1.0


def test_v1_conviction_weight():
    inputs = SizingInputs(conviction_band="MEDIUM", slot_budget=100_000, last_price=1000)
    r = size_position(inputs, version="v1")
    assert r.conviction_weight == 0.75
    assert r.position_notional == pytest.approx(75_000)


def test_v2_applies_volatility_factor():
    # High ATR (8%) → 0.60 vol factor
    inputs = SizingInputs(
        conviction_band="HIGH", slot_budget=100_000, last_price=1000,
        atr_pct=8.0, regime_posture="neutral",
    )
    r = size_position(inputs, version="v2")
    assert r.volatility_factor == 0.60
    assert r.position_notional == pytest.approx(60_000)  # 100K × 1.0 × 0.6 × 1.0 × 1.0


def test_v2_regime_scales_down_defensive():
    inputs = SizingInputs(
        conviction_band="HIGH", slot_budget=100_000, last_price=1000,
        atr_pct=3.0, regime_posture="defensive",
    )
    r = size_position(inputs, version="v2")
    assert r.regime_factor == 0.60
    # 100K × 1.0 × 1.0 (atr 3%) × 1.0 (no liquidity) × 0.6 = 60K
    assert r.position_notional == pytest.approx(60_000)


def test_v2_liquidity_scales_down_thin():
    inputs = SizingInputs(
        conviction_band="HIGH", slot_budget=100_000, last_price=1000,
        atr_pct=3.0, avg_daily_value=400_000, regime_posture="neutral",
        target_position_value=100_000,  # 25% participation → 0.40
    )
    r = size_position(inputs, version="v2")
    assert r.liquidity_factor == 0.40


def test_v2_calm_liquid_risk_on_sizes_up():
    inputs = SizingInputs(
        conviction_band="HIGH", slot_budget=100_000, last_price=1000,
        atr_pct=1.0, avg_daily_value=100_000_000, regime_posture="risk_on",
        target_position_value=100_000,
    )
    r = size_position(inputs, version="v2")
    # 1.0 conviction × 1.10 vol × 1.0 liq × 1.10 regime = 1.21
    assert r.position_notional == pytest.approx(121_000)


def test_low_conviction_zero_regardless_of_version():
    for v in ("v1", "v2"):
        inputs = SizingInputs(conviction_band="LOW", slot_budget=100_000, last_price=1000)
        r = size_position(inputs, version=v)
        assert r.position_notional == 0.0


def test_deterministic():
    inputs = SizingInputs(
        conviction_band="EXCEPTIONAL", slot_budget=120_000, last_price=500,
        atr_pct=2.5, avg_daily_value=5_000_000, regime_posture="neutral",
        target_position_value=120_000,
    )
    r1 = size_position(inputs, version="v2")
    r2 = size_position(inputs, version="v2")
    assert r1.position_notional == r2.position_notional
    assert r1.quantity == r2.quantity
