"""Regime Conditional Edge Engine (RCEE) — ADR-032.

Determines whether a strategy has statistically supported edge in the current regime.
All gates are individually auditable. No composite scoring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.platform_traceability import StrategyRegimePerformance


class EdgeState(StrEnum):
    EDGE_PRESENT = "EDGE_PRESENT"
    EDGE_PROVISIONAL = "EDGE_PROVISIONAL"  # P-04: early-sample tentative edge
    EDGE_WEAK = "EDGE_WEAK"
    NO_EDGE = "NO_EDGE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RCEEConfig:
    """All RCEE thresholds — config-driven, not hardcoded in gate logic."""

    # EDGE_PRESENT thresholds
    edge_present_ic_lower_95: float = 0.010
    edge_present_hit_rate: float = 0.55
    edge_present_sample_days: int = 60
    # P-18: expectancy route to EDGE_PRESENT. The IC/hit-rate gates are computed at a
    # fixed 20-day horizon, which structurally vetoes short-horizon strategies
    # (reversal_v1, low_vol_v1) whose mean-reversion signal has decayed/inverted by
    # day 20 — even when they are genuinely profitable. A strategy with positive
    # expectancy-after-costs over an adequate sample has *demonstrated* edge in this
    # regime regardless of the 20-day IC sign. This horizon-agnostic route requires the
    # same regime-aware sample floor so a thin/noisy sample cannot trip it.
    edge_present_expectancy_after_costs: float = 0.0
    # ADR-036: per-regime EDGE_PRESENT sample floor. Structurally rare regimes
    # (bear / high-vol) accumulate far fewer regime-days, so the flat 60-day floor
    # suppresses genuinely-significant edge there. ic_lower_95 already gates sample
    # uncertainty (a thin sample widens the CI), so a lower floor for rare regimes
    # does not weaken the significance test. Keys are regime labels; absence falls
    # back to edge_present_sample_days.
    edge_present_sample_days_by_regime: dict[str, int] = field(default_factory=dict)
    # EDGE_WEAK thresholds
    edge_weak_ic_lower_95: float = 0.000
    edge_weak_hit_rate: float = 0.50
    edge_weak_sample_days: int = 30
    # P-04: EDGE_PROVISIONAL — breaks the cold-start deadlock. With only 25-90
    # samples, ic_lower_95 is deeply negative even for a genuinely profitable
    # strategy (wide CI), so nothing ever clears EDGE_PRESENT and the first months
    # produce zero BUYs — which means no trades, hence no data to ever build edge.
    # A barely-not-significantly-negative IC with a >0.52 hit rate over 25-90 samples
    # is allowed to trade tentatively. Disabled once sample_count >= floor.
    provisional_allowed: bool = True
    edge_provisional_ic_lower_95: float = -0.005
    edge_provisional_hit_rate: float = 0.52
    edge_provisional_min_samples: int = 25
    # Cost hurdle (10bps round-trip)
    cost_hurdle: float = 0.001

    def sample_floor_for(self, regime_label: str | None) -> int:
        """EDGE_PRESENT sample floor for a regime (regime-aware, ADR-036)."""
        if regime_label:
            return self.edge_present_sample_days_by_regime.get(
                regime_label.upper(), self.edge_present_sample_days
            )
        return self.edge_present_sample_days


@dataclass(frozen=True)
class RegimeFit:
    """Result of RCEE evaluation for a (strategy, regime) pair.

    Every gate is individually recorded in gate_results for auditability.
    threshold_config captures the exact thresholds that were applied.
    """

    strategy_name: str
    regime_label: str
    avg_ic: float | None
    ic_lower_95: float | None
    hit_rate: float | None
    expectancy: float | None
    expectancy_after_costs: float | None
    sample_days: int
    edge_state: EdgeState
    # Auditability
    threshold_config: dict[str, float]
    gate_results: dict[str, bool]  # gate name → passed/failed


def evaluate(
    *,
    strategy_regime_row: "StrategyRegimePerformance | None",
    config: RCEEConfig,
) -> RegimeFit:
    """Evaluate edge state for a (strategy, regime) row.

    Returns RegimeFit with full gate_results audit trail.
    If row is None, returns UNKNOWN edge state.
    """
    # ADR-036: resolve the EDGE_PRESENT sample floor for this row's regime.
    regime_for_floor = strategy_regime_row.regime_label if strategy_regime_row else None
    present_sample_floor = config.sample_floor_for(regime_for_floor)

    threshold_config = {
        "edge_present_ic_lower_95": config.edge_present_ic_lower_95,
        "edge_present_hit_rate": config.edge_present_hit_rate,
        "edge_present_sample_days": float(present_sample_floor),
        "edge_weak_ic_lower_95": config.edge_weak_ic_lower_95,
        "edge_weak_hit_rate": config.edge_weak_hit_rate,
        "edge_weak_sample_days": float(config.edge_weak_sample_days),
        "cost_hurdle": config.cost_hurdle,
    }

    if strategy_regime_row is None:
        return RegimeFit(
            strategy_name="",
            regime_label="",
            avg_ic=None,
            ic_lower_95=None,
            hit_rate=None,
            expectancy=None,
            expectancy_after_costs=None,
            sample_days=0,
            edge_state=EdgeState.UNKNOWN,
            threshold_config=threshold_config,
            gate_results={},
        )

    row = strategy_regime_row
    ic_lower = float(row.ic_lower_95) if row.ic_lower_95 is not None else -math.inf
    hr = float(row.hit_rate) if row.hit_rate is not None else 0.0
    n = int(row.sample_count)
    avg_ic = float(row.avg_ic) if row.avg_ic is not None else None
    expectancy = float(row.expectancy) if row.expectancy is not None else None
    expectancy_after_costs = (
        float(row.expectancy_after_costs)
        if row.expectancy_after_costs is not None
        else None
    )

    # EDGE_PRESENT gates (sample floor is regime-aware — ADR-036)
    gate_ic_p = ic_lower >= config.edge_present_ic_lower_95
    gate_hr_p = hr >= config.edge_present_hit_rate
    gate_n_p = n >= present_sample_floor

    # P-18: expectancy route — positive expectancy-after-costs over an adequate sample.
    # Horizon-agnostic; unblocks short-horizon strategies the 20-day IC gate vetoes.
    gate_exp_p = (
        expectancy_after_costs is not None
        and expectancy_after_costs > config.edge_present_expectancy_after_costs
    )

    # P-04: EDGE_PROVISIONAL gates — only in the early window (below the floor).
    gate_ic_pv = ic_lower >= config.edge_provisional_ic_lower_95
    gate_hr_pv = hr >= config.edge_provisional_hit_rate
    gate_n_pv = config.edge_provisional_min_samples <= n < present_sample_floor

    # EDGE_WEAK gates
    gate_ic_w = ic_lower >= config.edge_weak_ic_lower_95
    gate_hr_w = hr >= config.edge_weak_hit_rate
    gate_n_w = n >= config.edge_weak_sample_days

    gate_results = {
        "edge_present_ic": gate_ic_p,
        "edge_present_hit_rate": gate_hr_p,
        "edge_present_sample_days": gate_n_p,
        "edge_present_expectancy": gate_exp_p,
        "edge_provisional_ic": gate_ic_pv,
        "edge_provisional_hit_rate": gate_hr_pv,
        "edge_provisional_sample_window": gate_n_pv,
        "edge_weak_ic": gate_ic_w,
        "edge_weak_hit_rate": gate_hr_w,
        "edge_weak_sample_days": gate_n_w,
    }

    # EDGE_PRESENT via either the IC/hit-rate route OR the expectancy route; both
    # require the regime-aware sample floor (gate_n_p) so a thin sample cannot qualify.
    if gate_n_p and ((gate_ic_p and gate_hr_p) or gate_exp_p):
        edge_state = EdgeState.EDGE_PRESENT
    elif config.provisional_allowed and gate_ic_pv and gate_hr_pv and gate_n_pv:
        edge_state = EdgeState.EDGE_PROVISIONAL
    elif gate_ic_w and gate_hr_w and gate_n_w:
        edge_state = EdgeState.EDGE_WEAK
    else:
        edge_state = EdgeState.NO_EDGE

    return RegimeFit(
        strategy_name=row.strategy_name,
        regime_label=row.regime_label,
        avg_ic=avg_ic,
        ic_lower_95=ic_lower if ic_lower != -math.inf else None,
        hit_rate=hr,
        expectancy=expectancy,
        expectancy_after_costs=expectancy_after_costs,
        sample_days=n,
        edge_state=edge_state,
        threshold_config=threshold_config,
        gate_results=gate_results,
    )


def load_regime_fit(
    *,
    db: "Session",
    strategy_name: str,
    strategy_version: str,
    regime_label: str,
    horizon: int,
    config: RCEEConfig,
) -> RegimeFit:
    """Load StrategyRegimePerformance from DB and evaluate edge state.

    Returns RegimeFit with UNKNOWN edge_state if no row exists.
    """
    from sqlalchemy import select

    from app.models.platform_traceability import StrategyRegimePerformance

    row = db.scalar(
        select(StrategyRegimePerformance).where(
            StrategyRegimePerformance.strategy_name == strategy_name,
            StrategyRegimePerformance.strategy_version == strategy_version,
            StrategyRegimePerformance.regime_label == regime_label,
            StrategyRegimePerformance.horizon == horizon,
        )
    )
    return evaluate(strategy_regime_row=row, config=config)
