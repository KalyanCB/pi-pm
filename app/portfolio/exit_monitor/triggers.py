"""Exit trigger definitions — pure functions, no DB access.

Each trigger takes position context and returns (fired: bool, details: dict).
All deterministic. No LLM.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerResult:
    fired: bool
    trigger_code: str
    details: dict
    urgency: str = "NORMAL"  # LOW | NORMAL | HIGH | CRITICAL


def check_rank_drop(
    current_rank: int | None,
    entry_rank: int | None,
    rank_deterioration_threshold: int = 40,
    entry_rank_threshold: int = 20,
) -> TriggerResult:
    """EXIT_RANK_DROP: rank fell below threshold (R-EXIT-01)."""
    if current_rank is None:
        return TriggerResult(False, "EXIT_RANK_DROP", {})
    fired = current_rank > rank_deterioration_threshold
    urgency = "HIGH" if current_rank > 60 else "NORMAL"
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_RANK_DROP",
        details={
            "current_rank": current_rank,
            "threshold": rank_deterioration_threshold,
            "entry_rank": entry_rank,
        },
        urgency=urgency,
    )


def check_alpha_decay(
    cum_alpha_at_day: float | None,
    days_held: int,
    decay_threshold_day: int = 15,
    decay_min_alpha: float = 0.0,
) -> TriggerResult:
    """EXIT_ALPHA_DECAY: cumulative alpha turned negative before decay_threshold_day (R-EXIT-02)."""
    if cum_alpha_at_day is None:
        return TriggerResult(False, "EXIT_ALPHA_DECAY", {})
    fired = days_held <= decay_threshold_day and cum_alpha_at_day < decay_min_alpha
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_ALPHA_DECAY",
        details={
            "cum_alpha_pct": cum_alpha_at_day,
            "days_held": days_held,
            "decay_threshold_day": decay_threshold_day,
        },
        urgency="HIGH" if fired else "NORMAL",
    )


def check_regime_change(
    current_regime_posture: str,
    entry_regime_posture: str | None,
) -> TriggerResult:
    """EXIT_REGIME: regime turned defensive or crisis (R-EXIT-03)."""
    fired = current_regime_posture in ("defensive", "crisis")
    urgency = "CRITICAL" if current_regime_posture == "crisis" else ("HIGH" if fired else "NORMAL")
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_REGIME",
        details={
            "current_posture": current_regime_posture,
            "entry_posture": entry_regime_posture,
        },
        urgency=urgency,
    )


def check_time_stop(
    days_held: int,
    max_holding_days: int = 30,
) -> TriggerResult:
    """EXIT_TIME: holding period exceeded swing horizon (R-EXIT-04)."""
    fired = days_held >= max_holding_days
    urgency = "HIGH" if days_held >= max_holding_days + 5 else ("NORMAL" if fired else "LOW")
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_TIME",
        details={"days_held": days_held, "max_holding_days": max_holding_days},
        urgency=urgency,
    )


def check_stop_loss(
    unrealized_pnl_pct: float | None,
    stop_loss_pct: float = -8.0,
) -> TriggerResult:
    """EXIT_STOP_LOSS: position lost more than stop_loss_pct."""
    if unrealized_pnl_pct is None:
        return TriggerResult(False, "EXIT_STOP_LOSS", {})
    fired = unrealized_pnl_pct <= stop_loss_pct
    urgency = (
        "CRITICAL" if unrealized_pnl_pct <= stop_loss_pct * 1.5 else ("HIGH" if fired else "NORMAL")
    )
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_STOP_LOSS",
        details={"unrealized_pnl_pct": unrealized_pnl_pct, "stop_loss_pct": stop_loss_pct},
        urgency=urgency,
    )


def check_trailing_stop(
    unrealized_pnl_pct: float | None,
    max_gain_pct: float | None,
    trailing_stop_pct: float = 5.0,
) -> TriggerResult:
    """EXIT_TRAILING_STOP: position pulled back trailing_stop_pct from peak."""
    if unrealized_pnl_pct is None or max_gain_pct is None or max_gain_pct <= 0:
        return TriggerResult(False, "EXIT_TRAILING_STOP", {})
    drawback = max_gain_pct - unrealized_pnl_pct
    fired = drawback >= trailing_stop_pct and max_gain_pct >= trailing_stop_pct
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_TRAILING_STOP",
        details={
            "max_gain_pct": max_gain_pct,
            "current_pnl_pct": unrealized_pnl_pct,
            "drawback_pct": round(drawback, 2),
            "trailing_stop_pct": trailing_stop_pct,
        },
        urgency="HIGH" if fired else "NORMAL",
    )


def check_concentration(
    weight_pct: float | None,
    single_name_cap_pct: float = 18.0,
) -> TriggerResult:
    """EXIT_CONCENTRATION: position weight exceeds single-name cap."""
    if weight_pct is None:
        return TriggerResult(False, "EXIT_CONCENTRATION", {})
    fired = weight_pct > single_name_cap_pct
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_CONCENTRATION",
        details={"weight_pct": weight_pct, "cap_pct": single_name_cap_pct},
        urgency="HIGH" if weight_pct > single_name_cap_pct * 1.2 else "NORMAL",
    )


def check_liquidity(
    avg_daily_volume: float | None,
    position_value: float | None,
    liquidity_days_threshold: float = 5.0,
) -> TriggerResult:
    """EXIT_LIQUIDITY: position would take too many days to unwind at average volume."""
    if avg_daily_volume is None or position_value is None or avg_daily_volume <= 0:
        return TriggerResult(False, "EXIT_LIQUIDITY", {})
    days_to_unwind = position_value / avg_daily_volume
    fired = days_to_unwind > liquidity_days_threshold
    return TriggerResult(
        fired=fired,
        trigger_code="EXIT_LIQUIDITY",
        details={
            "days_to_unwind": round(days_to_unwind, 1),
            "threshold_days": liquidity_days_threshold,
            "avg_daily_volume": avg_daily_volume,
        },
        urgency="HIGH" if fired else "NORMAL",
    )
