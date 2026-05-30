# Sprint 4 Implementation Plan (Revised)

**Product Owner revision:** Historical ranking generation must precede signal validation.  
**Branch:** `feature/sprint4-signal-validation`

---

## Problem Statement

Signal validation (IC, deciles, hit rates) requires **many historical ranking runs**. Without backfill, validation means "rank today, wait 60 days" — months before learning anything.

Pi-PM must answer, over the last 3 years:

- Average IC?
- Best / worst regime?
- Top vs bottom decile return?
- Hit rate?

---

## Sprint Structure

| Phase | Name | Delivers |
|-------|------|----------|
| **4.1** | Historical Ranking Generator | 500+ deterministic ranking runs in hours |
| **4.2** | Signal Validation Framework | Forward returns, IC, deciles, hit rates, reports |

4.2 depends on 4.1 output. Do not ship 4.2 before 4.1 is tested.

---

## Sprint 4.1 — Historical Ranking Generator

### Objective

Generate one ranking run per trading day between `start_date` and `end_date` using existing Universe Filter + Ranking Engine logic.

**Not in scope:** trading simulator, portfolio, execution, paper trading.

### Package: `app/backtest/`

| Module | Responsibility |
|--------|----------------|
| `trading_calendar.py` | Resolve trading days from market data (benchmark-anchored, universe fallback) |
| `ranking_replayer.py` | Iterate calendar days, invoke ranking per day, aggregate stats |
| `models.py` | `BacktestGenerationResult`, `TradingDayStats` dataclasses |

### Service: `app/services/backtest_service.py`

Orchestrates calendar resolution + replayer + transaction boundaries.

### API

```
POST /api/v1/backtest/generate-rankings
```

**Request:**
```json
{
  "universe_code": "PI_PM_CORE",
  "start_date": "2023-01-01",
  "end_date": "2025-12-31",
  "strategy_name": "momentum_v1",
  "strategy_version": "1.0.0",
  "benchmark_symbol": "^NSEI"
}
```

**Response:**
```json
{
  "universe_code": "PI_PM_CORE",
  "start_date": "2023-01-01",
  "end_date": "2025-12-31",
  "trading_days_total": 512,
  "runs_created": 480,
  "runs_reused": 32,
  "runs_failed": 0,
  "failed_dates": []
}
```

### Idempotency

Per day, delegates to `RankingService.run_ranking_with_outcome()`:

- Computes ranking via existing engine
- Reuses completed run when `inputs_hash` matches (`find_completed_by_inputs_hash`)
- Skips duplicate persist
- Failed days recorded; loop continues

### Trading calendar rules

1. If benchmark stock exists in DB → use its market-data dates in range
2. Else → union of distinct dates across universe member stocks
3. Filter to `[start_date, end_date]`, sorted ascending
4. Skip weekends only if no bar exists (data-driven, not exchange calendar file)

### Tests (4.1)

| Test | Validates |
|------|-----------|
| `test_trading_calendar_benchmark_anchored` | Benchmark dates used when available |
| `test_trading_calendar_universe_fallback` | Fallback when no benchmark |
| `test_ranking_replayer_idempotent` | Second pass → `runs_reused` |
| `test_generate_rankings_api` | Integration: 5-day range → 5 runs |
| `test_generate_rankings_deterministic` | Same inputs → same run IDs on replay |

### 4.1 Success criteria

- [ ] Generate rankings for arbitrary date range via API
- [ ] Each day uses Sprint 3 universe filter + ranking engine unchanged
- [ ] Idempotent reuse via `inputs_hash`
- [ ] Deterministic and auditable per run

---

## Sprint 4.2 — Signal Validation Framework

*(Deferred until 4.1 complete — design unchanged from prior plan.)*

### Objective

Measure predictive power of ranking signals across historical runs.

### Package: `app/validation/`

| Module | Responsibility |
|--------|----------------|
| `forward_returns.py` | N trading-day forward return from `as_of_date` |
| `statistics.py` | Spearman IC, decile buckets, hit rates |
| `report_builder.py` | Per-run + cross-run aggregate metrics |
| `models.py` | `HorizonMetrics`, `ValidationReport`, `CrossRunSummary` |

### Persistence

- **Fill** `ranking_performance_snapshots` (`return_5d/10d/20d/60d`)
- **New table** `ranking_validation_reports` (per-run metrics)
- **New table** `ranking_validation_summaries` (cross-run: avg IC, rolling IC, regime splits)

### APIs (4.2)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/validation/runs/{run_id}/compute` | Validate single run |
| POST | `/api/v1/validation/backfill` | Validate all runs in date range |
| GET | `/api/v1/validation/summary` | Cross-run: avg IC, decile spreads, hit rates |

### Cross-run metrics (answers PO questions)

| Question | Metric |
|----------|--------|
| Average IC? | Mean Spearman IC across runs per horizon |
| Best / worst regime? | IC grouped by volatility or trend regime bucket |
| Top decile return? | Mean forward return of decile 1, averaged across runs |
| Bottom decile return? | Mean forward return of decile 10 |
| Hit rate? | Mean `top_vs_bottom_hit_rate` across runs |

### Horizon semantics

`return_Nd` = N **trading days** forward from `as_of_date`, using `adj_close` when available.

### Tests (4.2)

- Unit: forward returns, IC, deciles, hit rates, golden fixtures
- Integration: rank → backfill validate → summary API
- Reproducibility: identical `validation_hash` on replay

### 4.2 Success criteria

- [ ] Fill forward returns for historical runs where data exists
- [ ] IC, decile spread, hit rate per run per horizon
- [ ] Cross-run summary over 3-year backfill
- [ ] Reproducible validation hash

---

## Implementation Phases (Execution Order)

```
Phase 1: Sprint 4.1 backtest package + calendar + replayer
Phase 2: Sprint 4.1 service + API + tests
Phase 3: Sprint 4.2 validation domain + forward returns
Phase 4: Sprint 4.2 persistence + validation APIs
Phase 5: Sprint 4.2 cross-run summary + golden tests + docs
```

---

## Architecture (End State)

```
Market Data
    ↓
[4.1] Backtest Generator ──→ ranking_runs × N dates
    ↓
[4.2] Validation Engine ──→ performance_snapshots (filled)
                          ──→ validation_reports (IC, deciles, hit rate)
                          ──→ validation_summaries (3-year evidence)
```

---

## Explicit Out of Scope (All Sprint 4)

- Portfolio Manager
- Risk Officer
- Execution / paper trading
- LangGraph / LLM
- Live trading simulation

---

## Sprint 4 Definition of Done

We are building an **investment platform** (not just software) when we can answer:

> Over the last 3 years, for `momentum_v1` on `PI_PM_CORE`:  
> Average IC₂₀ = ? · Top decile return = ? · Hit rate = ? · Best regime = ?

That requires **4.1 + 4.2** complete.
