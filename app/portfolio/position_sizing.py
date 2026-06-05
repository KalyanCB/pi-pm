"""Position sizing — v1 (conviction-weighted slots) and v2 (risk-adjusted).

v1:  position_notional = slot_budget × conviction_weight        (MVP default)
v2:  position_notional = slot_budget × conviction_weight
                         × volatility_factor × liquidity_factor × regime_factor

Both deterministic. No LLM. v2 is feature-flag controlled via
PortfolioConfig.position_sizing_version.
"""
from __future__ import annotations

from dataclasses import dataclass

CONVICTION_WEIGHTS: dict[str, float] = {
    "EXCEPTIONAL": 1.15,
    "HIGH": 1.00,
    "MEDIUM": 0.75,
    "LOW": 0.00,
    "BLOCKED": 0.00,
}


@dataclass
class SizingInputs:
    conviction_band: str
    slot_budget: float
    last_price: float
    # v2 inputs (ignored by v1)
    atr_pct: float | None = None            # ATR as % of price (volatility)
    avg_daily_value: float | None = None    # avg daily traded value (liquidity)
    regime_posture: str = "neutral"
    target_position_value: float | None = None  # for liquidity participation check


@dataclass
class SizingResult:
    version: str
    conviction_weight: float
    volatility_factor: float
    liquidity_factor: float
    regime_factor: float
    position_notional: float
    quantity: float
    factors_applied: dict


def _volatility_factor(atr_pct: float | None) -> float:
    """Reduce notional for high-ATR (volatile) names. 1.0 baseline.

    ATR < 2%  → 1.10 (calm, size up slightly)
    ATR 2–4%  → 1.00 (normal)
    ATR 4–6%  → 0.80
    ATR > 6%  → 0.60 (very volatile, size down)
    """
    if atr_pct is None:
        return 1.0
    if atr_pct < 2.0:
        return 1.10
    if atr_pct < 4.0:
        return 1.00
    if atr_pct < 6.0:
        return 0.80
    return 0.60


def _liquidity_factor(avg_daily_value: float | None, target_value: float | None) -> float:
    """Cap participation vs average daily traded value.

    If target position would be a large fraction of ADV, scale down.
    participation = target_value / avg_daily_value
    """
    if avg_daily_value is None or target_value is None or avg_daily_value <= 0:
        return 1.0
    participation = target_value / avg_daily_value
    if participation < 0.05:
        return 1.0
    if participation < 0.10:
        return 0.85
    if participation < 0.20:
        return 0.65
    return 0.40


def _regime_factor(posture: str) -> float:
    """Scale deployable slice by regime posture."""
    return {
        "risk_on": 1.10,
        "neutral": 1.00,
        "defensive": 0.60,
        "crisis": 0.30,
    }.get(posture, 1.00)


def size_position(inputs: SizingInputs, version: str = "v1") -> SizingResult:
    conviction_weight = CONVICTION_WEIGHTS.get(inputs.conviction_band, 0.0)

    if version == "v2":
        vol_f = _volatility_factor(inputs.atr_pct)
        liq_f = _liquidity_factor(inputs.avg_daily_value, inputs.target_position_value)
        reg_f = _regime_factor(inputs.regime_posture)
    else:
        vol_f = liq_f = reg_f = 1.0

    position_notional = inputs.slot_budget * conviction_weight * vol_f * liq_f * reg_f
    quantity = position_notional / inputs.last_price if inputs.last_price > 0 else 0.0

    return SizingResult(
        version=version,
        conviction_weight=conviction_weight,
        volatility_factor=vol_f,
        liquidity_factor=liq_f,
        regime_factor=reg_f,
        position_notional=round(position_notional, 2),
        quantity=round(quantity, 4),
        factors_applied={
            "conviction_weight": conviction_weight,
            "volatility_factor": vol_f,
            "liquidity_factor": liq_f,
            "regime_factor": reg_f,
        },
    )
