# Pi-PM Sprint 3 — Code Review Package

**Sprint:** 3 — Universe Filter + Deterministic Ranking Engine  
**App version:** `0.3.0`  
**Migration:** `20260530_0003`  
**Branch baseline:** `main` @ Sprint 2 (`de29214`)  
**Review scope:** ~1,500 LOC across universe, ranking, services, API, migration, tests  
**Test status:** 29 passed · ruff clean

---

## 1. Executive Summary

Sprint 3 implements a **deterministic, auditable ranking pipeline** for Pi-PM:

```
Universe Filter → Strategy Factors → Percentile Normalize → Rank → Persist
```

**In scope (implemented):**
- Universe filter with ADTV, min price, history, data status
- `momentum_v1` strategy (4 factors, continuous trend quality)
- Benchmark-resilient weight redistribution
- Ranking run persistence with `inputs_hash` idempotency
- Exclusion summary audit trail in `ranking_runs.metadata`
- `ranking_performance_snapshots` foundation table (null placeholders)

**Explicitly out of scope (not present):**
- LLM / LangGraph / Portfolio / Risk / Execution logic
- Performance analytics or learning engine
- Per-stock exclusion detail persistence

---

## 2. Architecture & Domain Boundaries

### 2.1 Layer diagram

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer          app/api/v1/rankings.py                  │
├─────────────────────────────────────────────────────────────┤
│  Service Layer      RankingService                          │
│                     UniverseFilterService                   │
├──────────────────────┬──────────────────────────────────────┤
│  Universe Domain     │  Ranking Domain                      │
│  app/universe/       │  app/ranking/                        │
│  - filter_engine     │  - engine                            │
│  - models            │  - strategies/momentum_v1            │
│                      │  - normalizer, hashing, math_utils   │
├──────────────────────┴──────────────────────────────────────┤
│  Repositories       universe, ranking_run/result/performance│
│  Models             ranking_run, ranking_performance_snapshot│
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Domain separation rules

| Domain | Owns | Must NOT own |
|--------|------|--------------|
| **Universe** (`app/universe/`) | Eligibility filtering, ADTV/price/history gates | Factor scoring, normalization, rank assignment |
| **Ranking** (`app/ranking/`) | Factor computation, normalization, ordering, hashing | Universe membership rules, stock master data |
| **Services** | Orchestration, persistence, idempotency | Business math (delegates to domains) |
| **API** | HTTP contract, symbol enrichment | Direct DB or factor access |

### 2.3 Orchestration flow

```
POST /rankings/run
  └─ RankingService.run_ranking()
       ├─ UniverseFilterService.build_tradable_universe()
       │    └─ UniverseFilterEngine → TradableUniverse
       ├─ RankingEngine.run(tradable_universe, strategy, benchmark)
       │    └─ RankingOutput (ranked_stocks, inputs_hash, metadata)
       ├─ find_by_inputs_hash() → return existing if match
       └─ persist: ranking_runs + ranking_results + performance_snapshots
```

**Coupling note for reviewers:** `FilterDecision` (universe package) is reused for ranking-phase exclusions. Acceptable for MVP; consider a shared `app/common/exclusions.py` if more strategies arrive.

---

## 3. Required Design Changes — Verification Matrix

| # | Requirement | Implementation | Verified by |
|---|-------------|----------------|-------------|
| 1 | ADTV filter (avg vol × avg close, default ₹1 Cr) | `UniverseFilterEngine._average_volume/_average_close` (20d window) | `test_universe_filter_traded_value_and_price` |
| 1 | Min stock price > ₹50 | `latest.close < config.min_stock_price` | same |
| 2 | Continuous trend quality | `0.5×(Close/MA50) + 0.5×(Close/MA200)` | `test_trend_quality_continuous` |
| 3 | Benchmark missing → no failure, weight redistribution | `redistribute_weights()` in engine | `test_benchmark_missing_redistributes_weights`, `test_redistribute_weights_without_benchmark` |
| 4 | `ranking_performance_snapshots` table | Migration + `RankingPerformanceRepository` | Integration run creates rows |
| 5 | Exclusion summary in metadata | `RankingService` merges into `metadata.exclusion_summary` | `test_ranking_api_flow` |
| 6 | Universe 63d history; strategy 201d | Config default 63; `MomentumV1Strategy.requirements()` = 201 | Filter + engine tests |

---

## 4. File Inventory

### 4.1 New files (review priority: HIGH)

| File | LOC (approx) | Review focus |
|------|--------------|--------------|
| `app/universe/filter_engine.py` | 220 | Filter logic correctness, exclusion codes |
| `app/ranking/engine.py` | 195 | Orchestration, benchmark resilience, tie-break |
| `app/ranking/strategies/momentum_v1.py` | 140 | Factor formulas, MIN_VOL guard |
| `app/ranking/normalizer.py` | 44 | Percentile tie handling, weight redistribution |
| `app/ranking/hashing.py` | 45 | Determinism, hash inputs completeness |
| `app/ranking/math_utils.py` | ~120 | Return/vol/SMA correctness |
| `app/services/ranking_service.py` | 150 | Idempotency, transaction boundaries |
| `app/api/v1/rankings.py` | 70 | API contract, error paths |
| `migrations/versions/20260530_0003_sprint3_ranking.py` | 93 | Backfill, indexes, FK cascades |

### 4.2 Modified files (review priority: MEDIUM)

| File | Change |
|------|--------|
| `app/core/config.py` | 8 ranking settings |
| `app/core/constants.py` | Exclusion codes, strategy constants |
| `app/models/ranking_run.py` | Extended columns + indexes |
| `app/api/deps.py` | DI wiring for ranking stack |
| `app/db/repositories/universe_repository.py` | `list_candidate_stocks()` |

### 4.3 Test files (review priority: HIGH)

| File | Tests | Purpose |
|------|-------|---------|
| `tests/unit/universe/test_filter_engine.py` | 1 | ADTV + min price exclusions |
| `tests/unit/ranking/test_engine.py` | 2 | Reproducibility, benchmark fallback |
| `tests/unit/ranking/test_normalizer.py` | 2 | Percentile ties, weight math |
| `tests/unit/ranking/test_momentum_v1.py` | 2 | Factor smoke tests |
| `tests/unit/ranking/test_golden_ranking.py` | 1 | Fixed hash/ranks/scores regression |
| `tests/integration/api/test_rankings_api.py` | 1 | Full API + idempotency |

---

## 5. Database Schema

### 5.1 Migration `20260530_0003`

**`ranking_runs` extensions:**

| Column | Type | Notes |
|--------|------|-------|
| `universe_code` | VARCHAR(32) NOT NULL | Backfilled `'UNKNOWN'` for existing rows |
| `benchmark_symbol` | VARCHAR(32) NOT NULL | Backfilled `'UNKNOWN'` |
| `filter_config_hash` | VARCHAR(64) NOT NULL | Backfilled from `inputs_hash` |
| `normalization_method` | VARCHAR(16) NOT NULL | Default `'percentile'` |
| `error_message` | TEXT NULL | Set on failed runs |

**New table `ranking_performance_snapshots`:**

```sql
id              UUID PK
ranking_run_id  UUID FK → ranking_runs (CASCADE)
stock_id        UUID FK → stocks (CASCADE)
return_5d       NUMERIC(18,8) NULL
return_10d      NUMERIC(18,8) NULL
return_20d      NUMERIC(18,8) NULL
return_60d      NUMERIC(18,8) NULL
captured_at     TIMESTAMPTZ NOT NULL
UNIQUE (ranking_run_id, stock_id)
```

### 5.2 Metadata schema (`ranking_runs.metadata` JSONB)

```json
{
  "filter_config": { "...canonical UniverseFilterConfig..." },
  "universe_stock_count": 3,
  "ranked_stock_count": 3,
  "universe_exclusion_summary": { "MIN_PRICE_FAILED": 2 },
  "ranking_exclusion_summary": { "INSUFFICIENT_STRATEGY_HISTORY": 1 },
  "exclusion_summary": { "MIN_PRICE_FAILED": 2, "INSUFFICIENT_STRATEGY_HISTORY": 1 },
  "benchmark_available": false,
  "effective_weights": { "volatility_adjusted_momentum": "0.47058824", ... },
  "base_weights": { "...original weights..." },
  "weight_adjustment_reason": "benchmark_data_unavailable"
}
```

---

## 6. API Contract

**Base path:** `/api/v1/rankings`

### 6.1 `POST /run` → 201

**Request:**
```json
{
  "universe_code": "PI_PM_CORE",
  "as_of_date": "2025-06-01",
  "strategy_name": "momentum_v1",
  "strategy_version": "1.0.0",
  "benchmark_symbol": "^NSEI",
  "filter_config": {
    "min_history_days": 63,
    "min_avg_daily_traded_value": "10000000",
    "min_stock_price": "50"
  }
}
```

**Response highlights:** `inputs_hash`, `status`, `results[]`, `metadata.exclusion_summary`

**Idempotency:** Identical inputs → same `inputs_hash` → returns existing run (no duplicate persist).

### 6.2 `GET /latest`

Query params: `universe_code`, `strategy_name`, `strategy_version` (all optional filters).

### 6.3 `GET /{run_id}`

Full run with all results and factor breakdown in `score_components`.

### 6.4 `GET /{run_id}/top?n=10`

Top-N ranked securities (`n` ∈ [1, 100]).

### 6.5 Error responses

| Exception | HTTP | When |
|-----------|------|------|
| `NotFoundError` | 404 | Unknown universe, run, or no latest run |
| `StrategyNotFoundError` | 404 | Unknown strategy name/version |
| `RankingError` | 422 | Ranking computation/persist failure |

---

## 7. Strategy Reference — `momentum_v1` v1.0.0

### 7.1 Factors & weights

| Factor | Weight | Formula |
|--------|--------|---------|
| `volatility_adjusted_momentum` | 40% | 63d total return ÷ annualized vol (63d log returns × √252) |
| `volume_expansion` | 25% | 20d avg volume ÷ 50d avg volume |
| `trend_quality` | 20% | `0.5 × (Close/MA50) + 0.5 × (Close/MA200)` |
| `relative_strength` | 15% | Stock 63d return − benchmark 63d return |

### 7.2 History requirements

| Phase | Minimum bars |
|-------|----------------|
| Universe filter | 63 |
| Strategy (`momentum_v1`) | 201 (MA200 + 1) |

### 7.3 Benchmark resilience

When benchmark stock missing or has < 201 bars:

```
Original:  Momentum 40% | Volume 25% | Trend 20% | RS 15%
Adjusted:  Momentum 47.06% | Volume 29.41% | Trend 23.53%
```

Persisted in `metadata.effective_weights` and `metadata.weight_adjustment_reason`.

### 7.4 Scoring pipeline

1. Compute raw factors per stock
2. Exclude stocks where any **active** factor is `None`
3. Percentile-normalize each factor cross-sectionally (tie → average rank percentile)
4. Weighted sum → composite score (8 decimal places)
5. Sort: **score DESC, symbol ASC**
6. Assign ranks 1..N

### 7.5 Determinism contract

`inputs_hash` = SHA-256 of canonical JSON containing:
- `as_of_date`, `universe_code`, `filter_config_hash`
- Strategy name/version, benchmark symbol, normalization method
- Effective weights, included symbols (sorted)
- Serialized market data bars (date, close, volume) per symbol
- Serialized benchmark bars (if available)

**Golden fixture:** hash `97a8b26da6fc7a8ee03b67234ea85fb5e54af4b21f46d0d1a49a3b3b25ff91ec`  
Ranks: BBB.NS #1 (0.65), AAA.NS #2 (0.50), CCC.NS #3 (0.35)

---

## 8. Exclusion Reason Codes

| Code | Phase | Trigger |
|------|-------|---------|
| `NOT_IN_UNIVERSE` | Universe | Not active membership |
| `STOCK_INACTIVE` | Universe | `is_active = false` |
| `DATA_STATUS_NOT_ACTIVE` | Universe | `data_status != ACTIVE` |
| `INSUFFICIENT_HISTORY` | Universe | < 63 trading days |
| `NO_PRICE_DATA` | Universe | No bar on/before as_of |
| `MIN_PRICE_FAILED` | Universe | Latest close < ₹50 |
| `INSUFFICIENT_TRADED_VALUE` | Universe | 20d ADTV < threshold |
| `INSUFFICIENT_STRATEGY_HISTORY` | Ranking | < 201 bars for momentum_v1 |
| `FACTOR_COMPUTATION_FAILED` | Ranking | Required factor returned None |

---

## 9. Configuration

| Env var | Default | Used in code? |
|---------|---------|---------------|
| `RANKING_DEFAULT_BENCHMARK` | `^NSEI` | ✅ Yes |
| `RANKING_MIN_HISTORY_DAYS` | `63` | ✅ Yes |
| `RANKING_MIN_AVG_DAILY_TRADED_VALUE` | `10000000` | ✅ Yes |
| `RANKING_MIN_STOCK_PRICE` | `50` | ✅ Yes |
| `RANKING_MARKET_DATA_SOURCE` | `yahoo` | ✅ Yes |
| `RANKING_DEFAULT_STRATEGY` | `momentum_v1` | ⚠️ Defined, not wired to API default |
| `RANKING_DEFAULT_STRATEGY_VERSION` | `1.0.0` | ⚠️ Defined, not wired |
| `RANKING_DEFAULT_UNIVERSE_CODE` | `PI_PM_CORE` | ⚠️ Defined, not wired |

---

## 10. Review Checklist

### 10.1 Correctness (must review)

- [ ] ADTV formula: 20d avg volume × 20d avg close — is 20d window acceptable vs design "average daily"?
- [ ] Trend quality continuous formula matches spec exactly
- [ ] Weight redistribution math: `0.40/0.85 = 0.47058824` etc.
- [ ] Percentile normalization tie-breaking produces stable ranks
- [ ] `inputs_hash` includes all inputs that affect output (no missing fields)
- [ ] Tie-break order: score DESC, symbol ASC
- [ ] Universe 63d vs strategy 201d separation works for newer listings
- [ ] `MIN_VOL = 0.001` floor — acceptable for production vs false exclusions?

### 10.2 Data integrity (must review)

- [ ] Idempotency: `find_by_inputs_hash` before create — race condition under concurrency?
- [ ] Failed runs leave `inputs_hash = "pending"` — collision risk?
- [ ] `find_by_inputs_hash` does not filter by `COMPLETED` status
- [ ] Transaction rollback on partial persist failure
- [ ] Migration backfill strategy for existing `ranking_runs` rows

### 10.3 Auditability (must review)

- [ ] Exclusion **counts** persisted — sufficient for MVP audit?
- [ ] Per-stock exclusion details (`FilterDecision.reason_detail`) **not persisted** — acceptable gap?
- [ ] Factor breakdown in `ranking_results.score_components` complete for replay?
- [ ] `filter_config_hash` independently verifiable from config JSON?

### 10.4 Performance (should review)

- [ ] Market data loaded twice (universe filter + ranking engine) — acceptable for MVP scale?
- [ ] `_symbol_map()` N+1 queries on API responses
- [ ] No pagination on full run results endpoint

### 10.5 Security & validation (should review)

- [ ] No auth on ranking endpoints (consistent with Sprint 2?)
- [ ] `universe_code` / `strategy_name` injection via unsanitized strings?
- [ ] `filter_config` bounds validation (min_history_days ≥ 1, positive thresholds)

### 10.6 Test coverage gaps (should review)

- [ ] No test with benchmark present → relative strength included
- [ ] No test for `INSUFFICIENT_STRATEGY_HISTORY` exclusion path
- [ ] No test for empty tradable universe (0 ranked stocks)
- [ ] No test for concurrent duplicate run requests
- [ ] Integration test always excludes RS (no benchmark seeded)

---

## 11. Known Issues & Deviations

| Item | Severity | Description | Recommendation |
|------|----------|-------------|----------------|
| Unused config defaults | Low | 3 settings defined but not wired | Wire to API defaults or remove |
| Per-stock exclusions not persisted | Medium | Only aggregate counts in metadata | Sprint 4: `ranking_exclusions` table or JSONB array |
| Double market data load | Medium | Universe + ranking each query bars | Sprint 4: shared bar cache in service layer |
| `find_by_inputs_hash` no status filter | Low | Could return failed run | Add `status = COMPLETED` filter |
| Exclusion code naming | Info | `INSUFFICIENT_TRADED_VALUE` vs design example `INSUFFICIENT_LIQUIDITY` | Document as intentional |
| `MIN_VOL` lowered to 0.001 | Info | Deviation from implicit 0.01 | Document in strategy constants |
| No `universe_filter_runs` table | Info | Design allowed metadata-only audit | Acceptable for MVP |

---

## 12. How to Run Review Locally

```bash
# Setup
cd pi-pm
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Migrate
alembic upgrade head

# Tests
pytest -v
ruff check app tests

# Manual API smoke (requires DB + seed data)
uvicorn app.main:app --reload
curl -X POST http://localhost:8000/api/v1/rankings/run \
  -H "Content-Type: application/json" \
  -d '{"universe_code":"PI_PM_CORE","as_of_date":"2025-06-01"}'
```

---

## 13. Suggested Review Order

1. **Migration** — `migrations/versions/20260530_0003_sprint3_ranking.py`
2. **Universe filter** — `app/universe/filter_engine.py` + unit test
3. **Strategy math** — `app/ranking/strategies/momentum_v1.py` + `math_utils.py`
4. **Engine orchestration** — `app/ranking/engine.py` + `normalizer.py` + `hashing.py`
5. **Persistence & idempotency** — `ranking_service.py` + repositories
6. **API contract** — `rankings.py` + `schemas/ranking.py`
7. **Golden + integration tests** — verify determinism claims
8. **Cross-cutting** — config, constants, deps wiring

---

## 14. Sign-off Template

| Reviewer | Area | Status | Notes |
|----------|------|--------|-------|
| | Universe filter | ☐ Approve ☐ Changes | |
| | Ranking engine | ☐ Approve ☐ Changes | |
| | Strategy math | ☐ Approve ☐ Changes | |
| | API / schemas | ☐ Approve ☐ Changes | |
| | Migration / schema | ☐ Approve ☐ Changes | |
| | Tests | ☐ Approve ☐ Changes | |
| | **Overall Sprint 3** | ☐ Approve ☐ Changes | |

---

*Generated for Pi-PM Sprint 3 code review. App version 0.3.0.*
