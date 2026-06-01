from app.workspace_exit_research.constants import (
    FIXED_HOLD_DAYS,
    RANK_EXIT_THRESHOLDS,
    REGIME_EXIT_VARIANTS,
    TREND_FAILURE_VARIANTS,
)


def test_fixed_hold_days_include_user_spec():
    assert FIXED_HOLD_DAYS == (5, 10, 15, 20, 30, 40, 60)


def test_rank_exit_thresholds():
    assert RANK_EXIT_THRESHOLDS == (50, 60, 70, 80, 90)


def test_regime_and_trend_variants_present():
    assert "REGIME_IMMEDIATE" in REGIME_EXIT_VARIANTS
    assert "TREND_DMA20_BREAK" in TREND_FAILURE_VARIANTS
