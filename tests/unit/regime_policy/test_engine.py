from decimal import Decimal

from app.core.constants import (
    PolicyAction,
    PolicyType,
    REGIME_BEAR_LOW_VOL,
    REGIME_BULL_LOW_VOL,
)
from app.regime_policy.engine import PolicyConfigSpec, RegimePolicyEngine, breakout_v1_preset_specs
from app.regime_policy.models import PolicyEvaluationContext


def _spec(policy_type: str, **kwargs) -> PolicyConfigSpec:
    base = breakout_v1_preset_specs()[0]
    defaults = {
        "policy_name": "test",
        "policy_type": policy_type,
        "strategy_name": base.strategy_name,
        "strategy_version": base.strategy_version,
        "allowed_regimes": [REGIME_BULL_LOW_VOL],
        "size_multipliers": {REGIME_BULL_LOW_VOL: 1.0},
        "min_decile": None,
        "max_decile": None,
        "default_action": PolicyAction.BLOCK.value,
    }
    defaults.update(kwargs)
    return PolicyConfigSpec(**defaults)


def test_e1_baseline_allows_all_regimes():
    engine = RegimePolicyEngine()
    config = _spec(PolicyType.BASELINE_E1.value, allowed_regimes=[], default_action=PolicyAction.ALLOW.value)
    for regime in [REGIME_BULL_LOW_VOL, REGIME_BEAR_LOW_VOL, "UNKNOWN"]:
        decision = engine.evaluate_run(config, PolicyEvaluationContext(regime_label=regime))
        assert decision.action == PolicyAction.ALLOW.value
        assert decision.size_multiplier == Decimal("1.0")


def test_e2_hard_gate_blocks_non_bull_low_vol():
    engine = RegimePolicyEngine()
    config = breakout_v1_preset_specs()[1]
    allowed = engine.evaluate_run(config, PolicyEvaluationContext(regime_label=REGIME_BULL_LOW_VOL))
    blocked = engine.evaluate_run(config, PolicyEvaluationContext(regime_label=REGIME_BEAR_LOW_VOL))
    assert allowed.action == PolicyAction.ALLOW.value
    assert blocked.action == PolicyAction.BLOCK.value
    assert blocked.size_multiplier == Decimal("0.0")


def test_e3_soft_gate_scales_non_bull_regimes():
    engine = RegimePolicyEngine()
    config = breakout_v1_preset_specs()[2]
    bull = engine.evaluate_run(config, PolicyEvaluationContext(regime_label=REGIME_BULL_LOW_VOL))
    bear = engine.evaluate_run(config, PolicyEvaluationContext(regime_label=REGIME_BEAR_LOW_VOL))
    assert bull.size_multiplier == Decimal("1.0")
    assert bear.size_multiplier == Decimal("0.5")
    assert bear.action == PolicyAction.REDUCE.value


def test_e4_blocks_non_bull_and_filters_decile():
    engine = RegimePolicyEngine()
    config = breakout_v1_preset_specs()[3]
    blocked = engine.evaluate_run(config, PolicyEvaluationContext(regime_label=REGIME_BEAR_LOW_VOL))
    assert blocked.action == PolicyAction.BLOCK.value

    allowed_stock = engine.evaluate_stock(
        config,
        PolicyEvaluationContext(regime_label=REGIME_BULL_LOW_VOL, decile=1),
    )
    blocked_stock = engine.evaluate_stock(
        config,
        PolicyEvaluationContext(regime_label=REGIME_BULL_LOW_VOL, decile=5),
    )
    assert allowed_stock.action == PolicyAction.ALLOW.value
    assert blocked_stock.action == PolicyAction.BLOCK.value


def test_preset_specs_include_all_four_experiments():
    specs = breakout_v1_preset_specs()
    types = {spec.policy_type for spec in specs}
    assert types == {
        PolicyType.BASELINE_E1.value,
        PolicyType.HARD_GATE_E2.value,
        PolicyType.SOFT_GATE_E3.value,
        PolicyType.THRESHOLD_GATE_E4.value,
    }
