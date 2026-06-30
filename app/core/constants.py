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
    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"
    SIX_MONTHS = "6mo"
    ONE_YEAR = "1y"
    TWO_YEARS = "2y"
    FIVE_YEARS = "5y"
    TEN_YEARS = "10y"
    MAX = "max"


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
    RANKING_RESULT = "ranking_result"
    VALIDATION_REPORT = "validation_report"
    EXPERIMENT_RUN = "experiment_run"
    DAILY_BATCH_RUN = "daily_batch_run"
    FACTOR_PERFORMANCE_RUN = "factor_performance_run"
    EXIT_RESEARCH_RUN = "exit_research_run"
    RESEARCH_INTELLIGENCE_RUN = "research_intelligence_run"
    RESEARCH_RUN = "research_run"
    INVESTMENT_REVIEW_PACKET = "investment_review_packet"
    COMMITTEE_REVIEW = "committee_review"
    CRO_REVIEW = "cro_review"
    GOVERNANCE_RESEARCH_REPORT = "governance_research_report"
    STOCK_SETUP_RESEARCH = "stock_setup_research"
    RECOMMENDATION_RUN = "recommendation_run"


class LineageRelationshipType(StrEnum):
    BATCH_SYMBOL = "batch_symbol"
    VALIDATES_RANKING = "validates_ranking"
    EXPERIMENT_RANKING = "experiment_ranking"
    RANKING_INGESTION = "ranking_ingestion"
    POLICY_BACKTEST_USES_VALIDATION = "policy_backtest_uses_validation"
    DAILY_BATCH_INGESTION = "daily_batch_ingestion"
    DAILY_BATCH_RANKING = "daily_batch_ranking"
    DAILY_BATCH_VALIDATION = "daily_batch_validation"
    DAILY_BATCH_FACTOR_IC = "daily_batch_factor_ic"
    DAILY_BATCH_EXIT_RESEARCH = "daily_batch_exit_research"
    DAILY_BATCH_REGIME_HISTORY = "daily_batch_regime_history"
    DAILY_BATCH_REGIME_PERFORMANCE = "daily_batch_regime_performance"
    RANKING_PRODUCES_PACKET = "ranking_produces_packet"
    RESEARCH_RUN_PRODUCES_PACKET = "research_run_produces_packet"
    PACKET_SOURCES_RANKING_RESULT = "packet_sources_ranking_result"
    PACKET_SOURCES_VALIDATION_REPORT = "packet_sources_validation_report"
    PACKET_REVIEWED_BY_COMMITTEE = "packet_reviewed_by_committee"
    REVIEWS_AGGREGATED_TO_CRO = "reviews_aggregated_to_cro"
    COMMITTEE_REVIEW_AGGREGATED_TO_CRO = "committee_agg_to_cro"
    CRO_ISSUES_GOVERNANCE_REPORT = "cro_issues_governance_report"
    DAILY_BATCH_RESEARCH = "daily_batch_research"
    RANK_RESULT_STOCK_SETUP = "rank_result_stock_setup"
    PACKET_SRC_STOCK_SETUP = "packet_src_stock_setup"
    DAILY_BATCH_RECOMMENDATION = "daily_batch_recommendation"


class DailyBatchRunStatus(StrEnum):
    PENDING = "pending"
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DailyBatchPhase(StrEnum):
    PREFLIGHT = "preflight"
    PLANNING = "planning"
    INGEST = "ingest"
    RANKINGS = "rankings"
    VALIDATION = "validation"
    RECOMMENDATIONS = "recommendations"
    REGIME_HISTORY = "regime_history"
    REGIME_PERFORMANCE = "regime_performance"
    FACTOR_IC = "factor_ic"
    RESEARCH_INTELLIGENCE = "research_intelligence"
    EXIT_RESEARCH = "exit_research"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


class DailyBatchArtifactType(StrEnum):
    INGESTION_BATCH = "ingestion_batch"
    RANKING_RUN = "ranking_run"
    VALIDATION_REPORT = "validation_report"
    RECOMMENDATION_RUN = "recommendation_run"
    FACTOR_PERFORMANCE_RUN = "factor_performance_run"
    REGIME_HISTORY_BACKFILL = "regime_history_backfill"
    REGIME_PERFORMANCE_REFRESH = "regime_performance_refresh"
    EXIT_RESEARCH_RUN = "exit_research_run"
    RESEARCH_INTELLIGENCE_RUN = "research_intelligence_run"


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


class ExitResearchRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExitResearchPhase(StrEnum):
    COLLECTING_ENTRIES = "collecting_entries"
    SIMULATING = "simulating"
    AGGREGATING_METRICS = "aggregating_metrics"
    PERSISTING_POLICY_METRICS = "persisting_policy_metrics"
    PERSISTING_ALPHA_DECAY = "persisting_alpha_decay"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class CommitteeReviewStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"
    TIMEOUT = "timeout"


class ResearchIntelligenceRunStatus(StrEnum):
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
MARKET_DATA_SOURCE_KITE = "kite"


class SymbolKind(StrEnum):
    EQUITY = "EQUITY"
    INDEX = "INDEX"
    ETF = "ETF"
    UNKNOWN = "UNKNOWN"


class RecommendationAction(StrEnum):
    BUY = "BUY"
    WATCH = "WATCH"
    HOLD = "HOLD"
    EXIT_APPROVED = "EXIT_APPROVED"
    REJECT = "REJECT"


class RecommendationLifecycleState(StrEnum):
    CANDIDATE = "CANDIDATE"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    EXIT_APPROVED = "EXIT_APPROVED"
    CLOSED = "CLOSED"


class ConvictionBand(StrEnum):
    BLOCKED = "BLOCKED"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXCEPTIONAL = "EXCEPTIONAL"


class RecommendationRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class ApprovalType(StrEnum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"


class OutcomeStatus(StrEnum):
    OPEN = "OPEN"
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"


# Recommendation reason codes
REC_REASON_RANK_OUTSIDE_POOL = "RANK_OUTSIDE_POOL"
REC_REASON_VALIDATION_PENDING = "VALIDATION_PENDING"
REC_REASON_VALIDATION_WEAK = "VALIDATION_WEAK"
REC_REASON_REGIME_BLOCK = "REGIME_BLOCK"
REC_REASON_CONVICTION_LOW = "CONVICTION_LOW"
REC_REASON_PORTFOLIO_FULL = "PORTFOLIO_FULL"
REC_REASON_EXIT_RISK = "EXIT_RISK"
REC_REASON_INSUFFICIENT_LIQUIDITY = "INSUFFICIENT_LIQUIDITY"
REC_REASON_STALE_CANDIDATE = "STALE_CANDIDATE"
REC_REASON_RANK_POOL_TOP20 = "RANK_POOL_TOP20"
REC_REASON_CROSS_STRATEGY_DUPLICATE = "CROSS_STRATEGY_DUPLICATE"
# ADR-032
REC_REASON_REGIME_NO_EDGE = "REGIME_NO_EDGE"
REC_REASON_PROVISIONAL_EDGE = "PROVISIONAL_EDGE"  # ADR-037 P-04
REC_REASON_LOW_EXPECTANCY = "LOW_EXPECTANCY"
REC_REASON_STALE_AGE = "STALE_AGE"
REC_REASON_RANK_EXITED_POOL = "RANK_EXITED_POOL"
REC_REASON_REGIME_EDGE_LOST = "REGIME_EDGE_LOST"


class RecommendationConfidence(StrEnum):
    EARLY = "EARLY"
    VALIDATED = "VALIDATED"
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    UNKNOWN = "UNKNOWN"

# Conviction config
CONVICTION_ENGINE_VERSION = "rec_v1.0.0"
CONVICTION_CONFIG_VERSION = "conv_v1.1.0"
CONVICTION_TOP_POOL_SIZE = 20
CONVICTION_EXCEPTIONAL_DAILY_CAP = 3
CONVICTION_BLOCKED_MAX_SCORE = 29
CONVICTION_LOW_MAX_SCORE = 49
CONVICTION_MEDIUM_MAX_SCORE = 69
CONVICTION_HIGH_MAX_SCORE = 84

EQUITY_SYMBOL_PATTERN = r"^[A-Z0-9][A-Z0-9&-]*(\.[A-Z]{1,4})?$"
INDEX_SYMBOL_PATTERN = r"^\^[A-Z0-9]+$"

# Backward-compatible alias for equity-only callers.
SYMBOL_PATTERN = EQUITY_SYMBOL_PATTERN

NORMALIZATION_METHOD_PERCENTILE = "percentile"

RANKING_STRATEGY_MOMENTUM_V1 = "momentum_v1"
RANKING_STRATEGY_MOMENTUM_V1_VERSION = "1.0.0"

RANKING_STRATEGY_BREAKOUT_V1 = "breakout_v1"
RANKING_STRATEGY_BREAKOUT_V1_VERSION = "1.0.0"

RANKING_STRATEGY_LOW_VOL_V1 = "low_vol_v1"
RANKING_STRATEGY_LOW_VOL_V1_VERSION = "1.0.0"

RANKING_STRATEGY_REVERSAL_V1 = "reversal_v1"
RANKING_STRATEGY_REVERSAL_V1_VERSION = "1.0.0"

# --- v2 strategies: anticipation-weighted, calibrated on forward IC (2026-06) ---
# v1 strategies loaded heavily on AFTER-the-fact confirmation factors (volume_surge,
# atr_expansion, relative_strength*) which carry NEGATIVE forward IC (you buy the top).
# v2 leads with the EARLY/setup factors that actually predict: consolidation_breakout
# (+0.027 IC, bull), short-term oversold reversion in bear (+2.57% fwd / 59% recover),
# and EARLY momentum (low base, just turning up: +1.75% fwd) — not already-gained.
RANKING_STRATEGY_BREAKOUT_V2 = "breakout_v2"
RANKING_STRATEGY_BREAKOUT_V2_VERSION = "1.0.0"

RANKING_STRATEGY_MOMENTUM_V2 = "momentum_v2"
RANKING_STRATEGY_MOMENTUM_V2_VERSION = "1.0.0"

RANKING_STRATEGY_REVERSION_V2 = "reversion_v2"
RANKING_STRATEGY_REVERSION_V2_VERSION = "1.0.0"

# reversion_v3: PURE deep-oversold bear reversion. v2 failed (bear IC ~0) because its
# `stabilizing` factor backfired (IC -0.024) and it used a 10d horizon. Full-sample
# validation (82 bear weeks) shows the pure crushed signal works: trailing-20d/60d
# return, bottom quintile, ~20d hold -> bear cross-sectional IC ~-0.08 (|0.08| > breakout).
RANKING_STRATEGY_REVERSION_V3 = "reversion_v3"
RANKING_STRATEGY_REVERSION_V3_VERSION = "1.0.0"

# momentum_v3: CLASSIC long-horizon momentum. momentum_v2 failed (IC -0.027) because it
# used a 10d horizon where momentum REVERTS. Full-sample validation: 12mo (252d) trailing
# return -> 60d-fwd, BULL cross-sectional IC +0.075 (stronger than breakout). Needs a
# ~quarter HOLD. Bull-only (bear IC -0.066 = momentum crash).
RANKING_STRATEGY_MOMENTUM_V3 = "momentum_v3"
RANKING_STRATEGY_MOMENTUM_V3_VERSION = "1.0.0"

# breakout_v3: deterministic 2-STATE regime tilt (replaces v2's mono-style + 35% dead
# weight). Per-year top-of-book validation (2021-2025, fwd250) BEATS/matches breakout_v2
# every year; the regime SWITCH earns its keep — no static style wins all regimes.
#   BROAD  market (breadth above trailing median): high_proximity 0.45 + momentum_12m
#          0.35 + trend_efficiency 0.20  (pro-trend; captures broad-bull upside 2021/23)
#   NARROW market (breadth below trailing median): high_proximity 0.55 + low_vol 0.45
#          (defensive; proximity is robust EVERY year, low-vol paid 2022/2024/2025)
# vol_contraction is DROPPED — its forward IC was ~0/negative every year 2021-2025.
RANKING_STRATEGY_BREAKOUT_V3_BROAD = "breakout_v3_broad"
RANKING_STRATEGY_BREAKOUT_V3_BROAD_VERSION = "1.0.0"
RANKING_STRATEGY_BREAKOUT_V3_DEF = "breakout_v3_def"
RANKING_STRATEGY_BREAKOUT_V3_DEF_VERSION = "1.0.0"

BENCHMARK_DEPENDENT_FACTORS = frozenset(
    {"relative_strength", "relative_strength_acceleration"}
)

DEFAULT_MIN_HISTORY_DAYS = 63
DEFAULT_MIN_AVG_DAILY_TRADED_VALUE = 10_000_000
DEFAULT_MIN_STOCK_PRICE = 50

DEFAULT_BENCHMARK_SYMBOL = "^NSEI"

UNIVERSE_NIFTY_500 = "NIFTY_500"
UNIVERSE_NIFTY_1000 = "NIFTY_1000"
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
