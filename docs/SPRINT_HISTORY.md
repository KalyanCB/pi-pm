# Pi-PM — Sprint History

**Last updated:** 2026-06-01

---

## Overview

| Sprint | Name | Status | Migration |
|--------|------|--------|-----------|
| 1 | Foundation | ✅ Complete | `20260530_0001` |
| 2 | Market Intelligence | ✅ Complete | `20260530_0002` |
| 3 | Universe Filter + Ranking | ✅ Complete | `20260530_0003` |
| 3.1 | Ranking Hardening | ✅ Complete | `20260530_0004` |
| 4.1 | Historical Ranking Generator | ✅ Complete | — |
| 4.2 | Signal Validation | ✅ Complete | `20260530_0005` |
| 5 / 5.1 | Breakout Strategy + NIFTY 500 | ✅ Complete | — |
| 6.1 | Full-Universe Validation | ✅ Code complete; ⏳ Results TBD | `20260530_0006` |

---

## Sprint 1 — Foundation

**Goal:** Project scaffold with health-checkable API and database.

### Features Delivered

- FastAPI application with `/api/v1/health`
- PostgreSQL via SQLAlchemy 2.0 + Alembic
- Docker Compose (API + Postgres)
- Core models: `stocks`, `ranking_runs`, `market_data`, `portfolio_positions`, `ranking_results`, `research_reports`, `paper_trades`
- Pydantic Settings from `.env`
- Structured logging

### Key Files

- `app/main.py`, `app/core/config.py`, `app/db/`
- `migrations/versions/20260530_0001_initial_schema.py`
- `docker/Dockerfile`, `docker/docker-compose.yml`

### Lessons Learned

- UUID primary keys from day one simplify cross-table references
- Separate Pydantic schemas from ORM models avoids coupling

---

## Sprint 2 — Market Intelligence

**Goal:** Ingest market data and manage investable universes.

### Features Delivered

- Yahoo Finance provider (`app/providers/yahoo/`)
- `POST /api/v1/market-data/ingest` with batch status (207 on partial failure)
- Stock master with `data_status` (ACTIVE/INACTIVE/ERROR)
- Universe tables: `stock_universes`, `universe_memberships`
- Seeded universes: NIFTY_50, NIFTY_100, NIFTY_500, PI_PM_CORE
- Ingestion run audit log
- Stock listing and market data query APIs

### Key Files

- `app/services/market_data_service.py`
- `app/models/stock_universe.py`, `universe_membership.py`
- `migrations/versions/20260530_0002_sprint2_market_intelligence.py`

### Lessons Learned

- Yahoo ingest fails in proxy-restricted environments (403) — must run locally
- `data_status` tracking essential for knowing which stocks can be ranked
- Batch ingest with per-symbol status enables partial recovery

---

## Sprint 3 — Universe Filter + Deterministic Ranking

**Goal:** Rank stocks using a versioned, reproducible factor model.

### Features Delivered

- `UniverseFilterEngine` — history, ADTV, price, active status filters
- `RankingEngine` + `PercentileNormalizer`
- `momentum_v1` strategy (4 factors, configurable weights)
- `POST /api/v1/rankings/run`, `GET /latest`, `GET /{id}`, `GET /{id}/top`
- `ranking_results` with `score_components` JSONB
- `ranking_performance_snapshots` (placeholder forward returns)
- `inputs_hash` for reproducibility
- Exclusion reason codes throughout pipeline

### Key Files

- `app/universe/filter_engine.py`
- `app/ranking/engine.py`, `strategies/momentum_v1.py`
- `app/services/ranking_service.py`
- `migrations/versions/20260530_0003_sprint3_ranking.py`

### Lessons Learned

- Domain boundaries (universe vs ranking) prevent logic leakage
- Metadata JSONB for exclusions invaluable for debugging low ranked counts
- Default universe `PI_PM_CORE` is fine for dev but misleading for production tests

---

## Sprint 3.1 — Ranking Hardening

**Goal:** Production-grade idempotency, benchmark resilience, cache abstraction.

### Features Delivered

- Nullable `inputs_hash` — NULL while pending/failed (no placeholder strings)
- Idempotent reuse: only `COMPLETED` runs match hash lookup
- Benchmark missing → exclude RS factor, redistribute weights proportionally
- `MarketDataCache` session-scoped abstraction
- Failed run independence — retry with same inputs creates fresh attempt
- Metadata: `benchmark_available`, `effective_weights`, `weight_adjustment_reason`

### Key Files

- `app/market_data/cache.py`
- `app/ranking/engine.py` (benchmark handling)
- `migrations/versions/20260530_0004_sprint31_ranking_hardening.py`

### Lessons Learned

- Never reuse failed runs via hash — only completed
- Weight redistribution must be proportional, not equal split
- Cache abstraction enables future performance work without API changes

---

## Sprint 4.1 — Historical Ranking Generator

**Goal:** Generate ranking runs for every trading day in a date range.

### Features Delivered

- `TradingCalendar` — benchmark-anchored trading days from market data
- `RankingReplayer` — calls `RankingService` per day with idempotency
- `POST /api/v1/backtest/generate-rankings`
- `GET /api/v1/backtest/summary` — ranking vs validation coverage
- `BacktestGenerationResult` with created/reused/failed counts

### Key Files

- `app/backtest/trading_calendar.py`, `ranking_replayer.py`
- `app/services/backtest_service.py`
- `app/api/v1/backtest.py`

### Lessons Learned

- Idempotent backfill essential — rerunning date ranges must not duplicate work
- Trading calendar must anchor on benchmark bars to handle market holidays
- Full 500-day backfill is slow — expect hours for full NIFTY 500

---

## Sprint 4.2 — Signal Validation Framework

**Goal:** Measure whether ranking signals predict forward returns.

### Features Delivered

- Forward returns at 5/10/20/60 trading days
- Regime classification: BULL/BEAR × HIGH_VOL/LOW_VOL
- Spearman IC, decile assignment, hit rates, spread
- `ranking_validation_reports` table
- `POST /validation/backfill`, `POST /validation/runs/{id}/compute`
- `GET /validation/summary` with cross-run aggregation and regime IC
- Per-stock snapshots filled with computed forward returns

### Key Files

- `app/validation/` (forward_returns, statistics, regimes, report_builder, summary_aggregator)
- `app/services/signal_validation_service.py`
- `migrations/versions/20260530_0005_sprint42_validation.py`

### Lessons Learned

- Per-run validation is necessary but insufficient for production decisions — need pooled full-universe view
- Regime breakdown reveals strategy performance varies by market condition
- Minimum sample size (5 stocks) for IC prevents noisy metrics on sparse runs

---

## Sprint 5 / 5.1 — Breakout Strategy + NIFTY 500 Expansion

**Goal:** Expand to full Indian equity universe and add breakout factor model.

### Features Delivered

- `breakout_v1` strategy with 8 factors (252-day history requirement)
- Breakout factors: high_proximity, volume_surge, atr_expansion, rs_acceleration, consolidation_breakout
- `data/nifty500_constituents.csv` (504 symbols)
- `UniverseBootstrapService` — load CSV → create stocks + memberships
- `UniverseCoverageService` — coverage reports (history, data status)
- Recovery scripts: `scripts/recover_universe.py`, `scripts/test_batch_ingest.py`
- Pipeline script: `scripts/sprint51_nifty500_pipeline.py`
- Diagnostic logging in ranking pipeline (filter stage counts)

### Scale Achieved

| Metric | Value |
|--------|------:|
| NIFTY 500 memberships | 504 |
| ACTIVE stocks (post-recovery) | ~445 |
| ERROR symbols remaining | 4 |
| Ranked per run | ~439 |
| Benchmark bars (^NSEI) | ~989 |

### Key Files

- `app/ranking/strategies/breakout_v1.py`
- `app/ranking/factors/` (5 breakout factor modules)
- `app/universe/nifty500_loader.py`
- `app/services/universe_bootstrap_service.py`, `universe_coverage_service.py`

### Lessons Learned

- **Always pass `universe_code: NIFTY_500`** — default is `PI_PM_CORE` (~15 stocks)
- Batch ingest with retries and sleep prevents Yahoo rate limiting
- 252-day history requirement eliminates many stocks until full 5y ingest completes
- Proxy-restricted environments cannot complete ingest — run recovery locally

### Branch / Merge

- Merged to `main` via PR #2 (`feature/sprint5-breakout-factors`)

---

## Sprint 6.1 — Full-Universe Historical Validation

**Goal:** Determine whether `breakout_v1` has predictive power on full NIFTY 500 universe.

### Features Delivered

- Campaign tables: campaigns, runs, metrics, deciles
- `FullUniverseValidationService` — orchestrates backfill + validate + aggregate
- `campaign_aggregator` — pools all stock-day observations across validated days
- Extended statistics: Pearson IC, Rank IC, top 20/50 returns, decile win rate, monotonicity
- API endpoints:
  - `POST /validation/full-universe/run`
  - `GET /validation/full-universe/summary`
  - `GET /validation/full-universe/deciles`
- Unit + integration tests (121 total passing)
- Validation report template: `docs/sprint61-full-universe-validation-report.md`

### Status

- Migration `20260530_0006` applied ✅
- API endpoints live ✅
- Campaign execution in progress or pending
- **Success criteria findings: TBD**

### Gate

No new signals until five validation questions answered:
1. Does breakout_v1 beat random?
2. Does top decile beat bottom decile?
3. Which horizon works best?
4. What is the historical spread?
5. Is ranking predictive enough for production?

### Key Files

- `app/services/full_universe_validation_service.py`
- `app/db/repositories/full_universe_validation_repository.py`
- `app/models/full_universe_validation.py`
- `app/validation/campaign_aggregator.py`
- `migrations/versions/20260530_0006_sprint61_full_universe_validation.py`

### Lessons Learned (Operational)

- Docker must be rebuilt/restarted after code changes — stale image caused 404 on new endpoints
- Full-universe campaign is long-running — plan for hours not minutes
- Campaign aggregation O(n²) hit rate — known performance issue

---

## Sprint 7 — Platform Traceability

**Branch:** merged via PR #3  
**Migration:** `20260530_0007`

### Deliverables

- Traceability tables: factor contributions, horizon/decile metrics, lineage, regime history, experiment registry
- Observability API: `/api/v1/observability/*`
- Structured logging events
- Incremental ingestion modes

### Key files

- `app/services/traceability_service.py`
- `app/services/observability_service.py`
- `migrations/versions/20260530_0007_sprint7_platform_traceability.py`
- `docs/sprint7-platform-traceability.md`

---

## Sprint 7.1 — Traceability Operationalization

**Migration:** None (uses Sprint 7 schema)

### Problem

Sprint 7 tables were empty despite active ranking/validation — reuse early-returns skipped traceability writes.

### Fix

- `ensure_ranking_traceability()` / `ensure_validation_traceability()` on reuse paths
- `scripts/backfill_sprint7_traceability.py --all`

### Post-backfill counts (approximate)

| Table | Rows |
|-------|-----:|
| ranking_factor_contributions | 1.18M |
| validation_horizon_metrics | 1,636 |
| regime_history | 348 |
| run_lineage_records | 409 |

**Runbook:** `docs/sprint71-traceability-operationalization.md`

---

## Sprint 8.1 — Regime-Aware Trading (Research)

**Branch:** `feature/sprint8`  
**Migration:** `20260531_0008`

### Objective

Test whether regime gating improves `breakout_v1` holdout performance vs baseline using historical replay (no reranking).

### Deliverables

- `RegimePolicyEngine` — E1–E4 policies (ALLOW/BLOCK/REDUCE)
- `RegimePolicyReplayService` — overlay on stored validation data
- Backtest comparison API with bootstrap CI + `research_findings`
- Preset loader: `scripts/init_regime_policy_presets.py`

### Critical fix (8.1.1)

Backtest hung before first `regime_backtest_runs` insert due to O(n²) `compute_hit_rates` on ~200k pooled rows. Fixed with `compute_pooled_period_metrics` + batch SQL load.

### Critical fix (8.1.2)

E2 backtest showed ALLOW in decisions but `sample_count=0` / `ranked_days=0`. Replay dropped ALLOW days when performance snapshot returns were NULL. Fixed with E1/E2 precomputed horizon-metrics fallback + train-metrics fallback in `research_findings`.

### Explicitly not done

- Live ranking integration
- Paper trading
- Factor weight changes

**Runbook:** `docs/sprint81-regime-aware-trading.md`

---

## Sprint 8.2 — Factor Predictive Power Analytics

**Branch:** `feature/sprint82-factor-ic-analytics`  
**Migration:** `20260601_0009`

### Objective

Read-only factor IC analytics: which factors have edge in BULL_LOW_VOL and whether it holds on holdout.

### Deliverables

- `app/factor_analytics/` domain package
- Tables: `factor_performance_metrics`, `factor_daily_metrics`, `factor_performance_runs`
- `FactorPredictivePowerService` + `/api/v1/analytics/factors/*`
- Train/holdout splits, stability score, regime coverage, weight resolution, ALL regime rollup
- Backfill script: `scripts/backfill_sprint82_factor_analytics.py`
- 27 new tests (177 total)

### Explicitly not done

- Ranking / validation / regime policy changes
- Factor weight changes
- Daily metrics API (deferred to 8.3)
- Sprint 8.2.1 interaction analysis (ADR-021 draft only)

**Runbook:** `docs/sprint82-factor-ic-analytics.md`  
**Review package:** `docs/sprint82-implementation-summary.md`

---

## Test Growth by Sprint

| Sprint | Approx. Tests |
|--------|--------------:|
| 3 | ~29 |
| 4.2 | ~80 |
| 5.1 | ~113 |
| 6.1 | 121 |
| 7 / 7.1 | 132 |
| 8.1 | **150** |
| 8.2 | **177** |

---

## Related Documentation

- `docs/HANDOFF.md` — **Takeover entry point**
- `docs/PROJECT_MASTER.md` — Current status
- `docs/ROADMAP.md` — Future sprints
- `docs/sprint61-full-universe-validation-report.md`
- `docs/sprint7-platform-traceability.md`
- `docs/sprint71-traceability-operationalization.md`
- `docs/sprint81-regime-aware-trading.md`
