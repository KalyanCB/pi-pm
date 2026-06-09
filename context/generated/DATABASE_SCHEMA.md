---
generated_at: 2026-06-09T00:56:52Z
generator: scripts/generate_context.py
---

# Database Schema

> Parsed from `app/models/*.py`. See `migrations/versions/` for migrations.

## Table index

- `committee_reviews` — `CommitteeReview` (`app/models/args.py`)
- `copilot_query_logs` — `CopilotQueryLog` (`app/models/copilot.py`)
- `cro_reviews` — `CroReview` (`app/models/args.py`)
- `daily_batch_run_artifacts` — `DailyBatchRunArtifact` (`app/models/daily_batch.py`)
- `daily_batch_runs` — `DailyBatchRun` (`app/models/daily_batch.py`)
- `execution_audit` — `ExecutionAudit` (`app/models/execution.py`)
- `execution_configs` — `ExecutionConfig` (`app/models/execution.py`)
- `execution_events` — `ExecutionEvent` (`app/models/execution.py`)
- `execution_orders` — `ExecutionOrder` (`app/models/execution.py`)
- `exit_research_alpha_decay_points` — `ExitResearchAlphaDecayPoint` (`app/models/exit_research.py`)
- `exit_research_policy_metrics` — `ExitResearchPolicyMetric` (`app/models/exit_research.py`)
- `exit_research_runs` — `ExitResearchRun` (`app/models/exit_research.py`)
- `experiment_runs` — `ExperimentRun` (`app/models/platform_traceability.py`)
- `factor_daily_metrics` — `FactorDailyMetric` (`app/models/factor_analytics.py`)
- `factor_performance_metrics` — `FactorPerformanceMetric` (`app/models/factor_analytics.py`)
- `factor_performance_runs` — `FactorPerformanceRun` (`app/models/factor_analytics.py`)
- `full_universe_validation_campaigns` — `FullUniverseValidationCampaign` (`app/models/full_universe_validation.py`)
- `full_universe_validation_deciles` — `FullUniverseValidationDecile` (`app/models/full_universe_validation.py`)
- `full_universe_validation_metrics` — `FullUniverseValidationMetric` (`app/models/full_universe_validation.py`)
- `full_universe_validation_runs` — `FullUniverseValidationRun` (`app/models/full_universe_validation.py`)
- `governance_research_report_evidence` — `GovernanceResearchReportEvidence` (`app/models/args.py`)
- `governance_research_reports` — `GovernanceResearchReport` (`app/models/args.py`)
- `ingestion_batch_runs` — `IngestionBatchRun` (`app/models/platform_traceability.py`)
- `investment_review_packets` — `InvestmentReviewPacket` (`app/models/args.py`)
- `llm_execution_records` — `LlmExecutionRecord` (`app/models/args.py`)
- `market_data` — `MarketData` (`app/models/market_data.py`)
- `market_data_ingestion_runs` — `MarketDataIngestionRun` (`app/models/market_data_ingestion_run.py`)
- `paper_trades` — `PaperTrade` (`app/models/paper_trade.py`)
- `permissions` — `PermissionRecord` (`app/models/auth.py`)
- `portfolio_cash_ledger` — `CashLedger` (`app/models/portfolio_analytics.py`)
- `portfolio_configs` — `PortfolioConfig` (`app/models/portfolio_position.py`)
- `portfolio_exit_recommendations` — `ExitRecommendation` (`app/models/portfolio_analytics.py`)
- `portfolio_nav_history` — `PortfolioNavHistory` (`app/models/portfolio_analytics.py`)
- `portfolio_positions` — `PortfolioPosition` (`app/models/portfolio_position.py`)
- `portfolio_reconciliation_reports` — `PortfolioReconciliationReport` (`app/models/portfolio_analytics.py`)
- `portfolios` — `Portfolio` (`app/models/auth.py`)
- `prompt_versions` — `PromptVersion` (`app/models/args.py`)
- `ranking_factor_contributions` — `RankingFactorContribution` (`app/models/platform_traceability.py`)
- `ranking_performance_snapshots` — `RankingPerformanceSnapshot` (`app/models/ranking_performance_snapshot.py`)
- `ranking_results` — `RankingResult` (`app/models/ranking_result.py`)
- `ranking_runs` — `RankingRun` (`app/models/ranking_run.py`)
- `ranking_validation_reports` — `RankingValidationReport` (`app/models/ranking_validation_report.py`)
- `recommendation_approvals` — `RecommendationApproval` (`app/models/recommendation.py`)
- `recommendation_configs` — `RecommendationConfig` (`app/models/recommendation.py`)
- `recommendation_outcomes` — `RecommendationOutcome` (`app/models/recommendation.py`)
- `recommendation_results` — `RecommendationResult` (`app/models/recommendation.py`)
- `recommendation_runs` — `RecommendationRun` (`app/models/recommendation.py`)
- `refresh_tokens` — `RefreshToken` (`app/models/auth.py`)
- `regime_backtest_runs` — `RegimeBacktestRun` (`app/models/regime_policy.py`)
- `regime_history` — `RegimeHistory` (`app/models/platform_traceability.py`)
- `regime_policy_configs` — `RegimePolicyConfig` (`app/models/regime_policy.py`)
- `regime_policy_decisions` — `RegimePolicyDecision` (`app/models/regime_policy.py`)
- `research_intelligence_reports` — `ResearchIntelligenceReport` (`app/models/research_intelligence.py`)
- `research_intelligence_runs` — `ResearchIntelligenceRun` (`app/models/research_intelligence.py`)
- `research_reports` — `ResearchReport` (`app/models/research_report.py`)
- `research_runs` — `ResearchRun` (`app/models/args.py`)
- `role_permissions` — `RolePermission` (`app/models/auth.py`)
- `roles` — `Role` (`app/models/auth.py`)
- `run_lineage_records` — `RunLineageRecord` (`app/models/platform_traceability.py`)
- `stock_setup_research` — `StockSetupResearch` (`app/models/stock_setup_research.py`)
- `stock_setup_research_metrics` — `StockSetupResearchMetric` (`app/models/stock_setup_research.py`)
- `stock_universes` — `StockUniverse` (`app/models/stock_universe.py`)
- `stocks` — `Stock` (`app/models/stock.py`)
- `strategy_regime_performance` — `StrategyRegimePerformance` (`app/models/platform_traceability.py`)
- `universe_memberships` — `UniverseMembership` (`app/models/universe_membership.py`)
- `user_portfolio_memberships` — `UserPortfolioMembership` (`app/models/auth.py`)
- `user_preferences` — `UserPreference` (`app/models/auth.py`)
- `users` — `User` (`app/models/auth.py`)
- `validation_decile_metrics` — `ValidationDecileMetric` (`app/models/platform_traceability.py`)
- `validation_horizon_metrics` — `ValidationHorizonMetric` (`app/models/platform_traceability.py`)

## Key tables (detail)

### `execution_orders`

| Column | Type | FK |
|--------|------|-----|
| `portfolio_id` | UUID | `portfolios.id` |
| `symbol` | String | `recommendation_results.id` |
| `side` | String | `recommendation_results.id` |
| `quantity` | Numeric | `recommendation_results.id` |
| `strategy_name` | String | `recommendation_results.id` |
| `recommendation_id` | UUID | `recommendation_results.id` |
| `approval_id` | UUID | `recommendation_approvals.id` |
| `requested_by` | UUID | `users.id` |
| `approved_by` | UUID | `users.id` |
| `executed_by` | UUID | `users.id` |
| `execution_mode` | String | — |
| `status` | String | — |
| `client_order_id` | String | — |
| `idempotency_key` | String | — |
| `broker_name` | String | — |
| `broker_order_id` | String | — |
| `filled_quantity` | Numeric | `paper_trades.id` |
| `avg_fill_price` | Numeric | `paper_trades.id` |
| `fees` | Numeric | `paper_trades.id` |
| `slippage` | Numeric | `paper_trades.id` |
| `paper_trade_id` | UUID | `paper_trades.id` |
| `raw_response` | JSONB | — |
| `rejection_reason` | Date | — |
| `submitted_at` | Date | — |
| `completed_at` | Date | — |

### `paper_trades`

| Column | Type | FK |
|--------|------|-----|
| `stock_id` | UUID | `stocks.id` |
| `side` | String | — |
| `quantity` | Numeric | — |
| `limit_price` | Numeric | — |
| `fill_price` | Numeric | — |
| `fill_quantity` | Numeric | `ranking_runs.id` |
| `status` | String | `ranking_runs.id` |
| `rejection_reason` | UUID | `ranking_runs.id` |
| `ranking_run_id` | UUID | `ranking_runs.id` |
| `idempotency_key` | String | — |
| `requested_at` | Date | — |
| `filled_at` | Date | — |
| `metadata_` | JSONB | — |
| `stock` | other | — |

### `portfolio_exit_recommendations`

| Column | Type | FK |
|--------|------|-----|
| `portfolio_position_id` | UUID | `portfolio_positions.id` |
| `stock_id` | UUID | `stocks.id` |
| `as_of_date` | Date | — |
| `status` | String | — |
| `triggers` | JSONB | — |
| `trigger_details` | JSONB | — |
| `current_rank` | Numeric | — |
| `days_held` | Numeric | — |
| `unrealized_pnl_pct` | Numeric | — |
| `urgency` | String | — |
| `monitor_tier` | String | — |
| `auto_executed` | String | — |
| `actor_id` | String | — |
| `confirmed_at` | Date | — |
| `rejected_at` | Date | — |
| `rejection_reason` | String | — |
| `position` | other | — |

### `portfolio_nav_history`

| Column | Type | FK |
|--------|------|-----|
| `as_of_date` | Date | — |
| `total_equity` | Numeric | — |
| `cash_balance` | Numeric | — |
| `market_value` | Numeric | — |
| `unrealized_pnl` | Numeric | — |
| `realized_pnl_cumulative` | Numeric | — |
| `open_positions` | Integer | — |
| `cash_pct` | Numeric | — |
| `day_return_pct` | Numeric | — |
| `benchmark_return_pct` | Numeric | — |
| `alpha_pct` | Numeric | — |
| `regime_label` | String | — |

### `portfolio_positions`

| Column | Type | FK |
|--------|------|-----|
| `portfolio_id` | UUID | `portfolios.id` |
| `stock_id` | UUID | `stocks.id` |
| `recommendation_result_id` | UUID | `recommendation_results.id` |
| `quantity` | Numeric | — |
| `avg_cost` | Numeric | — |
| `entry_price` | Numeric | — |
| `exit_price` | Numeric | — |
| `entry_date` | Date | — |
| `exit_date` | Date | — |
| `stop_loss_price` | Numeric | — |
| `market_value` | Numeric | — |
| `unrealized_pnl` | Numeric | — |
| `realized_pnl` | Numeric | — |
| `weight_pct` | Numeric | — |
| `conviction_band` | String | — |
| `strategy_name` | String | — |
| `sector` | String | — |
| `as_of` | Date | — |
| `is_current` | Boolean | — |
| `position_status` | String | — |
| `exit_reason` | String | — |
| `stock` | other | — |

### `ranking_results`

| Column | Type | FK |
|--------|------|-----|
| `ranking_run_id` | UUID | `ranking_runs.id` |
| `stock_id` | UUID | `stocks.id` |
| `rank` | Integer | — |
| `score` | Numeric | — |
| `score_components` | JSONB | — |
| `created_at` | Date | — |
| `ranking_run` | other | — |
| `stock` | other | — |

### `ranking_runs`

| Column | Type | FK |
|--------|------|-----|
| `strategy_name` | String | — |
| `strategy_version` | String | — |
| `as_of_date` | Date | — |
| `inputs_hash` | String | — |
| `universe_code` | String | — |
| `benchmark_symbol` | String | — |
| `filter_config_hash` | String | — |
| `normalization_method` | String | — |
| `status` | String | — |
| `started_at` | Date | — |
| `completed_at` | Date | — |
| `error_message` | JSONB | — |
| `metadata_` | JSONB | — |
| `regime_label` | String | — |
| `weight_config_hash` | String | — |
| `ranked_stock_count` | Integer | — |
| `excluded_stock_count` | Integer | — |
| `execution_duration_ms` | Integer | — |
| `results` | other | — |
| `performance_snapshots` | other | — |
| `validation_report` | other | — |

### `recommendation_results`

| Column | Type | FK |
|--------|------|-----|
| `recommendation_run_id` | UUID | `recommendation_runs.id` |
| `stock_id` | UUID | `stocks.id` |
| `rank` | Integer | — |
| `composite_score` | Numeric | — |
| `action` | String | — |
| `lifecycle_state` | String | — |
| `conviction_score` | Integer | — |
| `conviction_band` | String | `portfolio_positions.id` |
| `conviction_components` | JSONB | `portfolio_positions.id` |
| `reason_codes` | JSONB | `portfolio_positions.id` |
| `portfolio_position_id` | UUID | `portfolio_positions.id` |
| `prior_recommendation_id` | UUID | `recommendation_results.id` |
| `args_research_run_id` | UUID | `research_runs.id` |
| `recommendation_confidence` | String | — |
| `recommendation_run` | other | — |
| `stock` | other | — |
| `approvals` | other | — |
| `outcome` | other | — |
