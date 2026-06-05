"""Conviction scorer v1.1 — deterministic, no LLM, no committee inputs.

Formula (PRD §4, conv_v1.1.0):
  conviction_score = clamp(round(
    0.26 * S_rank_quality
  + 0.32 * S_validation
  + 0.16 * S_ic_factor
  + 0.16 * S_regime
  + 0.10 * S_exit_health
  ), 0, 100)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from app.core.constants import (
    CONVICTION_BLOCKED_MAX_SCORE,
    CONVICTION_CONFIG_VERSION,
    CONVICTION_HIGH_MAX_SCORE,
    CONVICTION_LOW_MAX_SCORE,
    CONVICTION_MEDIUM_MAX_SCORE,
    CONVICTION_TOP_POOL_SIZE,
    ConvictionBand,
)

_WEIGHTS = {
    "rank_quality": 0.26,
    "validation": 0.32,
    "ic_factor": 0.16,
    "regime": 0.16,
    "exit_health": 0.10,
}

RegimePosture = Literal["risk_on", "neutral", "defensive"]
PositionState = Literal["none", "active_clean", "active_deteriorating", "active_decay"]


@dataclass(frozen=True)
class ConvictionInputs:
    rank: int
    composite_score: float
    top20_composite_scores: list[float]
    validation_status: str
    validation_ic_20d: float | None
    validation_top_decile_spread: float | None
    factor_ic_median: float | None
    regime_posture: RegimePosture
    position_state: PositionState
    rank_v2_promoted: bool
    config_version: str = CONVICTION_CONFIG_VERSION


@dataclass
class ConvictionResult:
    score: int
    band: ConvictionBand
    components: dict = field(default_factory=dict)


def _score_rank_quality(inputs: ConvictionInputs) -> float:
    rank = inputs.rank
    scores = inputs.top20_composite_scores

    # Pool membership (0–100)
    if rank <= CONVICTION_TOP_POOL_SIZE:
        pool_score = 100.0
    elif rank <= 50:
        pool_score = 100.0 * (50 - rank) / (50 - CONVICTION_TOP_POOL_SIZE)
    else:
        pool_score = 0.0

    # Separation within top pool
    if scores and inputs.composite_score is not None:
        sorted_scores = sorted(scores)
        below = sum(1 for s in sorted_scores if s < inputs.composite_score)
        separation_score = 100.0 * below / len(sorted_scores)
    else:
        separation_score = 50.0

    # Rank inversion guard (PRD R-ENTRY-06)
    rank_penalty = 0.0
    if not inputs.rank_v2_promoted and 1 <= rank <= 5:
        rank_penalty = min(rank, 5) * 8.0

    raw = 0.6 * pool_score + 0.4 * separation_score - rank_penalty
    return max(0.0, min(100.0, raw))


def _score_validation(inputs: ConvictionInputs) -> float:
    if inputs.validation_status == "insufficient_data":
        return 35.0

    ic = inputs.validation_ic_20d
    if ic is None:
        return 35.0

    if ic <= 0:
        base = 20.0
    elif ic <= 0.05:
        base = 50.0
    else:
        base = 80.0

    spread_bonus = 0.0
    if inputs.validation_top_decile_spread is not None and inputs.validation_top_decile_spread > 0:
        spread_bonus = 10.0

    return min(100.0, base + spread_bonus)


def _score_ic_factor(inputs: ConvictionInputs) -> float:
    ic = inputs.factor_ic_median
    if ic is None:
        return 50.0
    if ic > 0.03:
        return 80.0
    if ic >= 0:
        return 55.0
    return 30.0


def _score_regime(inputs: ConvictionInputs) -> float:
    mapping = {"risk_on": 75.0, "neutral": 55.0, "defensive": 25.0}
    return mapping.get(inputs.regime_posture, 55.0)


def _score_exit_health(inputs: ConvictionInputs) -> float:
    mapping = {
        "none": 70.0,
        "active_clean": 80.0,
        "active_deteriorating": 20.0,
        "active_decay": 15.0,
    }
    return mapping.get(inputs.position_state, 70.0)


def _band_from_score(score: int) -> ConvictionBand:
    if score <= CONVICTION_BLOCKED_MAX_SCORE:
        return ConvictionBand.BLOCKED
    if score <= CONVICTION_LOW_MAX_SCORE:
        return ConvictionBand.LOW
    if score <= CONVICTION_MEDIUM_MAX_SCORE:
        return ConvictionBand.MEDIUM
    if score <= CONVICTION_HIGH_MAX_SCORE:
        return ConvictionBand.HIGH
    return ConvictionBand.EXCEPTIONAL


def score(inputs: ConvictionInputs) -> ConvictionResult:
    s_rank = _score_rank_quality(inputs)
    s_val = _score_validation(inputs)
    s_ic = _score_ic_factor(inputs)
    s_regime = _score_regime(inputs)
    s_exit = _score_exit_health(inputs)

    raw = (
        _WEIGHTS["rank_quality"] * s_rank
        + _WEIGHTS["validation"] * s_val
        + _WEIGHTS["ic_factor"] * s_ic
        + _WEIGHTS["regime"] * s_regime
        + _WEIGHTS["exit_health"] * s_exit
    )
    final_score = max(0, min(100, math.floor(raw + 0.5)))

    # Rank inversion guard: ranks 1–5 without calibration never EXCEPTIONAL
    if not inputs.rank_v2_promoted and 1 <= inputs.rank <= 5:
        band = _band_from_score(final_score)
        if band == ConvictionBand.EXCEPTIONAL:
            final_score = CONVICTION_HIGH_MAX_SCORE  # cap at 84

    band = _band_from_score(final_score)

    components = {
        "rank_quality": round(s_rank, 2),
        "validation": round(s_val, 2),
        "ic_factor": round(s_ic, 2),
        "regime": round(s_regime, 2),
        "exit_health": round(s_exit, 2),
        "weights": _WEIGHTS,
        "config_version": inputs.config_version,
    }
    return ConvictionResult(score=final_score, band=band, components=components)
