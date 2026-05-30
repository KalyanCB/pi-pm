# Architecture

Pi-PM is a personal AI-powered portfolio management platform.

Core principles:

1. LLMs never rank securities.
2. LLMs never determine position sizes.
3. LLMs never approve trades.
4. LLMs never override risk controls.
5. All money-related decisions must be deterministic.

## Current Layers

| Sprint | Layer | Status |
|--------|-------|--------|
| 1 | Foundation (FastAPI, PostgreSQL, Alembic, Docker, health) | Complete |
| 2 | Market Intelligence (Yahoo ingestion, stocks, market data) | Complete |
| 3 | Universe Filter + Deterministic Ranking Engine | Complete |
| 3.1 | Ranking hardening (idempotency, failed runs, cache prep, tests) | Complete |
| 4.1 | Historical ranking generator (backtest replayer) | Complete |
| 4.2 | Signal validation framework (IC, deciles, hit rates) | Complete |

## Sprint 3 — Ranking Pipeline

```
POST /api/v1/rankings/run
  → UniverseFilterEngine (eligibility)
  → RankingEngine + momentum_v1 (scoring)
  → Percentile normalization
  → Persist ranking_runs + ranking_results + performance_snapshots
```

Key properties: deterministic, reproducible, auditable, versioned.

## Sprint 3.1 — Hardening

### Benchmark handling

- When benchmark stock exists with sufficient history (≥201 bars for `momentum_v1`), all four factors are active at configured weights (40/25/20/15).
- When benchmark is missing or insufficient, `relative_strength` is excluded and remaining weights are redistributed proportionally. Ranking does **not** fail.
- Metadata fields: `benchmark_available`, `effective_weights`, optional `weight_adjustment_reason`.

### Idempotency behavior

- After computing `inputs_hash`, `RankingService` checks `find_completed_by_inputs_hash()`.
- **Only `COMPLETED` runs** are reused. Failed or pending runs never satisfy idempotent lookup.
- Identical inputs → same hash → same scores → same ranks.

### Failed run behavior

- Pending runs are created with `inputs_hash = NULL` (no `"pending"` placeholder).
- On failure: `status = FAILED`, `error_message` populated, `inputs_hash` remains `NULL`.
- A subsequent request with the same inputs recomputes and may succeed independently.

### Market data cache abstraction

- `MarketDataCache` (`app/market_data/cache.py`) is a session-scoped bar cache.
- Shared per ranking request between `UniverseFilterEngine` and `MarketDataLoader`.
- Sprint 3.1 wires the abstraction only; no performance optimization yet (Sprint 4).

## Sprint 4.1 — Historical Ranking Generator

Generates deterministic ranking runs for every trading day in a date range:

```
POST /api/v1/backtest/generate-rankings
  → TradingCalendar (benchmark-anchored dates from market data)
  → RankingReplayer (RankingService per day)
  → ranking_runs × N (idempotent via inputs_hash)
```

This produces the historical run corpus required before signal validation (Sprint 4.2).

## Sprint 4.2 — Signal Validation Framework

Measures whether ranking signals predict forward returns:

```
POST /api/v1/validation/runs/{run_id}/compute
  → Forward returns (5/10/20/60 trading days)
  → Regime classification (BULL/BEAR × HIGH_VOL/LOW_VOL)
  → IC, decile spreads, hit rates
  → ranking_validation_reports + filled performance_snapshots
```

Summary endpoint (`GET /api/v1/validation/summary`) aggregates across historical runs:
average IC, decile returns, hit rate, and IC by regime.

Backtest summary (`GET /api/v1/backtest/summary`) reports ranking vs validation coverage.

### Configuration defaults

API request fields `universe_code`, `strategy_name`, and `strategy_version` are optional. When omitted, values resolve from `Settings`:

- `RANKING_DEFAULT_UNIVERSE_CODE`
- `RANKING_DEFAULT_STRATEGY`
- `RANKING_DEFAULT_STRATEGY_VERSION`

See [domain-boundaries.md](./domain-boundaries.md) for domain separation rules.
