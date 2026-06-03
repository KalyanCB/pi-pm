from __future__ import annotations

SEE_ENGINE_VERSION = "see_v2"

REGIME_LABEL_ALL_REGIMES = "ALL_REGIMES"

REGIME_LABELS_V2: tuple[str, ...] = (
    REGIME_LABEL_ALL_REGIMES,
    "BULL_LOW_VOL",
    "BULL_HIGH_VOL",
    "BEAR_LOW_VOL",
    "BEAR_HIGH_VOL",
)

# Breakout factor universe (legacy alias for tests referencing SEE_FACTOR_NAMES).
SEE_FACTOR_NAMES_BREAKOUT: tuple[str, ...] = (
    "volume_surge",
    "atr_expansion",
    "trend_quality",
    "high_proximity",
    "relative_strength",
    "consolidation_breakout",
    "volatility_adjusted_momentum",
    "relative_strength_acceleration",
)

SEE_FACTOR_NAMES_MOMENTUM: tuple[str, ...] = (
    "volatility_adjusted_momentum",
    "volume_expansion",
    "trend_quality",
    "relative_strength",
)

# Backward-compatible alias used by v1 tests.
SEE_FACTOR_NAMES = SEE_FACTOR_NAMES_BREAKOUT

DEFAULT_MIN_SIMILARITY = 0.55
DEFAULT_HISTORY_TRADING_DAYS = 504
DEFAULT_SETUP_SAMPLE_STEP = 5
DEFAULT_MAX_STORED_SETUPS = 100

# nearest_n=0 means no cap on qualifying matches (threshold-only retrieval).
DEFAULT_NEAREST_SETUPS = 0

STOCK_SETUP_STATUS_PENDING = "pending"
STOCK_SETUP_STATUS_RUNNING = "running"
STOCK_SETUP_STATUS_COMPLETED = "completed"
STOCK_SETUP_STATUS_FAILED = "failed"
STOCK_SETUP_STATUS_INSUFFICIENT_DATA = "insufficient_data"
