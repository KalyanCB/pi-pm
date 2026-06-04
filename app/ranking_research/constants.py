from __future__ import annotations

from app.outcome_attribution.constants import ATTRIBUTION_HORIZONS, REGIME_LABEL_ALL
from app.validation.constants import VALIDATION_HORIZONS

RESEARCH_HORIZONS: tuple[int, ...] = VALIDATION_HORIZONS

RANK_MIN = 1
RANK_MAX = 20
EXACT_RANKS: tuple[int, ...] = tuple(range(RANK_MIN, RANK_MAX + 1))

REGIME_LABELS: tuple[str, ...] = (
    "BULL_LOW_VOL",
    "BULL_HIGH_VOL",
    "BEAR_LOW_VOL",
    "BEAR_HIGH_VOL",
)

# Cliff: alpha improvement from rank k to k+1 exceeds this (20d, fraction)
CLIFF_ALPHA_JUMP_THRESHOLD = 0.003

# Noisy band: |alpha| below this with sufficient samples
NOISY_ALPHA_ABS_THRESHOLD = 0.001

MIN_OBS_FOR_RANK_ANALYSIS = 5
MIN_OBS_FOR_FACTOR_ANALYSIS = 10

# Calibration weights (research only — not deployed)
DEFAULT_CALIBRATION_WEIGHTS = {
    "raw_score": 1.0,
    "regime_reliability": 0.15,
    "factor_reliability": 0.10,
    "historical_rank_reliability": 0.20,
}

FACTOR_KEYS_MOMENTUM = (
    "volatility_adjusted_momentum",
    "volume_expansion",
    "trend_quality",
    "relative_strength",
)

FACTOR_KEYS_BREAKOUT = (
    "volatility_adjusted_momentum",
    "relative_strength",
    "trend_quality",
    "volume_surge",
    "high_proximity",
    "atr_expansion",
    "relative_strength_acceleration",
    "consolidation_breakout",
)

STRATEGY_FACTOR_KEYS: dict[str, tuple[str, ...]] = {
    "momentum_v1": FACTOR_KEYS_MOMENTUM,
    "breakout_v1": FACTOR_KEYS_BREAKOUT,
}

# Top-20 composite score buckets (label, inclusive low, exclusive high)
SCORE_BUCKET_SPECS: tuple[tuple[str, float, float], ...] = (
    ("score_ge_0.97", 0.97, 1.01),
    ("score_0.94_0.97", 0.94, 0.97),
    ("score_0.92_0.94", 0.92, 0.94),
    ("score_0.90_0.92", 0.90, 0.92),
    ("score_lt_0.90", 0.0, 0.90),
)

__all__ = [
    "ATTRIBUTION_HORIZONS",
    "REGIME_LABEL_ALL",
    "RESEARCH_HORIZONS",
    "EXACT_RANKS",
    "REGIME_LABELS",
    "SCORE_BUCKET_SPECS",
    "STRATEGY_FACTOR_KEYS",
]
