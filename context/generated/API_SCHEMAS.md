---
generated_at: 2026-06-07T03:43:13Z
generator: scripts/generate_context.py
---

# API Schemas Summary

> 142 paths from FastAPI OpenAPI. Full spec: `context/generated/API_SCHEMAS.json`

| Method | Path | Summary |
|--------|------|---------|
| POST | `/api/v1/analytics/exit/backfill` | Run Backfill |
| GET | `/api/v1/analytics/exit/reports/alpha-decay` | Alpha Decay Report |
| GET | `/api/v1/analytics/exit/reports/exit-policy-comparison` | Exit Policy Comparison |
| GET | `/api/v1/analytics/exit/reports/rank-deterioration` | Rank Deterioration Report |
| GET | `/api/v1/analytics/exit/reports/recommended-exit-policy` | Recommended Exit Policy |
| GET | `/api/v1/analytics/exit/reports/regime-transition` | Regime Transition Report |
| GET | `/api/v1/analytics/exit/reports/trend-failure` | Trend Failure Report |
| GET | `/api/v1/analytics/exit/runs` | List Runs |
| POST | `/api/v1/analytics/factors/backfill` | Run Backfill |
| GET | `/api/v1/analytics/factors/compare` | Compare Factor |
| GET | `/api/v1/analytics/factors/leaderboard` | Get Leaderboard |
| GET | `/api/v1/analytics/factors/performance` | Get Performance |
| GET | `/api/v1/analytics/factors/runs` | List Runs |
| GET | `/api/v1/analytics/factors/runs/{run_id}` | Get Run |
| GET | `/api/v1/analytics/factors/train-holdout-drift` | Get Train Holdout Drift |
| GET | `/api/v1/analytics/recommendations/committee` | Get Committee Performance |
| GET | `/api/v1/analytics/recommendations/conviction` | Get Conviction Performance |
| GET | `/api/v1/analytics/recommendations/regime` | Get Regime Performance |
| GET | `/api/v1/analytics/recommendations/summary` | Get Summary |
| GET | `/api/v1/analytics/recommendations/symbol/{symbol}` | Get Symbol Analytics |
| GET | `/api/v1/analytics/recommendations/trust` | Get Trust Metrics |
| POST | `/api/v1/analytics/research-intelligence/generate` | Generate Executive Pack |
| GET | `/api/v1/analytics/research-intelligence/reports/coverage` | Coverage Report |
| GET | `/api/v1/analytics/research-intelligence/reports/executive-summary` | Executive Summary |
| GET | `/api/v1/analytics/research-intelligence/reports/ic-by-strategy` | Ic By Strategy |
| GET | `/api/v1/analytics/research-intelligence/reports/top-20` | Top 20 |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/logout` | Logout |
| POST | `/api/v1/auth/logout-all` | Logout All |
| GET | `/api/v1/auth/me` | Me |
| POST | `/api/v1/auth/refresh` | Refresh |
| POST | `/api/v1/auth/register` | Register |
| POST | `/api/v1/backtest/generate-rankings` | Generate Rankings |
| GET | `/api/v1/backtest/summary` | Get Backtest Summary |
| POST | `/api/v1/copilot/ask` | Ask |
| GET | `/api/v1/copilot/audit` | Get Audit |
| GET | `/api/v1/execution/config` | Get Config |
| POST | `/api/v1/execution/config` | Update Config |
| GET | `/api/v1/execution/events` | List Events |
| GET | `/api/v1/execution/health` | Execution Health |
| POST | `/api/v1/execution/orders` | Submit Order |
| GET | `/api/v1/execution/orders` | List Orders |
| GET | `/api/v1/execution/orders/{order_id}` | Get Order |
| POST | `/api/v1/execution/orders/{order_id}/cancel` | Cancel Order |
| GET | `/api/v1/health` | Health Check |
| GET | `/api/v1/health/live` | Liveness |
| GET | `/api/v1/health/ready` | Readiness |
| GET | `/api/v1/investment-committee/committees/members` | List Committee Members |
| GET | `/api/v1/investment-committee/latest` | Latest Committee Review |
| POST | `/api/v1/investment-committee/review` | Start Committee Review |
| GET | `/api/v1/investment-committee/{review_id}` | Get Committee Review |
| GET | `/api/v1/investment-committee/{review_id}/explain` | Explain Committee Review |
| GET | `/api/v1/investment-committee/{review_id}/packets` | Get Committee Packets |
| GET | `/api/v1/investment-committee/{review_id}/report` | Get Committee Report |
| POST | `/api/v1/market-data/ingest` | Ingest Market Data |
| POST | `/api/v1/market-data/ingest-universe` | Ingest Universe |
| GET | `/api/v1/observability/experiments` | List Experiments |
| POST | `/api/v1/observability/experiments` | Create Experiment |
| POST | `/api/v1/observability/experiments/{experiment_id}/complete` | Complete Experiment |
| GET | `/api/v1/observability/health/platform` | Platform Health |
| GET | `/api/v1/observability/ingestion/batches` | List Ingestion Batches |
| GET | `/api/v1/observability/ingestion/batches/{batch_id}` | Get Ingestion Batch |
| GET | `/api/v1/observability/lineage/{entity_type}/{entity_id}` | Get Lineage |
| GET | `/api/v1/observability/rankings/runs` | List Ranking Runs |
| GET | `/api/v1/observability/rankings/{ranking_run_id}/stocks/{stock_id}/score-reconstruction` | Reconstruct Score |
| GET | `/api/v1/observability/regime/current` | Get Current Regime |
| GET | `/api/v1/observability/regime/performance` | List Regime Performance |
| POST | `/api/v1/observability/regime/performance/refresh` | Refresh Regime Performance |
| GET | `/api/v1/observability/validation/metrics` | List Validation Metrics |
| POST | `/api/v1/ops/daily-batch/runs` | Create Daily Batch Run |
| GET | `/api/v1/ops/daily-batch/runs` | List Daily Batch Runs |
| GET | `/api/v1/ops/daily-batch/runs/{run_id}` | Get Daily Batch Run |
| GET | `/api/v1/ops/daily-batch/runs/{run_id}/trace` | Get Daily Batch Trace |
| GET | `/api/v1/pilot/alerts` | Get Alerts |
| GET | `/api/v1/pilot/command-center` | Get Command Center |
| GET | `/api/v1/pilot/dashboard/committee` | Get Committee Dashboard |
| GET | `/api/v1/pilot/dashboard/health` | Get Health Dashboard |
| GET | `/api/v1/pilot/dashboard/operational` | Get Operational Dashboard |
| GET | `/api/v1/pilot/dashboard/pilot` | Get Pilot Dashboard |
| GET | `/api/v1/pilot/dashboard/recommendations` | Get Recommendation Dashboard |
| GET | `/api/v1/pilot/dashboard/trust` | Get Trust Dashboard |
| GET | `/api/v1/pilot/metrics/success` | Get Success Metrics |
| GET | `/api/v1/pilot/reports/{report_type}` | Get Report |
| GET | `/api/v1/portfolio/allocation` | Compute Allocation |
| GET | `/api/v1/portfolio/attribution` | Get Attribution |
| GET | `/api/v1/portfolio/benchmark` | Get Benchmark |
| GET | `/api/v1/portfolio/cash-ledger` | Get Cash Ledger |
| POST | `/api/v1/portfolio/config` | Upsert Config |
| GET | `/api/v1/portfolio/dashboard` | Get Dashboard |
| GET | `/api/v1/portfolio/exits` | Get Exits |
| POST | `/api/v1/portfolio/exits/run` | Run Exit Monitor |
| POST | `/api/v1/portfolio/exits/{exit_id}/confirm` | Confirm Exit |
| POST | `/api/v1/portfolio/exits/{exit_id}/reject` | Reject Exit |
| GET | `/api/v1/portfolio/limits` | Get Limits |
| GET | `/api/v1/portfolio/nav-history` | Get Nav History |
| POST | `/api/v1/portfolio/nav-snapshot` | Take Nav Snapshot |
| GET | `/api/v1/portfolio/performance` | Get Performance |
| GET | `/api/v1/portfolio/positions` | Get Positions |
| POST | `/api/v1/portfolio/recompute` | Recompute |
| POST | `/api/v1/portfolio/reconcile` | Run Reconciliation |
| GET | `/api/v1/portfolio/reconciliation` | Get Reconciliation |
| GET | `/api/v1/portfolio/risk` | Get Risk |
| GET | `/api/v1/portfolio/summary` | Get Summary |
| POST | `/api/v1/portfolio/trades/entry` | Execute Entry |
| POST | `/api/v1/portfolio/trades/exit` | Execute Exit |
| GET | `/api/v1/rankings/latest` | Get Latest Ranking |
| POST | `/api/v1/rankings/run` | Run Ranking |
| GET | `/api/v1/rankings/{run_id}` | Get Ranking Run |
| GET | `/api/v1/rankings/{run_id}/top` | Get Ranking Top |
| GET | `/api/v1/recommendations/daily` | Get Daily |
| GET | `/api/v1/recommendations/dates` | List Recommendation Dates |
| GET | `/api/v1/recommendations/latest` | Get Latest |
| GET | `/api/v1/recommendations/queue` | Get Approval Queue |
| POST | `/api/v1/recommendations/run` | Run Recommendation |
| GET | `/api/v1/recommendations/why-not/{symbol}` | Why Not Recommended |
| POST | `/api/v1/recommendations/{result_id}/approve` | Approve Recommendation |
| POST | `/api/v1/recommendations/{result_id}/reject` | Reject Recommendation |
| GET | `/api/v1/recommendations/{run_id}` | Get Run Results |
| GET | `/api/v1/recommendations/{run_id}/stocks/{symbol}` | Get Result By Symbol |
| POST | `/api/v1/regime-policy/backtest/run` | Run Backtest |
| GET | `/api/v1/regime-policy/backtest/runs` | List Backtest Runs |
| GET | `/api/v1/regime-policy/configs` | List Configs |
| POST | `/api/v1/regime-policy/configs` | Create Config |
| POST | `/api/v1/regime-policy/configs/presets/load` | Load Presets |
| POST | `/api/v1/regime-policy/configs/{config_id}/activate` | Activate Config |
| GET | `/api/v1/regime-policy/decisions` | List Decisions |
| POST | `/api/v1/regime-policy/evaluate` | Evaluate Policy |
| GET | `/api/v1/research/latest` | Latest Research Run |
| POST | `/api/v1/research/run` | Start Research Run |
| GET | `/api/v1/research/stock-setup/runs/{ranking_run_id}` | List Stock Setup Research |
| POST | `/api/v1/research/stock-setup/runs/{ranking_run_id}/generate` | Generate Stock Setup Research |
| GET | `/api/v1/research/{run_id}` | Get Research Run |
| GET | `/api/v1/research/{run_id}/explain` | Explain Research Run |
| GET | `/api/v1/research/{run_id}/lineage` | Research Run Lineage |
| GET | `/api/v1/research/{run_id}/packet` | Get Research Packets |
| GET | `/api/v1/stocks` | List Stocks |
| POST | `/api/v1/stocks/bootstrap` | Bootstrap Nifty500 |
| GET | `/api/v1/stocks/{symbol}` | Get Stock |
| GET | `/api/v1/stocks/{symbol}/market-data` | Get Stock Market Data |
| POST | `/api/v1/validation/backfill` | Backfill Validation |
| GET | `/api/v1/validation/full-universe/deciles` | Get Full Universe Validation Deciles |
| POST | `/api/v1/validation/full-universe/run` | Run Full Universe Validation |
| GET | `/api/v1/validation/full-universe/summary` | Get Full Universe Validation Summary |
| GET | `/api/v1/validation/runs/{run_id}` | Get Validation Report |
| POST | `/api/v1/validation/runs/{run_id}/compute` | Compute Validation |
| GET | `/api/v1/validation/runs/{run_id}/snapshots` | Get Validation Snapshots |
| GET | `/api/v1/validation/summary` | Get Validation Summary |