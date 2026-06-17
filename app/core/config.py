from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://pipm:pipm@localhost:5432/pipm"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_pre_ping: bool = True

    yahoo_request_timeout_seconds: int = 30
    market_data_default_period: str = "1y"
    # "yahoo" | "kite" — selects the OHLCV data provider for ingestion
    market_data_provider: str = "yahoo"

    ranking_default_strategy: str = "momentum_v1"
    ranking_default_strategy_version: str = "1.0.0"
    ranking_default_benchmark: str = "^NSEI"
    ranking_default_universe_code: str = "PI_PM_CORE"
    ranking_min_history_days: int = 63
    ranking_min_avg_daily_traded_value: float = 10_000_000.0
    ranking_min_stock_price: float = 50.0
    ranking_market_data_source: str = "yahoo"

    validation_high_vol_threshold: float = 0.20

    # ARGS LLM routing — global defaults (per-agent vars override when set)
    # provider: mock | openai | openai_compatible | custom via register_llm_provider()
    args_llm_provider: str = "mock"
    args_llm_default_model: str = "gpt-4o-mini"
    args_llm_openai_api_key: str = ""
    # Backward-compatible generic key name sometimes used in .env files.
    openai_api_key: str = ""
    args_llm_openai_base_url: str = "https://api.openai.com/v1"
    args_llm_timeout_seconds: int = 60
    # TARC
    args_llm_tarc_provider: str = ""
    args_llm_tarc_model: str = ""
    args_llm_tarc_api_key: str = ""
    args_llm_tarc_base_url: str = ""
    args_llm_tarc_timeout_seconds: int = 0
    # FRC
    args_llm_frc_provider: str = ""
    args_llm_frc_model: str = ""
    args_llm_frc_api_key: str = ""
    args_llm_frc_base_url: str = ""
    args_llm_frc_timeout_seconds: int = 0
    # QRC
    args_llm_qrc_provider: str = ""
    args_llm_qrc_model: str = ""
    args_llm_qrc_api_key: str = ""
    args_llm_qrc_base_url: str = ""
    args_llm_qrc_timeout_seconds: int = 0
    # NRCC
    args_llm_nrcc_provider: str = ""
    args_llm_nrcc_model: str = ""
    args_llm_nrcc_api_key: str = ""
    args_llm_nrcc_base_url: str = ""
    args_llm_nrcc_timeout_seconds: int = 0
    # RC
    args_llm_rc_provider: str = ""
    args_llm_rc_model: str = ""
    args_llm_rc_api_key: str = ""
    args_llm_rc_base_url: str = ""
    args_llm_rc_timeout_seconds: int = 0
    # CRO
    args_llm_cro_provider: str = ""
    args_llm_cro_model: str = ""
    args_llm_cro_api_key: str = ""
    args_llm_cro_base_url: str = ""
    args_llm_cro_timeout_seconds: int = 0

    # QRC evidence mode — SQE experiment (default off; legacy brief unchanged when false)
    args_qrc_use_sqe: bool = False

    # Authentication (Track E)
    auth_enabled: bool = True
    jwt_secret_key: str = "change-me-in-production-use-openssl-rand"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 15
    jwt_refresh_token_days: int = 7
    auth_bypass_for_tests: bool = False

    # CORS — comma-separated browser origins (local UI preview + Expo web dev)
    cors_allowed_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:8081,http://127.0.0.1:8081"
    )

    # Execution platform (Track K)
    enable_live_trading: bool = False
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_access_token: str = ""
    # Headless token refresh (daily cron)
    kite_user_id: str = ""
    kite_password: str = ""
    kite_totp_secret: str = ""

    # ── Human-In-The-Loop (HITL) feature flag ────────────────────────────────
    # True  = require explicit human approval before any BUY is executed (default, production)
    # False = auto-approve BUYs after recommendation + committee review (paper trading mode)
    # Set HITL_ENABLED=false in .env to enable autonomous paper trading.
    hitl_enabled: bool = True

    # ── Paper trading mode ────────────────────────────────────────────────────
    # True  = execute paper trades in daily batch when HITL_ENABLED=false
    # False = generate recommendations only, no execution
    paper_trading_enabled: bool = False

    # ── ADR-033: Intraday exit monitor ────────────────────────────────────────
    # T1 intraday price monitor (stop_loss + trailing_stop).
    # For paper mode uses last known close as LTP proxy.
    # For live, inject a real QuoteProvider (Kite adapter).
    intraday_exit_monitor_enabled: bool = False
    intraday_interval_sec: int = 300  # poll cadence when run by a scheduler

    # Advisory stop — creates PENDING exit + notifies owner (HITL required).
    advisory_stop_pct: float = -8.0   # unrealized % vs avg_cost; e.g. -8.0

    # Critical stop — bypasses HITL; only when auto_exit_on_critical_stop=true.
    critical_stop_pct: float = -10.0  # e.g. -10.0

    # Whether the critical stop fires an automatic SELL (no HITL).
    # PO must explicitly enable. Never auto-enabled.
    auto_exit_on_critical_stop: bool = False

    # ── ADR-035: Regime-dynamic stops & time-stop removal (flag-off default) ───
    # When enabled, the advisory stop is resolved per-day from the market regime
    # (regime_history, ^NSEI) via regime_stop_map; critical = advisory + offset.
    # Defaults preserve current behaviour (static advisory/critical, time stop on).
    regime_dynamic_stops_enabled: bool = False
    regime_stop_map: str = (
        '{"BULL_LOW_VOL": -6.0, "BULL_HIGH_VOL": -8.0, '
        '"BEAR_LOW_VOL": -2.0, "BEAR_HIGH_VOL": -3.0}'
    )
    regime_stop_fallback_pct: float = -4.0   # no regime row / unknown label
    regime_critical_offset_pct: float = -2.0  # critical = advisory + this
    # ADR-035 D2: master switch for the 30-day time stop (engine R-EXIT-04 +
    # T2 exit monitor EXIT_TIME). True = current behaviour.
    time_stop_enabled: bool = True

    # ── ADR-034: Recommendation trade levels (deterministic, BUY) ──────────────
    # Entry range + stop-loss range decorated onto BUY recommendations at the
    # recommendation phase. Stops reuse advisory_stop_pct / critical_stop_pct above.
    recommendation_trade_levels_enabled: bool = True
    recommendation_atr_period: int = 14
    recommendation_entry_band_atr_mult: float = 0.5      # half-width = mult × ATR
    recommendation_entry_band_pct_fallback: float = 1.0  # used when ATR unavailable


def parse_cors_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
