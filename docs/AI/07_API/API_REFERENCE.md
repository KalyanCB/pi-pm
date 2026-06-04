# API Reference (Auto-discovered)

**Base:** `http://localhost:8000/api/v1`  
**OpenAPI:** `/docs`, `/openapi.json`  
**Legacy detail:** [API_REFERENCE.md](../../API_REFERENCE.md)

Schemas: `app/schemas/`.

---

## Health

| Method | Path | Schema |
|--------|------|--------|
| GET | `/health` | inline dict |

---

## Stocks

| Method | Path | Schema |
|--------|------|--------|
| GET | `/stocks` | `list[StockRead]` — `app/schemas/stock.py` |
| GET | `/stocks/{symbol}` | `StockRead` |
| GET | `/stocks/{symbol}/market-data` | `list[MarketDataRead]` |

---

## Market data

| Method | Path | Schema |
|--------|------|--------|
| POST | `/market-data/ingest` | `MarketDataIngestResponse` — `market_data.py` |

---

## Rankings

| Method | Path | Schema |
|--------|------|--------|
| POST | `/rankings/run` | `RankingRunRead` — `ranking.py` |
| GET | `/rankings/latest` | `RankingRunRead` |
| GET | `/rankings/{run_id}` | `RankingRunRead` |
| GET | `/rankings/{run_id}/top` | `RankingTopRead` |

---

## Backtest

| Method | Path | Schema |
|--------|------|--------|
| POST | `/backtest/generate-rankings` | `GenerateRankingsResponse` — `backtest.py` |
| GET | `/backtest/summary` | `BacktestSummaryRead` |

---

## Validation

| Method | Path | Schema |
|--------|------|--------|
| POST | `/validation/backfill` | `ValidationBackfillResponse` |
| POST | `/validation/runs/{run_id}/compute` | `ValidationReportRead` |
| GET | `/validation/runs/{run_id}` | `ValidationReportRead` |
| GET | `/validation/runs/{run_id}/snapshots` | `list[ValidationSnapshotRead]` |
| GET | `/validation/summary` | `ValidationSummaryRead` |
| POST | `/validation/full-universe/campaigns` | campaign create (see router) |
| GET | `/validation/full-universe/summary` | `FullUniverseValidationSummaryRead` |
| GET | `/validation/full-universe/deciles` | `FullUniverseDecilesResponse` |

---

## Observability

| Method | Path | Schema |
|--------|------|--------|
| GET | `/observability/health/platform` | dict |
| GET | `/observability/ingestion/batches` | list |
| GET | `/observability/ingestion/batches/{batch_id}` | dict |
| GET | `/observability/rankings/runs` | list |
| GET | `/observability/validation/metrics` | dict |
| GET | `/observability/lineage/{entity_type}/{entity_id}` | list |
| GET | `/observability/rankings/{ranking_run_id}/stocks/{stock_id}/score-reconstruction` | `ScoreReconstructionRead` |
| GET | `/observability/experiments` | list |
| POST | `/observability/experiments` | `ExperimentRunCreate` |
| POST | `/observability/experiments/{experiment_id}/complete` | — |
| GET | `/observability/regime/current` | dict |
| POST | `/observability/regime/performance/refresh` | — |
| GET | `/observability/regime/performance` | dict |

---

## Regime policy

| Method | Path | Schema |
|--------|------|--------|
| GET | `/regime-policy/configs` | list |
| POST | `/regime-policy/configs` | create |
| POST | `/regime-policy/configs/presets/load` | — |
| POST | `/regime-policy/configs/{config_id}/activate` | — |
| GET | `/regime-policy/decisions` | list |
| POST | `/regime-policy/evaluate` | evaluate |
| POST | `/regime-policy/backtest/run` | backtest |
| GET | `/regime-policy/backtest/runs` | list |

Schemas: `app/schemas/regime_policy.py`

---

## Factor analytics

Prefix: `/analytics/factors`

| Method | Path |
|--------|------|
| GET | `/performance` |
| GET | `/leaderboard` |
| GET | `/compare` |
| GET | `/train-holdout-drift` |
| POST | `/backfill` |
| GET | `/runs` |
| GET | `/runs/{run_id}` |

Schemas: `app/schemas/factor_analytics.py`

---

## Exit analytics

Prefix: `/analytics/exit`

| Method | Path |
|--------|------|
| POST | `/backfill` |
| GET | `/reports/exit-policy-comparison` |
| GET | `/reports/alpha-decay` |
| GET | `/reports/rank-deterioration` |
| GET | `/reports/regime-transition` |
| GET | `/reports/trend-failure` |
| GET | `/reports/recommended-exit-policy` |
| GET | `/runs` |

Schemas: `app/schemas/exit_research.py`

---

## Research intelligence

Prefix: `/analytics/research-intelligence`

| Method | Path |
|--------|------|
| POST | `/generate` |
| GET | `/reports/executive-summary` |
| GET | `/reports/coverage` |
| GET | `/reports/ic-by-strategy` |
| GET | `/reports/top-20` |

Schemas: `app/schemas/research_intelligence.py`

---

## ARGS research

Prefix: `/research`

| Method | Path | Schema |
|--------|------|--------|
| POST | `/run` | 201 — `args.py` |
| GET | `/latest` | — |
| GET | `/{run_id}` | — |
| GET | `/{run_id}/packet` | packet JSON |
| GET | `/{run_id}/explain` | — |
| GET | `/{run_id}/lineage` | lineage |

---

## Stock setup (SEE)

Prefix: `/research/stock-setup`

| Method | Path |
|--------|------|
| POST | `/runs/{ranking_run_id}/generate` |
| GET | `/runs/{ranking_run_id}` |

---

## Daily batch

Prefix: `/ops/daily-batch`

| Method | Path | Schema |
|--------|------|--------|
| POST | `/runs` | `DailyBatchRunCreateResponse` |
| GET | `/runs` | `list[DailyBatchRunSummary]` |
| GET | `/runs/{run_id}` | `DailyBatchRunStatusResponse` |
| GET | `/runs/{run_id}/trace` | `DailyBatchTraceResponse` |

Schemas: `app/schemas/daily_batch.py`

---

## Error codes

| HTTP | Exception |
|------|-----------|
| 400 | `PiPMError` |
| 404 | `NotFoundError` |
| 422 | `ValidationError`, `InvalidSymbolError`, `StrategyNotFoundError` |
| 500 | `RankingError` |
| 502 | `ProviderError` |
| 207 | Partial ingest success |
