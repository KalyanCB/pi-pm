---
generated_at: 2026-06-07T03:43:13Z
generator: scripts/generate_context.py
---

# Test Coverage Map

> Test files grouped by module area.

## `args`

- `tests/unit/args/test_committee_effectiveness.py`
- `tests/unit/args/test_committee_evidence_enforcement.py`
- `tests/unit/args/test_committee_packet_views.py`
- `tests/unit/args/test_committee_registry.py`
- `tests/unit/args/test_cro_no_trade_fields.py`
- `tests/unit/args/test_evidence_validator.py`
- `tests/unit/args/test_llm_registry.py`
- `tests/unit/args/test_packet_builder.py`
- `tests/unit/args/test_packet_evidence_coverage.py`
- `tests/unit/args/test_packet_schema.py`
- `tests/unit/args/test_qrc_sqe_brief.py`
- `tests/unit/args/test_qrc_sqe_flag.py`
- … +5 more

## `auth`

- `tests/unit/auth/test_constants.py`
- `tests/unit/auth/test_jwt.py`

## `backtest`

- `tests/unit/backtest/test_ranking_replayer.py`
- `tests/unit/backtest/test_trading_calendar.py`

## `copilot`

- `tests/unit/copilot/test_citations.py`
- `tests/unit/copilot/test_copilot_service.py`
- `tests/unit/copilot/test_intent.py`
- `tests/unit/copilot/test_lineage.py`

## `core`

- `tests/unit/core/test_symbols.py`

## `execution`

- `tests/unit/execution/test_execution_service.py`
- `tests/unit/execution/test_state_machine.py`
- `tests/unit/execution/test_zerodha_adapter.py`

## `factor_analytics`

- `tests/unit/factor_analytics/test_daily_upsert.py`
- `tests/unit/factor_analytics/test_label_column_lengths.py`
- `tests/unit/factor_analytics/test_metrics_engine.py`
- `tests/unit/factor_analytics/test_observation_loader.py`
- `tests/unit/factor_analytics/test_reports.py`
- `tests/unit/factor_analytics/test_service_backfill.py`
- `tests/unit/factor_analytics/test_weight_resolver.py`
- `tests/unit/factor_analytics/test_window.py`

## `integration/api`

- `tests/integration/api/test_auth_api.py`
- `tests/integration/api/test_backtest_api.py`
- `tests/integration/api/test_exit_and_research_api.py`
- `tests/integration/api/test_factor_analytics_api.py`
- `tests/integration/api/test_full_universe_validation_api.py`
- `tests/integration/api/test_market_data_api.py`
- `tests/integration/api/test_rankings_api.py`
- `tests/integration/api/test_regime_policy_api.py`
- `tests/integration/api/test_stock_setup_research_api.py`
- `tests/integration/api/test_tenant_isolation.py`
- `tests/integration/api/test_validation_api.py`

## `integration/args`

- `tests/integration/args/test_lineage.py`
- `tests/integration/args/test_lineage_chain.py`
- `tests/integration/args/test_packet_sqe.py`
- `tests/integration/args/test_research_api.py`

## `investment_committee`

- `tests/unit/investment_committee/test_advisory.py`
- `tests/unit/investment_committee/test_persistence.py`

## `market_data`

- `tests/unit/market_data/test_market_data_cache.py`

## `ops`

- `tests/unit/ops/test_daily_batch_planner.py`
- `tests/unit/ops/test_daily_batch_portfolio_schema.py`
- `tests/unit/ops/test_evidence_windows.py`
- `tests/unit/ops/test_paper_pilot_ops.py`
- `tests/unit/ops/test_pilot_alerting.py`
- `tests/unit/ops/test_pilot_command_center.py`

## `other`

- `tests/test_health.py`
- `tests/test_platform.py`

## `outcome_attribution`

- `tests/unit/outcome_attribution/test_service.py`
- `tests/unit/outcome_attribution/test_statistics.py`

## `portfolio`

- `tests/unit/portfolio/test_analytics.py`
- `tests/unit/portfolio/test_exit_triggers.py`
- `tests/unit/portfolio/test_intraday_exit_monitor.py`
- `tests/unit/portfolio/test_portfolio_service.py`
- `tests/unit/portfolio/test_position_sizing.py`
- `tests/unit/portfolio/test_reconciliation.py`

## `providers`

- `tests/unit/providers/test_yahoo_client.py`

## `ranking`

- `tests/unit/ranking/test_breakout_v1.py`
- `tests/unit/ranking/test_engine.py`
- `tests/unit/ranking/test_golden_ranking.py`
- `tests/unit/ranking/test_low_vol_v1.py`
- `tests/unit/ranking/test_momentum_v1.py`
- `tests/unit/ranking/test_normalizer.py`
- `tests/unit/ranking/test_reversal_v1.py`

## `ranking/factors`

- `tests/unit/ranking/factors/test_atr_expansion.py`
- `tests/unit/ranking/factors/test_consolidation_breakout.py`
- `tests/unit/ranking/factors/test_high_proximity.py`
- `tests/unit/ranking/factors/test_relative_strength_acceleration.py`
- `tests/unit/ranking/factors/test_volume_surge.py`

## `ranking_research`

- `tests/unit/ranking_research/test_backtest.py`
- `tests/unit/ranking_research/test_calibration.py`
- `tests/unit/ranking_research/test_rank_reliability.py`
- `tests/unit/ranking_research/test_root_cause.py`
- `tests/unit/ranking_research/test_score_compression.py`

## `recommendation`

- `tests/unit/recommendation/test_conviction_scorer.py`
- `tests/unit/recommendation/test_cross_strategy_dedup.py`
- `tests/unit/recommendation/test_engine.py`
- `tests/unit/recommendation/test_engine_rcee.py`
- `tests/unit/recommendation/test_exit_signals.py`
- `tests/unit/recommendation/test_regime_edge_engine.py`

## `recommendation_analytics`

- `tests/unit/recommendation_analytics/test_calculator.py`
- `tests/unit/recommendation_analytics/test_trust_metrics.py`

## `regime_policy`

- `tests/unit/regime_policy/test_engine.py`
- `tests/unit/regime_policy/test_metrics.py`
- `tests/unit/regime_policy/test_pooled_metrics.py`
- `tests/unit/regime_policy/test_replay.py`

## `replay`

- `tests/unit/replay/test_experiment_config.py`
- `tests/unit/replay/test_metrics_collector.py`
- `tests/unit/replay/test_portfolio_manager.py`

## `services`

- `tests/unit/services/test_exit_research_phases.py`
- `tests/unit/services/test_exit_research_progress.py`
- `tests/unit/services/test_market_data_service.py`
- `tests/unit/services/test_paper_trade_lineage.py`
- `tests/unit/services/test_platform_traceability.py`
- `tests/unit/services/test_ranking_service.py`
- `tests/unit/services/test_signal_validation_service.py`
- `tests/unit/services/test_sprint71_traceability.py`
- `tests/unit/services/test_stock_service.py`
- `tests/unit/services/test_universe_bootstrap_service.py`
- `tests/unit/services/test_universe_coverage_service.py`

## `stock_setup_evidence`

- `tests/unit/stock_setup_evidence/test_similarity_and_outcomes.py`
- `tests/unit/stock_setup_evidence/test_strategy_profiles.py`

## `universe`

- `tests/unit/universe/test_filter_engine.py`
- `tests/unit/universe/test_nifty500_loader.py`
- `tests/unit/universe/test_nse_index_loader.py`

## `validation`

- `tests/unit/validation/test_campaign_aggregator.py`
- `tests/unit/validation/test_forward_returns.py`
- `tests/unit/validation/test_full_horizon_metrics.py`
- `tests/unit/validation/test_golden_validation.py`
- `tests/unit/validation/test_regimes.py`
- `tests/unit/validation/test_statistics.py`
- `tests/unit/validation/test_summary_aggregator.py`

## `workspace_exit_research`

- `tests/unit/workspace_exit_research/test_aggregation_index.py`
- `tests/unit/workspace_exit_research/test_constants.py`
- `tests/unit/workspace_exit_research/test_forward_returns_benchmark.py`
- `tests/unit/workspace_exit_research/test_forward_returns_index.py`
- `tests/unit/workspace_exit_research/test_policy_simulators.py`
- `tests/unit/workspace_exit_research/test_progress_phases.py`
