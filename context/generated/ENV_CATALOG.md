---
generated_at: 2026-06-09T00:56:52Z
generator: scripts/generate_context.py
---

# Environment Catalog

> From `app/core/config.py` Settings. See also `.env.example`.

| Env var | Field | Default | Type |
|---------|-------|---------|------|
| `RANKING_DEFAULT_STRATEGY` | `ranking_default_strategy` | `momentum_v1` | <class 'str'> |
| `ARGS_LLM_PROVIDER` | `args_llm_provider` | `mock` | <class 'str'> |
| `ARGS_LLM_DEFAULT_MODEL` | `args_llm_default_model` | `gpt-4o-mini` | <class 'str'> |
| `ARGS_LLM_OPENAI_API_KEY` | `args_llm_openai_api_key` | `` | <class 'str'> |
| `ARGS_LLM_OPENAI_BASE_URL` | `args_llm_openai_base_url` | `https://api.openai.com/v1` | <class 'str'> |
| `ARGS_LLM_TIMEOUT_SECONDS` | `args_llm_timeout_seconds` | `60` | <class 'int'> |
| `ARGS_LLM_TARC_PROVIDER` | `args_llm_tarc_provider` | `` | <class 'str'> |
| `ARGS_LLM_TARC_MODEL` | `args_llm_tarc_model` | `` | <class 'str'> |
| `ARGS_LLM_TARC_API_KEY` | `args_llm_tarc_api_key` | `` | <class 'str'> |
| `ARGS_LLM_TARC_BASE_URL` | `args_llm_tarc_base_url` | `` | <class 'str'> |
| `ARGS_LLM_TARC_TIMEOUT_SECONDS` | `args_llm_tarc_timeout_seconds` | `0` | <class 'int'> |
| `ARGS_LLM_FRC_PROVIDER` | `args_llm_frc_provider` | `` | <class 'str'> |
| `ARGS_LLM_FRC_MODEL` | `args_llm_frc_model` | `` | <class 'str'> |
| `ARGS_LLM_FRC_API_KEY` | `args_llm_frc_api_key` | `` | <class 'str'> |
| `ARGS_LLM_FRC_BASE_URL` | `args_llm_frc_base_url` | `` | <class 'str'> |
| `ARGS_LLM_FRC_TIMEOUT_SECONDS` | `args_llm_frc_timeout_seconds` | `0` | <class 'int'> |
| `ARGS_LLM_QRC_PROVIDER` | `args_llm_qrc_provider` | `` | <class 'str'> |
| `ARGS_LLM_QRC_MODEL` | `args_llm_qrc_model` | `` | <class 'str'> |
| `ARGS_LLM_QRC_API_KEY` | `args_llm_qrc_api_key` | `` | <class 'str'> |
| `ARGS_LLM_QRC_BASE_URL` | `args_llm_qrc_base_url` | `` | <class 'str'> |
| `ARGS_LLM_QRC_TIMEOUT_SECONDS` | `args_llm_qrc_timeout_seconds` | `0` | <class 'int'> |
| `ARGS_LLM_NRCC_PROVIDER` | `args_llm_nrcc_provider` | `` | <class 'str'> |
| `ARGS_LLM_NRCC_MODEL` | `args_llm_nrcc_model` | `` | <class 'str'> |
| `ARGS_LLM_NRCC_API_KEY` | `args_llm_nrcc_api_key` | `` | <class 'str'> |
| `ARGS_LLM_NRCC_BASE_URL` | `args_llm_nrcc_base_url` | `` | <class 'str'> |
| `ARGS_LLM_NRCC_TIMEOUT_SECONDS` | `args_llm_nrcc_timeout_seconds` | `0` | <class 'int'> |
| `ARGS_LLM_RC_PROVIDER` | `args_llm_rc_provider` | `` | <class 'str'> |
| `ARGS_LLM_RC_MODEL` | `args_llm_rc_model` | `` | <class 'str'> |
| `ARGS_LLM_RC_API_KEY` | `args_llm_rc_api_key` | `` | <class 'str'> |
| `ARGS_LLM_RC_BASE_URL` | `args_llm_rc_base_url` | `` | <class 'str'> |
| `ARGS_LLM_RC_TIMEOUT_SECONDS` | `args_llm_rc_timeout_seconds` | `0` | <class 'int'> |
| `ARGS_LLM_CRO_PROVIDER` | `args_llm_cro_provider` | `` | <class 'str'> |
| `ARGS_LLM_CRO_MODEL` | `args_llm_cro_model` | `` | <class 'str'> |
| `ARGS_LLM_CRO_API_KEY` | `args_llm_cro_api_key` | `` | <class 'str'> |
| `ARGS_LLM_CRO_BASE_URL` | `args_llm_cro_base_url` | `` | <class 'str'> |
| `ARGS_LLM_CRO_TIMEOUT_SECONDS` | `args_llm_cro_timeout_seconds` | `0` | <class 'int'> |
| `AUTH_ENABLED` | `auth_enabled` | `True` | <class 'bool'> |
| `ENABLE_LIVE_TRADING` | `enable_live_trading` | `False` | <class 'bool'> |
| `HITL_ENABLED` | `hitl_enabled` | `True` | <class 'bool'> |
| `PAPER_TRADING_ENABLED` | `paper_trading_enabled` | `False` | <class 'bool'> |
| `INTRADAY_EXIT_MONITOR_ENABLED` | `intraday_exit_monitor_enabled` | `False` | <class 'bool'> |
| `ADVISORY_STOP_PCT` | `advisory_stop_pct` | `-8.0` | <class 'float'> |
| `CRITICAL_STOP_PCT` | `critical_stop_pct` | `-10.0` | <class 'float'> |
| `AUTO_EXIT_ON_CRITICAL_STOP` | `auto_exit_on_critical_stop` | `False` | <class 'bool'> |

## All settings fields

- `APP_ENV` → `app_env`
- `DEBUG` → `debug`
- `LOG_LEVEL` → `log_level`
- `DATABASE_URL` → `database_url`
- `DB_POOL_SIZE` → `db_pool_size`
- `DB_MAX_OVERFLOW` → `db_max_overflow`
- `DB_POOL_PRE_PING` → `db_pool_pre_ping`
- `YAHOO_REQUEST_TIMEOUT_SECONDS` → `yahoo_request_timeout_seconds`
- `MARKET_DATA_DEFAULT_PERIOD` → `market_data_default_period`
- `RANKING_DEFAULT_STRATEGY` → `ranking_default_strategy`
- `RANKING_DEFAULT_STRATEGY_VERSION` → `ranking_default_strategy_version`
- `RANKING_DEFAULT_BENCHMARK` → `ranking_default_benchmark`
- `RANKING_DEFAULT_UNIVERSE_CODE` → `ranking_default_universe_code`
- `RANKING_MIN_HISTORY_DAYS` → `ranking_min_history_days`
- `RANKING_MIN_AVG_DAILY_TRADED_VALUE` → `ranking_min_avg_daily_traded_value`
- `RANKING_MIN_STOCK_PRICE` → `ranking_min_stock_price`
- `RANKING_MARKET_DATA_SOURCE` → `ranking_market_data_source`
- `VALIDATION_HIGH_VOL_THRESHOLD` → `validation_high_vol_threshold`
- `ARGS_LLM_PROVIDER` → `args_llm_provider`
- `ARGS_LLM_DEFAULT_MODEL` → `args_llm_default_model`
- `ARGS_LLM_OPENAI_API_KEY` → `args_llm_openai_api_key`
- `OPENAI_API_KEY` → `openai_api_key`
- `ARGS_LLM_OPENAI_BASE_URL` → `args_llm_openai_base_url`
- `ARGS_LLM_TIMEOUT_SECONDS` → `args_llm_timeout_seconds`
- `ARGS_LLM_TARC_PROVIDER` → `args_llm_tarc_provider`
- `ARGS_LLM_TARC_MODEL` → `args_llm_tarc_model`
- `ARGS_LLM_TARC_API_KEY` → `args_llm_tarc_api_key`
- `ARGS_LLM_TARC_BASE_URL` → `args_llm_tarc_base_url`
- `ARGS_LLM_TARC_TIMEOUT_SECONDS` → `args_llm_tarc_timeout_seconds`
- `ARGS_LLM_FRC_PROVIDER` → `args_llm_frc_provider`
- `ARGS_LLM_FRC_MODEL` → `args_llm_frc_model`
- `ARGS_LLM_FRC_API_KEY` → `args_llm_frc_api_key`
- `ARGS_LLM_FRC_BASE_URL` → `args_llm_frc_base_url`
- `ARGS_LLM_FRC_TIMEOUT_SECONDS` → `args_llm_frc_timeout_seconds`
- `ARGS_LLM_QRC_PROVIDER` → `args_llm_qrc_provider`
- `ARGS_LLM_QRC_MODEL` → `args_llm_qrc_model`
- `ARGS_LLM_QRC_API_KEY` → `args_llm_qrc_api_key`
- `ARGS_LLM_QRC_BASE_URL` → `args_llm_qrc_base_url`
- `ARGS_LLM_QRC_TIMEOUT_SECONDS` → `args_llm_qrc_timeout_seconds`
- `ARGS_LLM_NRCC_PROVIDER` → `args_llm_nrcc_provider`
- `ARGS_LLM_NRCC_MODEL` → `args_llm_nrcc_model`
- `ARGS_LLM_NRCC_API_KEY` → `args_llm_nrcc_api_key`
- `ARGS_LLM_NRCC_BASE_URL` → `args_llm_nrcc_base_url`
- `ARGS_LLM_NRCC_TIMEOUT_SECONDS` → `args_llm_nrcc_timeout_seconds`
- `ARGS_LLM_RC_PROVIDER` → `args_llm_rc_provider`
- `ARGS_LLM_RC_MODEL` → `args_llm_rc_model`
- `ARGS_LLM_RC_API_KEY` → `args_llm_rc_api_key`
- `ARGS_LLM_RC_BASE_URL` → `args_llm_rc_base_url`
- `ARGS_LLM_RC_TIMEOUT_SECONDS` → `args_llm_rc_timeout_seconds`
- `ARGS_LLM_CRO_PROVIDER` → `args_llm_cro_provider`
- `ARGS_LLM_CRO_MODEL` → `args_llm_cro_model`
- `ARGS_LLM_CRO_API_KEY` → `args_llm_cro_api_key`
- `ARGS_LLM_CRO_BASE_URL` → `args_llm_cro_base_url`
- `ARGS_LLM_CRO_TIMEOUT_SECONDS` → `args_llm_cro_timeout_seconds`
- `ARGS_QRC_USE_SQE` → `args_qrc_use_sqe`
- `AUTH_ENABLED` → `auth_enabled`
- `JWT_SECRET_KEY` → `jwt_secret_key`
- `JWT_ALGORITHM` → `jwt_algorithm`
- `JWT_ACCESS_TOKEN_MINUTES` → `jwt_access_token_minutes`
- `JWT_REFRESH_TOKEN_DAYS` → `jwt_refresh_token_days`
- `AUTH_BYPASS_FOR_TESTS` → `auth_bypass_for_tests`
- `CORS_ALLOWED_ORIGINS` → `cors_allowed_origins`
- `ENABLE_LIVE_TRADING` → `enable_live_trading`
- `KITE_API_KEY` → `kite_api_key`
- `KITE_API_SECRET` → `kite_api_secret`
- `KITE_ACCESS_TOKEN` → `kite_access_token`
- `HITL_ENABLED` → `hitl_enabled`
- `PAPER_TRADING_ENABLED` → `paper_trading_enabled`
- `INTRADAY_EXIT_MONITOR_ENABLED` → `intraday_exit_monitor_enabled`
- `INTRADAY_INTERVAL_SEC` → `intraday_interval_sec`
- `ADVISORY_STOP_PCT` → `advisory_stop_pct`
- `CRITICAL_STOP_PCT` → `critical_stop_pct`
- `AUTO_EXIT_ON_CRITICAL_STOP` → `auto_exit_on_critical_stop`