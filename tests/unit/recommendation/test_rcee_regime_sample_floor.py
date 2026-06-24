"""ADR-036: regime-aware EDGE_PRESENT sample floor in RCEE."""

from dataclasses import dataclass

from app.recommendation.regime_edge_engine import EdgeState, RCEEConfig, evaluate


@dataclass
class _Row:
    """Mimic StrategyRegimePerformance for evaluate()."""
    strategy_name: str
    regime_label: str
    avg_ic: float | None
    ic_lower_95: float | None
    hit_rate: float | None
    sample_count: int
    expectancy: float | None = None
    expectancy_after_costs: float | None = None


# The real reversal_v1 / BEAR_LOW_VOL row: strong edge, but only 53 samples.
def _reversal_bear_row(n: int = 53) -> _Row:
    return _Row(
        strategy_name="reversal_v1",
        regime_label="BEAR_LOW_VOL",
        avg_ic=0.09,
        ic_lower_95=0.072,   # clears EDGE_PRESENT IC bar (>= 0.010)
        hit_rate=0.808,      # clears EDGE_PRESENT hit bar (>= 0.55)
        sample_count=n,
    )


def test_flat_floor_blocks_strong_rare_regime_edge():
    """With the flat 60 floor, n=53 → EDGE_WEAK (the pre-ADR-036 behaviour).
    provisional disabled to isolate the EDGE_PRESENT floor (P-04 would otherwise
    make this strong-IC n=53 row EDGE_PROVISIONAL)."""
    fit = evaluate(
        strategy_regime_row=_reversal_bear_row(53),
        config=RCEEConfig(provisional_allowed=False),
    )
    assert fit.edge_state == EdgeState.EDGE_WEAK
    assert fit.gate_results["edge_present_sample_days"] is False
    # IC and hit gates DID pass — only sample blocked it.
    assert fit.gate_results["edge_present_ic"] is True
    assert fit.gate_results["edge_present_hit_rate"] is True


def test_regime_aware_floor_unblocks_bear_low_vol():
    """ADR-036: rare-regime floor of 45 → n=53 clears → EDGE_PRESENT."""
    cfg = RCEEConfig(edge_present_sample_days_by_regime={"BEAR_LOW_VOL": 45})
    fit = evaluate(strategy_regime_row=_reversal_bear_row(53), config=cfg)
    assert fit.edge_state == EdgeState.EDGE_PRESENT
    assert fit.threshold_config["edge_present_sample_days"] == 45.0


def test_common_regime_floor_unchanged():
    """A BULL_LOW_VOL row (not in the rare map) still uses the flat 60 floor."""
    cfg = RCEEConfig(
        edge_present_sample_days_by_regime={"BEAR_LOW_VOL": 45},
        provisional_allowed=False,  # isolate the EDGE_PRESENT floor boundary
    )
    row = _Row("breakout_v1", "BULL_LOW_VOL", 0.05, 0.04, 0.667, sample_count=55)
    fit = evaluate(strategy_regime_row=row, config=cfg)
    # 55 < 60 → still blocked in the common regime.
    assert fit.edge_state == EdgeState.EDGE_WEAK
    assert fit.threshold_config["edge_present_sample_days"] == 60.0


def test_lower_floor_does_not_rescue_genuinely_weak_edge():
    """A bear strategy with negative IC stays NO_EDGE even with the lower floor."""
    cfg = RCEEConfig(edge_present_sample_days_by_regime={"BEAR_LOW_VOL": 45})
    row = _Row("momentum_v1", "BEAR_LOW_VOL", -0.08, -0.0789, 0.28, sample_count=190)
    fit = evaluate(strategy_regime_row=row, config=cfg)
    assert fit.edge_state == EdgeState.NO_EDGE


def test_sample_floor_for_helper():
    cfg = RCEEConfig(
        edge_present_sample_days=60,
        edge_present_sample_days_by_regime={"BEAR_LOW_VOL": 45},
    )
    assert cfg.sample_floor_for("BEAR_LOW_VOL") == 45
    assert cfg.sample_floor_for("bear_low_vol") == 45  # case-insensitive
    assert cfg.sample_floor_for("BULL_LOW_VOL") == 60
    assert cfg.sample_floor_for(None) == 60
