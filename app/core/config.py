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


@lru_cache
def get_settings() -> Settings:
    return Settings()
