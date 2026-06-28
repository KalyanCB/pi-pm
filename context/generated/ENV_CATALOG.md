---
generated_at: 2026-06-28T03:28:38Z
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
- `MARKET_DATA_PROVIDER` → `market_data_provider`
- `RANKING_DEFAULT_STRATEGY` → `ranking_default_strategy`
- `RANKING_DEFAULT_STRATEGY_VERSION` → `ranking_default_strategy_version`
- `RANKING_DEFAULT_BENCHMARK` → `ranking_default_benchmark`
- `RANKING_DEFAULT_UNIVERSE_CODE` → `ranking_default_universe_code`
- `RANKING_MIN_HISTORY_DAYS` → `ranking_min_history_days`
- `RANKING_MIN_AVG_DAILY_TRADED_VALUE` → `ranking_min_avg_daily_traded_value`
- `RANKING_MIN_STOCK_PRICE` → `ranking_min_stock_price`
- `RANKING_MARKET_DATA_SOURCE` → `ranking_market_data_source`
- `MEGA_DIVERSIFIER_ENABLED` → `mega_diversifier_enabled`
- `MEGA_MIN_ADTV_INR` → `mega_min_adtv_inr`
- `MEGA_DIVERSIFIER_BEAR_MAX_BUY` → `mega_diversifier_bear_max_buy`
- `MEGA_DIVERSIFIER_CRISIS_MAX_BUY` → `mega_diversifier_crisis_max_buy`
- `MEGA_DIVERSIFIER_TOTAL_SLOTS` → `mega_diversifier_total_slots`
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
- `KITE_USER_ID` → `kite_user_id`
- `KITE_PASSWORD` → `kite_password`
- `KITE_TOTP_SECRET` → `kite_totp_secret`
- `HITL_ENABLED` → `hitl_enabled`
- `PAPER_TRADING_ENABLED` → `paper_trading_enabled`
- `INTRADAY_EXIT_MONITOR_ENABLED` → `intraday_exit_monitor_enabled`
- `INTRADAY_INTERVAL_SEC` → `intraday_interval_sec`
- `GRADUATION_ENABLED` → `graduation_enabled`
- `GRADUATION_WINNER_TRAIL_PCT` → `graduation_winner_trail_pct`
- `RUNNER_TIER_ENABLED` → `runner_tier_enabled`
- `RUNNER_MAX_RANK` → `runner_max_rank`
- `RUNNER_MIN_GAIN_PCT` → `runner_min_gain_pct`
- `RUNNER_TRAIL_PCT` → `runner_trail_pct`
- `ATR_DYNAMIC_EXITS_ENABLED` → `atr_dynamic_exits_enabled`
- `ATR_STOP_MULT_BULL` → `atr_stop_mult_bull`
- `ATR_STOP_MULT_BEAR` → `atr_stop_mult_bear`
- `ATR_TRAIL_MULT_NORMAL` → `atr_trail_mult_normal`
- `ATR_TRAIL_MULT_WINNER` → `atr_trail_mult_winner`
- `ATR_TRAIL_MULT_RUNNER` → `atr_trail_mult_runner`
- `ATR_STOP_FLOOR_PCT` → `atr_stop_floor_pct`
- `ATR_STOP_CAP_PCT` → `atr_stop_cap_pct`
- `ATR_TRAIL_FLOOR_PCT` → `atr_trail_floor_pct`
- `ATR_TRAIL_CAP_PCT` → `atr_trail_cap_pct`
- `GOLD_ROTATION_ENABLED` → `gold_rotation_enabled`
- `GOLD_SYMBOL` → `gold_symbol`
- `GOLD_ALLOC_PCT` → `gold_alloc_pct`
- `GOLD_YIELD_TO_BUYS_ENABLED` → `gold_yield_to_buys_enabled`
- `ADVISORY_STOP_PCT` → `advisory_stop_pct`
- `CRITICAL_STOP_PCT` → `critical_stop_pct`
- `AUTO_EXIT_ON_CRITICAL_STOP` → `auto_exit_on_critical_stop`
- `RCEE_EDGE_PRESENT_SAMPLE_DAYS` → `rcee_edge_present_sample_days`
- `RCEE_RARE_REGIME_SAMPLE_DAYS` → `rcee_rare_regime_sample_days`
- `RCEE_RARE_REGIMES` → `rcee_rare_regimes`
- `REGIME_DYNAMIC_STOPS_ENABLED` → `regime_dynamic_stops_enabled`
- `REGIME_STOP_MAP` → `regime_stop_map`
- `REGIME_STOP_FALLBACK_PCT` → `regime_stop_fallback_pct`
- `REGIME_CRITICAL_OFFSET_PCT` → `regime_critical_offset_pct`
- `TIME_STOP_ENABLED` → `time_stop_enabled`
- `REGIME_EXIT_PER_STOCK_TREND_ENABLED` → `regime_exit_per_stock_trend_enabled`
- `REGIME_EXIT_TREND_SMA_FAST` → `regime_exit_trend_sma_fast`
- `REGIME_EXIT_TREND_SMA_SLOW` → `regime_exit_trend_sma_slow`
- `REGIME_EXIT_INTRA_BEAR_HOLD` → `regime_exit_intra_bear_hold`
- `ALPHA_DECAY_GRACE_DAYS` → `alpha_decay_grace_days`
- `TRANSACTION_COSTS_ENABLED` → `transaction_costs_enabled`
- `COST_STT_BUY_PCT` → `cost_stt_buy_pct`
- `COST_STT_SELL_PCT` → `cost_stt_sell_pct`
- `COST_STAMP_BUY_PCT` → `cost_stamp_buy_pct`
- `COST_EXCHANGE_TXN_PCT` → `cost_exchange_txn_pct`
- `COST_SEBI_PCT` → `cost_sebi_pct`
- `COST_GST_RATE` → `cost_gst_rate`
- `COST_SLIPPAGE_BPS` → `cost_slippage_bps`
- `OHLC_FILLS_ENABLED` → `ohlc_fills_enabled`
- `NEXT_OPEN_FILLS_ENABLED` → `next_open_fills_enabled`
- `ENTRY_BAND_FILLS_ENABLED` → `entry_band_fills_enabled`
- `ENTRY_BAND_FILL_LEVEL` → `entry_band_fill_level`
- `ENTRY_BAND_RETRY_DAYS` → `entry_band_retry_days`
- `FAST_DEPLOY_ENABLED` → `fast_deploy_enabled`
- `FAST_DEPLOY_BUY_MULTIPLIER` → `fast_deploy_buy_multiplier`
- `REALISTIC_FILLS_ENABLED` → `realistic_fills_enabled`
- `INTRADAY_INTERVAL` → `intraday_interval`
- `VWAP_WINDOW_MINUTES` → `vwap_window_minutes`
- `IMPACT_SPREAD_BPS` → `impact_spread_bps`
- `IMPACT_COEFF_BPS` → `impact_coeff_bps`
- `ADV_LOOKBACK_DAYS` → `adv_lookback_days`
- `FAST_DEPLOY_RISK_ON_PCT` → `fast_deploy_risk_on_pct`
- `FAST_DEPLOY_LIMITED_PCT` → `fast_deploy_limited_pct`
- `FAST_DEPLOY_NEUTRAL_PCT` → `fast_deploy_neutral_pct`
- `FAST_DEPLOY_DEFENSIVE_PCT` → `fast_deploy_defensive_pct`
- `GOLD_MIN_PCT` → `gold_min_pct`
- `GOLD_MAX_PCT` → `gold_max_pct`
- `GOLD_BUY_COOLDOWN_DAYS` → `gold_buy_cooldown_days`
- `RECOMMENDATION_TRADE_LEVELS_ENABLED` → `recommendation_trade_levels_enabled`
- `RECOMMENDATION_ATR_PERIOD` → `recommendation_atr_period`
- `RECOMMENDATION_ENTRY_BAND_ATR_MULT` → `recommendation_entry_band_atr_mult`
- `RECOMMENDATION_ENTRY_BAND_PCT_FALLBACK` → `recommendation_entry_band_pct_fallback`