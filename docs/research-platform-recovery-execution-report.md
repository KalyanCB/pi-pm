# Research Platform Recovery — Execution Report

**Date:** 2026-06-02  
**Scope:** Deterministic research stack only (no ARGS / TARC / QRC / CRO / prompts / OpenAI changes)  
**Reference audits:** `docs/pipm-research-platform-audit.md`, `docs/pipm-research-platform-root-cause-analysis.md`, `docs/pipm-research-platform-recovery-plan.md`

---

## 1) Root causes found

| Symptom | Root cause | Layer |
|--------|------------|--------|
| `regime_history = 0` | `RegimeAnalyticsService.compute_and_store_regime()` existed but was **never scheduled**; only on-demand API reads triggered storage | Orchestration gap |
| `strategy_regime_performance = 0` (pre-recovery) | `refresh_strategy_regime_performance()` existed but was **not in daily batch**; manual `POST /observability/regime/performance/refresh` only | Orchestration gap |
| `factor_performance_metrics = 0` (pre-recovery) | Factor backfill used **narrow date windows** (e.g. latest as-of only) where validations are `insufficient_data`; observation loader correctly requires `status=completed` + non-null forward returns | Scheduling / window selection |
| `research_intelligence_* = 0` (pre-recovery) | `ResearchIntelligenceService.generate_executive_pack()` **not wired** into batch | Orchestration gap |
| ARGS looked “empty” | Downstream **packet inputs** (factor IC, regime performance) were empty — not ARGS packet builder or committee logic | Misattributed symptom |

**Confirmed:** Ranking, validation, exit research, and packet **builders** were operational. Failure mode was **missing jobs + wrong backfill windows**, not broken algorithms.

---

## 2) Code changes (deterministic stack only)

### Phase 1 — Regime analytics

- **`app/services/regime_analytics_service.py`**
  - Added `backfill_regime_history(start_date, end_date, benchmark_symbol)` using `TradingCalendar` + `classify_regime()` → `regime_history` upserts.
- **`app/db/repositories/regime_analytics_repository.py`**
  - Added `count_regime_history()` for planner gaps.
- **`app/services/daily_batch_service.py`**
  - New phase **`regime_history`** after validation.
  - Existing **`regime_performance`** refresh retained (aggregates `validation_horizon_metrics`).

### Phase 2 — Factor IC

- **`app/ops/daily_batch/evidence_windows.py`**
  - Resolves backfill window from **completed** validation dates only.
  - Fixes case where `plan_from_date` > last completed as-of (recent `insufficient_data` tail).
- **`app/factor_analytics/observation_loader.py`** (unchanged — already correct)
  - Filters: `VALIDATION_STATUS_COMPLETED`, non-null horizon return column, non-null regime label.
- **`app/services/signal_validation_service.py`**
  - `backfill(..., universe_code=...)` scopes validation to universe.
- **`app/ops/daily_batch/batch_planner.py`**
  - `factor_ic_needed` only when `evidence_window` exists (no blind `force_from_date` factor runs).

### Phase 3 — Research intelligence

- **`app/services/daily_batch_service.py`**
  - Phase **`research_intelligence`** runs after factor IC when evidence window exists.
- **`scripts/run_research_platform_recovery.py`**
  - One-shot recovery + metrics snapshot.

### Phase 4 — Orchestration order (target)

```
Ingest → Rankings → Validation → Regime History → Regime Performance
  → Factor IC → Research Intelligence → Exit Research
```

Implemented in `DailyBatchService` (phase flags in `app/schemas/daily_batch.py`).

### Supporting

- **`app/core/constants.py`** — `DailyBatchPhase.REGIME_HISTORY`, artifact `regime_history_backfill`
- **`app/ops/daily_batch/traceability.py`** — artifact recording for regime history backfill
- **`app/ops/research_platform_metrics.py`** — table count snapshots
- **`scripts/run_recovery_batch.py`** — recovery-only batch (from prior session; still valid)

**Not modified:** `app/args/**`, committee plugins, prompts, packet schema, OpenAI wiring.

---

## 3) Tables populated (verification run)

Recovery executed via `scripts/run_research_platform_recovery.py` + daily batch run `25965b31-0d13-42ed-8f21-03084ea3f7fe`.

Metrics file: `docs/research-platform-recovery-metrics.json`

| Table | Before | After | Δ |
|-------|--------|-------|---|
| `regime_history` | 0 | **348** | +348 |
| `strategy_regime_performance` | 8 | **8** | 0 (already populated) |
| `factor_performance_metrics` | 456 | **936** | +480 |
| `factor_daily_metrics` | 11,832 | **12,120** | +288 |
| `factor_performance_runs` | 8 | **10** | +2 |
| `research_intelligence_runs` | 1 | **2** | +1 |
| `research_intelligence_reports` | 9 | **18** | +9 |
| `validation_horizon_metrics` | 4,712 | 4,712 | 0 |

Regime history backfill: **348 trading days** (2025-01-01 → 2026-06-02), **348 rows written**, 0 skipped.

Factor IC evidence window used: **2025-04-28 → 2026-05-22** (completed validations with forward returns).

---

## 4) Before / after metrics (audit baseline vs post-recovery)

**Audit baseline (user-reported empty state):**

```text
factor_performance_metrics     = 0
factor_daily_metrics           = 0
strategy_regime_performance    = 0
regime_history                 = 0
research_intelligence_runs     = 0
research_intelligence_reports  = 0
```

**Post-recovery (this environment):**

```text
factor_performance_metrics     = 936
factor_daily_metrics           = 12,120
strategy_regime_performance    = 8
regime_history                 = 348
research_intelligence_runs     = 2
research_intelligence_reports  = 18
```

---

## 5) Verification SQL

```sql
-- Acceptance gates
SELECT COUNT(*) FROM regime_history;                    -- expect > 0
SELECT COUNT(*) FROM strategy_regime_performance;       -- expect > 0
SELECT COUNT(*) FROM factor_performance_metrics;        -- expect > 0
SELECT COUNT(*) FROM factor_daily_metrics;              -- expect > 0
SELECT COUNT(*) FROM research_intelligence_reports;     -- expect > 0

-- Regime history coverage
SELECT MIN(as_of_date), MAX(as_of_date), COUNT(*)
FROM regime_history
WHERE benchmark_symbol = '^NSEI';

-- Strategy regime performance
SELECT strategy_name, strategy_version, regime_label, horizon, sample_count, avg_ic
FROM strategy_regime_performance
ORDER BY strategy_name, regime_label;

-- Factor IC runs with output
SELECT id, strategy_name, status, reports_processed, metrics_written,
       as_of_date_start, as_of_date_end
FROM factor_performance_runs
ORDER BY started_at DESC
LIMIT 10;

-- Completed validations in factor window (driver for IC)
SELECT COUNT(*)
FROM ranking_validation_reports rvr
JOIN ranking_runs rr ON rr.id = rvr.ranking_run_id
WHERE rvr.status = 'completed'
  AND rr.universe_code = 'NIFTY_500'
  AND rr.as_of_date BETWEEN '2025-04-28' AND '2026-05-22';

-- Research intelligence
SELECT report_type, universe_code, created_at
FROM research_intelligence_reports
ORDER BY created_at DESC;
```

---

## 6) Demonstration checklist

| # | Requirement | Evidence |
|---|-------------|----------|
| 1 | Regime performance generated | 8 rows (`4` regimes × `2` strategies, horizon 20) |
| 2 | Factor IC generated | 936 `factor_performance_metrics`; runs show `metrics_written > 0` |
| 3 | Research intelligence generated | 18 reports (9 types × 2 runs) |
| 4 | Regime history generated | 348 `regime_history` rows for `^NSEI` |
| 5 | No synthetic data | All rows from ranking/validation/market-data pipelines |
| 6 | ARGS untouched | No changes under `app/args/` |

---

## 7) Remaining gaps

1. **Latest as-of validation tail** — Dates near `market_data.max(date)` (e.g. 2026-06-01, 2026-06-02) remain `insufficient_data` until forward horizons exist. Rankings still work; same-day horizon validation does not.
2. **Incremental daily batch** — Full holdout regime-history backfill (~348 days) should run once; daily runs should only backfill `plan.from_date → target` (already scoped in batch).
3. **`force_from_date` ranking gaps** — Planner may list large `ranking_gaps` when `force_from_date=true`; use normal incremental batch for production.
4. **Exit research** — Recovery script skipped exit phase; full target pipeline includes exit **after** research intelligence.
5. **ARGS reassessment** — Defer TARC/QRC tuning until packet quant blocks are verified on a **completed-validation** as-of (e.g. 2026-05-22) and on **latest** ranking with `require_completed_validation=false`.

---

## 8) Recommended next steps

1. **Production daily batch** — Run with default phases (including `regime_history`, `regime_performance`, `factor_ic`, `research_intelligence`) without `force_from_date` after market ingest.
2. **Monitor** — Alert if `factor_performance_metrics` or `strategy_regime_performance` counts stall while `validation_horizon_metrics` grows.
3. **Packet spot-check** — Rebuild investment review packet for ranking run `6f067f04-299e-486c-b7ab-85a7bb46c683` (2026-05-22, completed validation); confirm non-empty `horizon_metrics`, `factor_ic`, `strategy_regime_performance`.
4. **Only then** — Resume ARGS/TARC/QRC quality work with real quant evidence.

---

## Operational commands

```bash
# Full recovery snapshot (regime history + performance; optional factor/intel in script)
cd /Users/kalyancb/pi-pm && source .venv/bin/activate
PYTHONPATH=. python3 scripts/run_research_platform_recovery.py

# Recovery-only daily batch phases
PYTHONPATH=. python3 scripts/run_recovery_batch.py

# Manual regime performance refresh (still available)
curl -X POST "http://127.0.0.1:8000/api/v1/observability/regime/performance/refresh?strategy_name=breakout_v1&strategy_version=1.0.0&horizon=20"
```

**Daily batch trace (example):** `GET /api/v1/ops/daily-batch/runs/25965b31-0d13-42ed-8f21-03084ea3f7fe/trace`
