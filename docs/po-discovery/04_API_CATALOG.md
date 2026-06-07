# API Catalog

**Date:** 2026-06-05 (updated post Phase 2 + auth)  
**Base URL:** `/api/v1` (`app/main.py`)  
**Router:** `app/api/router.py`  
**OpenAPI:** Auto-generated at `/docs` (FastAPI default)  
**Full audit:** [`docs/audit/API_AUDIT_REPORT.md`](../audit/API_AUDIT_REPORT.md)

---

## Summary

| Tag / group | Prefix | Endpoints | Router file |
|-------------|--------|-----------|-------------|
| health | `/health` | 3 | `app/api/v1/health.py` |
| auth | `/auth` | 6 | `app/api/v1/auth.py` |
| stocks | `/stocks` | 4 | `app/api/v1/stocks.py` |
| market-data | `/market-data` | 2 | `app/api/v1/market_data.py` |
| rankings | `/rankings` | 4 | `app/api/v1/rankings.py` |
| backtest | `/backtest` | 2 | `app/api/v1/backtest.py` |
| validation | `/validation` | 8 | `app/api/v1/validation.py` |
| observability | `/observability` | 13 | `app/api/v1/observability.py` |
| regime-policy | `/regime-policy` | 8 | `app/api/v1/regime_policy.py` |
| factor-analytics | `/analytics/factors` | 7 | `app/api/v1/factor_analytics.py` |
| exit-analytics | `/analytics/exit` | 8 | `app/api/v1/exit_analytics.py` |
| research-intelligence | `/analytics/research-intelligence` | 5 | `app/api/v1/research_intelligence.py` |
| research (**deprecated**) | `/research` | 6 | `app/api/v1/research.py` |
| investment-committee | `/investment-committee` | 7 | `app/api/v1/investment_committee.py` |
| research-stock-setup | `/research/stock-setup` | 2 | `app/api/v1/stock_setup_research.py` |
| ops-daily-batch | `/ops/daily-batch` | 4 | `app/api/v1/daily_batch.py` |
| pilot-command-center | `/pilot` | 10 | `app/api/v1/pilot_ops.py` |
| recommendations | `/recommendations` | 9 | `app/api/v1/recommendations.py` |
| recommendation-analytics | `/analytics/recommendations` | 6 | `app/api/v1/recommendation_analytics.py` |
| portfolio | `/portfolio` | 22 | `app/api/v1/portfolio.py` |
| execution | `/execution` | 8 | `app/api/v1/execution.py` |
| copilot | `/copilot` | 2 | `app/api/v1/copilot.py` |

**Total HTTP routes:** ~130 (`grep '@router.(get|post|put|patch|delete)' app/api/v1/`)

### Authentication

All domain routers require JWT except **health** and **auth login/refresh/register/logout**.

| Layer | Enforcement | Routes |
|-------|-------------|--------|
| `get_current_user` | Bearer JWT | stocks, rankings, validation, portfolio read, pilot, copilot ask, … |
| `require_owner` | OWNER or ADMIN role | daily-batch mutations, recommendation approve/reject, portfolio mutations |
| `PortfolioScope` | `X-Portfolio-Id` + membership check | portfolio summary/positions, execution orders |
| `require_permission` | Fine-grained RBAC | execution read/write only |

**Dev bypass:** `auth_enabled=false` or `auth_bypass_for_tests=true` injects a fixed dev owner (`app/api/auth_deps.py`).

**Note:** `scripts/run_daily_nifty500_batch.py` POSTs without Authorization — use a service-account token or invoke `DailyBatchService` directly for unattended cron.

---

## health

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| GET | `/api/v1/health` | Liveness + DB ping | inline dict |

---

## stocks

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| GET | `/api/v1/stocks` | List stocks | `list[StockRead]` — `app/schemas/stock.py` |
| GET | `/api/v1/stocks/{symbol}` | Stock by symbol | `StockRead` |
| GET | `/api/v1/stocks/{symbol}/market-data` | OHLCV history | `list[MarketDataRead]` — `app/schemas/market_data.py` |

---

## market-data

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| POST | `/api/v1/market-data/ingest` | Trigger Yahoo ingest | `MarketDataIngestResponse` |

---

## rankings

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| POST | `/api/v1/rankings/run` | Execute ranking | `RankingRunRead` — `app/schemas/ranking.py` |
| GET | `/api/v1/rankings/latest` | Latest run for params | `RankingRunRead` |
| GET | `/api/v1/rankings/{run_id}` | Run metadata | `RankingRunRead` |
| GET | `/api/v1/rankings/{run_id}/top` | Top-N results | `RankingTopRead` |

**Default strategy:** `momentum_v1` (`app/core/config.py:21`)

---

## backtest

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| POST | `/api/v1/backtest/generate-rankings` | Historical ranking replay | `GenerateRankingsResponse` — `app/schemas/backtest.py` |
| GET | `/api/v1/backtest/summary` | Backtest aggregate | `BacktestSummaryRead` |

---

## validation

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| POST | `/api/v1/validation/backfill` | Backfill validation | `ValidationBackfillResponse` |
| POST | `/api/v1/validation/runs/{run_id}/compute` | Compute report | `ValidationReportRead` — `app/schemas/validation.py` |
| GET | `/api/v1/validation/runs/{run_id}` | Get report | `ValidationReportRead` |
| GET | `/api/v1/validation/runs/{run_id}/snapshots` | Performance snapshots | `list[ValidationSnapshotRead]` |
| GET | `/api/v1/validation/summary` | Aggregated summary | `ValidationSummaryRead` |
| POST | `/api/v1/validation/full-universe/campaigns` | Start campaign | (see router) |
| GET | `/api/v1/validation/full-universe/summary` | Campaign summary | `FullUniverseValidationSummaryRead` |
| GET | `/api/v1/validation/full-universe/deciles` | Decile breakdown | `FullUniverseDecilesResponse` |

---

## observability

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| GET | `/api/v1/observability/health/platform` | Platform health | inline |
| GET | `/api/v1/observability/ingestion/batches` | Ingest batches | inline list |
| GET | `/api/v1/observability/ingestion/batches/{batch_id}` | Batch detail | inline |
| GET | `/api/v1/observability/rankings/runs` | Ranking run list | inline |
| GET | `/api/v1/observability/validation/metrics` | Validation metrics | inline |
| GET | `/api/v1/observability/lineage/{entity_type}/{entity_id}` | Lineage chain | `list[dict]` |
| GET | `/api/v1/observability/rankings/{ranking_run_id}/stocks/{stock_id}/score-reconstruction` | Factor reconstruction | `ScoreReconstructionRead` — `app/schemas/observability.py` |
| GET | `/api/v1/observability/experiments` | List experiments | inline |
| POST | `/api/v1/observability/experiments` | Create experiment | `ExperimentRunCreate` |
| POST | `/api/v1/observability/experiments/{experiment_id}/complete` | Complete experiment | inline |
| GET | `/api/v1/observability/regime/current` | Current regime | inline |
| POST | `/api/v1/observability/regime/performance/refresh` | Refresh regime perf | inline |
| GET | `/api/v1/observability/regime/performance` | Regime performance | inline |

---

## regime-policy

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| GET | `/api/v1/regime-policy/configs` | List configs | `app/schemas/regime_policy.py` |
| POST | `/api/v1/regime-policy/configs` | Create config | same |
| POST | `/api/v1/regime-policy/configs/presets/load` | Load presets | same |
| POST | `/api/v1/regime-policy/configs/{config_id}/activate` | Activate | same |
| GET | `/api/v1/regime-policy/decisions` | Decision history | same |
| POST | `/api/v1/regime-policy/evaluate` | Evaluate day | same |
| POST | `/api/v1/regime-policy/backtest/run` | Run backtest | same |
| GET | `/api/v1/regime-policy/backtest/runs` | List backtests | same |

---

## analytics/factors

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| GET | `/api/v1/analytics/factors/performance` | Factor performance | `app/schemas/factor_analytics.py` |
| GET | `/api/v1/analytics/factors/leaderboard` | Leaderboard | same |
| GET | `/api/v1/analytics/factors/compare` | Compare factors | same |
| GET | `/api/v1/analytics/factors/train-holdout-drift` | Drift report | same |
| POST | `/api/v1/analytics/factors/backfill` | Backfill IC | same |
| GET | `/api/v1/analytics/factors/runs` | List runs | same |
| GET | `/api/v1/analytics/factors/runs/{run_id}` | Run detail | same |

---

## analytics/exit

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| POST | `/api/v1/analytics/exit/backfill` | Backfill exit research | `app/schemas/exit_research.py` |
| GET | `/api/v1/analytics/exit/reports/exit-policy-comparison` | Policy comparison | inline |
| GET | `/api/v1/analytics/exit/reports/alpha-decay` | Alpha decay | inline |
| GET | `/api/v1/analytics/exit/reports/rank-deterioration` | Rank deterioration | inline |
| GET | `/api/v1/analytics/exit/reports/regime-transition` | Regime transition | inline |
| GET | `/api/v1/analytics/exit/reports/trend-failure` | Trend failure | inline |
| GET | `/api/v1/analytics/exit/reports/recommended-exit-policy` | Recommended policy | inline |
| GET | `/api/v1/analytics/exit/runs` | List runs | inline |

---

## analytics/research-intelligence

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| POST | `/api/v1/analytics/research-intelligence/generate` | Generate reports | `app/schemas/research_intelligence.py` |
| GET | `/api/v1/analytics/research-intelligence/reports/executive-summary` | Executive summary | same |
| GET | `/api/v1/analytics/research-intelligence/reports/coverage` | Coverage | same |
| GET | `/api/v1/analytics/research-intelligence/reports/ic-by-strategy` | IC by strategy | same |
| GET | `/api/v1/analytics/research-intelligence/reports/top-20` | Top-20 report | same |

---

## research (ARGS)

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| POST | `/api/v1/research/run` | Start ARGS run | `app/schemas/args.py` |
| GET | `/api/v1/research/latest` | Latest run | same |
| GET | `/api/v1/research/{run_id}` | Run status | same |
| GET | `/api/v1/research/{run_id}/packet` | Packet for symbol | same |
| GET | `/api/v1/research/{run_id}/explain` | Explain output | same |
| GET | `/api/v1/research/{run_id}/lineage` | Full lineage | same |

---

## research/stock-setup (SEE v2)

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| POST | `/api/v1/research/stock-setup/runs/{ranking_run_id}/generate` | Generate SEE | inline |
| GET | `/api/v1/research/stock-setup/runs/{ranking_run_id}` | Get SEE results | inline |

---

## ops/daily-batch

| Method | Path | Description | Schema |
|--------|------|-------------|--------|
| POST | `/api/v1/ops/daily-batch/runs` | Start batch | `DailyBatchRunCreateResponse` — `app/schemas/daily_batch.py` |
| GET | `/api/v1/ops/daily-batch/runs` | List runs | `list[DailyBatchRunSummary]` |
| GET | `/api/v1/ops/daily-batch/runs/{run_id}` | Run status | `DailyBatchRunStatusResponse` |
| GET | `/api/v1/ops/daily-batch/runs/{run_id}/trace` | Phase trace | `DailyBatchTraceResponse` |

---

## Missing APIs (schema exists, no router)

| Domain | Models | Gap |
|--------|--------|-----|
| Paper trades | `app/models/paper_trade.py` | No `/paper-trades` router |
| Portfolio | `app/models/portfolio_position.py` | No `/portfolio` router |
| Outcome attribution | `app/outcome_attribution/` | Script-only reports |

---

## Error handling

| Exception | HTTP | Handler |
|-----------|------|---------|
| `NotFoundError` | 404 | `app/main.py` |
| `InvalidSymbolError`, `ValidationError`, `StrategyNotFoundError` | 422 | same |
| `ProviderError` | 502 | same |
| `RankingError` | 500 | same |
| `PiPMError` | 400 | same |

---

## Discrepancies

| Source | Issue |
|--------|-------|
| `docs/API_REFERENCE.md` | May not list all Sprint 8.6+ routes — **code router is authoritative** |
| `docs/AI/07_API/API_REFERENCE.md` | Cross-check recommended; this catalog from grep 2026-06-05 |

---

## References

- [`docs/AI/07_API/API_REFERENCE.md`](../AI/07_API/API_REFERENCE.md)
- [`docs/AI/07_API/API_WORKFLOWS.md`](../AI/07_API/API_WORKFLOWS.md)
- Integration tests: `tests/integration/api/`
