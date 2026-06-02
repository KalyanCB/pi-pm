from __future__ import annotations

REGIME_LABEL_ALL_REGIMES = "ALL_REGIMES"

SEE_FACTOR_NAMES: tuple[str, ...] = (
    "volume_surge",
    "atr_expansion",
    "trend_quality",
    "high_proximity",
    "relative_strength",
    "consolidation_breakout",
    "volatility_adjusted_momentum",
    "relative_strength_acceleration",
)

DEFAULT_NEAREST_SETUPS = 25
DEFAULT_MIN_SIMILARITY = 0.55
DEFAULT_HISTORY_TRADING_DAYS = 504
DEFAULT_SETUP_SAMPLE_STEP = 5

STOCK_SETUP_STATUS_PENDING = "pending"
STOCK_SETUP_STATUS_RUNNING = "running"
STOCK_SETUP_STATUS_COMPLETED = "completed"
STOCK_SETUP_STATUS_FAILED = "failed"
STOCK_SETUP_STATUS_INSUFFICIENT_DATA = "insufficient_data"
