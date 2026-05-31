from enum import StrEnum


class TradeSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(StrEnum):
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RankingRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchReportStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"


class DataStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"


class IngestionRunStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IngestPeriod(StrEnum):
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"
    SIX_MONTHS = "6mo"
    ONE_YEAR = "1y"
    FIVE_YEARS = "5y"


class IngestBatchStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"


class IngestionMode(StrEnum):
    FULL_REFRESH = "full_refresh"
    INCREMENTAL = "incremental"
    BACKFILL = "backfill"


class ExperimentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LineageEntityType(StrEnum):
    INGESTION_BATCH = "ingestion_batch"
    INGESTION_SYMBOL = "ingestion_symbol"
    RANKING_RUN = "ranking_run"
    VALIDATION_REPORT = "validation_report"
    EXPERIMENT_RUN = "experiment_run"


class LineageRelationshipType(StrEnum):
    BATCH_SYMBOL = "batch_symbol"
    VALIDATES_RANKING = "validates_ranking"
    EXPERIMENT_RANKING = "experiment_ranking"
    RANKING_INGESTION = "ranking_ingestion"
    POLICY_BACKTEST_USES_VALIDATION = "policy_backtest_uses_validation"


class PolicyAction(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REDUCE = "REDUCE"


class PolicyType(StrEnum):
    BASELINE_E1 = "BASELINE_E1"
    HARD_GATE_E2 = "HARD_GATE_E2"
    SOFT_GATE_E3 = "SOFT_GATE_E3"
    THRESHOLD_GATE_E4 = "THRESHOLD_GATE_E4"


class PolicyConfigStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class RegimeBacktestRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FactorPerformanceRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReplayWindowMode(StrEnum):
    SINGLE_HOLDOUT = "single_holdout"
    ROLLING = "rolling"
    WALK_FORWARD = "walk_forward"


REGIME_BULL_LOW_VOL = "BULL_LOW_VOL"
REGIME_BEAR_LOW_VOL = "BEAR_LOW_VOL"
REGIME_BULL_HIGH_VOL = "BULL_HIGH_VOL"
REGIME_BEAR_HIGH_VOL = "BEAR_HIGH_VOL"

DEFAULT_REGIME_POLICY_HOLDOUT_START = "2025-01-01"


MARKET_DATA_SOURCE_YAHOO = "yahoo"


class SymbolKind(StrEnum):
    EQUITY = "EQUITY"
    INDEX = "INDEX"
    ETF = "ETF"
    UNKNOWN = "UNKNOWN"


EQUITY_SYMBOL_PATTERN = r"^[A-Z0-9]+(\.[A-Z]{1,4})?$"
INDEX_SYMBOL_PATTERN = r"^\^[A-Z0-9]+$"

# Backward-compatible alias for equity-only callers.
SYMBOL_PATTERN = EQUITY_SYMBOL_PATTERN

NORMALIZATION_METHOD_PERCENTILE = "percentile"

RANKING_STRATEGY_MOMENTUM_V1 = "momentum_v1"
RANKING_STRATEGY_MOMENTUM_V1_VERSION = "1.0.0"

RANKING_STRATEGY_BREAKOUT_V1 = "breakout_v1"
RANKING_STRATEGY_BREAKOUT_V1_VERSION = "1.0.0"

BENCHMARK_DEPENDENT_FACTORS = frozenset(
    {"relative_strength", "relative_strength_acceleration"}
)

DEFAULT_MIN_HISTORY_DAYS = 63
DEFAULT_MIN_AVG_DAILY_TRADED_VALUE = 10_000_000
DEFAULT_MIN_STOCK_PRICE = 50

DEFAULT_BENCHMARK_SYMBOL = "^NSEI"

UNIVERSE_NIFTY_500 = "NIFTY_500"
NIFTY500_MIN_BREAKOUT_HISTORY_DAYS = 252

# Exclusion reason codes
EXCLUSION_NOT_IN_UNIVERSE = "NOT_IN_UNIVERSE"
EXCLUSION_STOCK_INACTIVE = "STOCK_INACTIVE"
EXCLUSION_DATA_STATUS_NOT_ACTIVE = "DATA_STATUS_NOT_ACTIVE"
EXCLUSION_INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
EXCLUSION_INSUFFICIENT_TRADED_VALUE = "INSUFFICIENT_TRADED_VALUE"
EXCLUSION_MIN_PRICE_FAILED = "MIN_PRICE_FAILED"
EXCLUSION_NO_PRICE_DATA = "NO_PRICE_DATA"
EXCLUSION_INSUFFICIENT_STRATEGY_HISTORY = "INSUFFICIENT_STRATEGY_HISTORY"
EXCLUSION_FACTOR_COMPUTATION_FAILED = "FACTOR_COMPUTATION_FAILED"
