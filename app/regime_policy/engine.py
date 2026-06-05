from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.core.constants import (
    REGIME_BEAR_HIGH_VOL,
    REGIME_BEAR_LOW_VOL,
    REGIME_BULL_HIGH_VOL,
    REGIME_BULL_LOW_VOL,
    PolicyAction,
    PolicyType,
)
from app.regime_policy.models import PolicyDecision, PolicyEvaluationContext


@dataclass(frozen=True)
class PolicyConfigSpec:
    policy_name: str
    policy_type: str
    strategy_name: str
    strategy_version: str
    allowed_regimes: list[str]
    size_multipliers: dict[str, float]
    min_decile: int | None
    max_decile: int | None
    default_action: str
    notes: str | None = None


class RegimePolicyEngine:
    """Deterministic regime policy evaluation. No DB access."""

    def evaluate_run(
        self,
        config: PolicyConfigSpec,
        context: PolicyEvaluationContext,
    ) -> PolicyDecision:
        regime = context.regime_label or "UNKNOWN"
        if config.policy_type == PolicyType.BASELINE_E1.value:
            return PolicyDecision(
                action=PolicyAction.ALLOW.value,
                size_multiplier=Decimal("1.0"),
                reason="E1 baseline: no gating",
            )

        if config.policy_type == PolicyType.HARD_GATE_E2.value:
            if regime in config.allowed_regimes:
                return PolicyDecision(
                    action=PolicyAction.ALLOW.value,
                    size_multiplier=Decimal("1.0"),
                    reason=f"E2 hard gate: {regime} allowed",
                )
            return PolicyDecision(
                action=PolicyAction.BLOCK.value,
                size_multiplier=Decimal("0.0"),
                reason=f"E2 hard gate: {regime} blocked",
            )

        if config.policy_type == PolicyType.SOFT_GATE_E3.value:
            multiplier = Decimal(str(config.size_multipliers.get(regime, 0.5)))
            return PolicyDecision(
                action=PolicyAction.REDUCE.value
                if multiplier < Decimal("1.0")
                else PolicyAction.ALLOW.value,
                size_multiplier=multiplier,
                reason=f"E3 soft gate: {regime} size_multiplier={multiplier}",
            )

        if config.policy_type == PolicyType.THRESHOLD_GATE_E4.value:
            if regime not in config.allowed_regimes:
                return PolicyDecision(
                    action=PolicyAction.BLOCK.value,
                    size_multiplier=Decimal("0.0"),
                    reason=f"E4 threshold gate: {regime} blocked (BULL_LOW_VOL only)",
                )
            return PolicyDecision(
                action=PolicyAction.ALLOW.value,
                size_multiplier=Decimal("1.0"),
                reason=f"E4 threshold gate: {regime} allowed, top decile only",
                decile_filter=config.min_decile,
            )

        if regime in config.allowed_regimes or not config.allowed_regimes:
            multiplier = Decimal(str(config.size_multipliers.get(regime, 1.0)))
            return PolicyDecision(
                action=PolicyAction.ALLOW.value,
                size_multiplier=multiplier,
                reason=f"Custom policy: {regime} allowed",
            )
        if config.default_action == PolicyAction.BLOCK.value:
            return PolicyDecision(
                action=PolicyAction.BLOCK.value,
                size_multiplier=Decimal("0.0"),
                reason=f"Custom policy: {regime} blocked by default",
            )
        return PolicyDecision(
            action=PolicyAction.ALLOW.value,
            size_multiplier=Decimal("1.0"),
            reason=f"Custom policy: {regime} default allow",
        )

    def evaluate_stock(
        self,
        config: PolicyConfigSpec,
        context: PolicyEvaluationContext,
    ) -> PolicyDecision:
        run_decision = self.evaluate_run(config, context)
        if run_decision.action == PolicyAction.BLOCK.value:
            return run_decision

        if config.policy_type != PolicyType.THRESHOLD_GATE_E4.value:
            return run_decision

        decile = context.decile
        min_decile = config.min_decile or 1
        max_decile = config.max_decile or 1
        if decile is None:
            return PolicyDecision(
                action=PolicyAction.BLOCK.value,
                size_multiplier=Decimal("0.0"),
                reason="E4: missing decile assignment",
                decile_filter=min_decile,
            )
        if min_decile <= decile <= max_decile:
            return PolicyDecision(
                action=PolicyAction.ALLOW.value,
                size_multiplier=run_decision.size_multiplier,
                reason=f"E4: decile {decile} within [{min_decile}, {max_decile}]",
                decile_filter=decile,
            )
        return PolicyDecision(
            action=PolicyAction.BLOCK.value,
            size_multiplier=Decimal("0.0"),
            reason=f"E4: decile {decile} outside [{min_decile}, {max_decile}]",
            decile_filter=decile,
        )


def breakout_v1_preset_specs() -> list[PolicyConfigSpec]:
    strategy_name = "breakout_v1"
    strategy_version = "1.0.0"
    all_regimes = [
        REGIME_BULL_LOW_VOL,
        REGIME_BEAR_LOW_VOL,
        REGIME_BULL_HIGH_VOL,
        REGIME_BEAR_HIGH_VOL,
    ]
    return [
        PolicyConfigSpec(
            policy_name="breakout_v1_baseline_e1",
            policy_type=PolicyType.BASELINE_E1.value,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            allowed_regimes=list(all_regimes),
            size_multipliers={regime: 1.0 for regime in all_regimes},
            min_decile=None,
            max_decile=None,
            default_action=PolicyAction.ALLOW.value,
            notes="E1 baseline: no gating",
        ),
        PolicyConfigSpec(
            policy_name="breakout_v1_hard_gate_e2",
            policy_type=PolicyType.HARD_GATE_E2.value,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            allowed_regimes=[REGIME_BULL_LOW_VOL],
            size_multipliers={REGIME_BULL_LOW_VOL: 1.0},
            min_decile=None,
            max_decile=None,
            default_action=PolicyAction.BLOCK.value,
            notes="E2 hard gate: BULL_LOW_VOL only",
        ),
        PolicyConfigSpec(
            policy_name="breakout_v1_soft_gate_e3",
            policy_type=PolicyType.SOFT_GATE_E3.value,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            allowed_regimes=list(all_regimes),
            size_multipliers={
                REGIME_BULL_LOW_VOL: 1.0,
                REGIME_BEAR_LOW_VOL: 0.5,
                REGIME_BULL_HIGH_VOL: 0.5,
                REGIME_BEAR_HIGH_VOL: 0.5,
            },
            min_decile=None,
            max_decile=None,
            default_action=PolicyAction.ALLOW.value,
            notes="E3 soft gate: 100% BULL_LOW_VOL, 50% elsewhere",
        ),
        PolicyConfigSpec(
            policy_name="breakout_v1_threshold_gate_e4",
            policy_type=PolicyType.THRESHOLD_GATE_E4.value,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            allowed_regimes=[REGIME_BULL_LOW_VOL],
            size_multipliers={REGIME_BULL_LOW_VOL: 1.0},
            min_decile=1,
            max_decile=1,
            default_action=PolicyAction.BLOCK.value,
            notes="E4 experimental: BULL_LOW_VOL + top decile only",
        ),
    ]
