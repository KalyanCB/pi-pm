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
    # EDGE_WEAK thresholds
    edge_weak_ic_lower_95: float = 0.000
    edge_weak_hit_rate: float = 0.50
    edge_weak_sample_days: int = 30
    # Cost hurdle (10bps round-trip)
    cost_hurdle: float = 0.001


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
    threshold_config = {
        "edge_present_ic_lower_95": config.edge_present_ic_lower_95,
        "edge_present_hit_rate": config.edge_present_hit_rate,
        "edge_present_sample_days": float(config.edge_present_sample_days),
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

    # EDGE_PRESENT gates
    gate_ic_p = ic_lower >= config.edge_present_ic_lower_95
    gate_hr_p = hr >= config.edge_present_hit_rate
    gate_n_p = n >= config.edge_present_sample_days

    # EDGE_WEAK gates
    gate_ic_w = ic_lower >= config.edge_weak_ic_lower_95
    gate_hr_w = hr >= config.edge_weak_hit_rate
    gate_n_w = n >= config.edge_weak_sample_days

    gate_results = {
        "edge_present_ic": gate_ic_p,
        "edge_present_hit_rate": gate_hr_p,
        "edge_present_sample_days": gate_n_p,
        "edge_weak_ic": gate_ic_w,
        "edge_weak_hit_rate": gate_hr_w,
        "edge_weak_sample_days": gate_n_w,
    }

    if gate_ic_p and gate_hr_p and gate_n_p:
        edge_state = EdgeState.EDGE_PRESENT
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
