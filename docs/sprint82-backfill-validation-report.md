# Sprint 8.2 Backfill Validation Report

**Date:** 2026-05-31  
**Branch:** `feature/sprint82-factor-ic-analytics`  
**Alembic head:** `20260602_0010`

---

## 1. Root Cause

### Primary (HTTP 500 on first backfill)

**`coverage_label` VARCHAR(16) overflow**

| Value | Length | Column limit |
|-------|--------|--------------|
| `adequate_coverage` | **17** | VARCHAR(16) |

When regime coverage > 15%, `FactorMetricsEngine.coverage_label()` returns `adequate_coverage`. PostgreSQL rejected the INSERT with a string truncation / value error during SQLAlchemy flush. This affected most NIFTY_500 ALL-split rows (e.g. `atr_expansion`, `sample_size=99232`, `ranked_days=236`).

### Secondary (backfill failure on retry)

**Daily metrics upsert duplicate-key in same session**

`upsert_daily()` selected existing rows from DB but did not `flush()` after each insert. SQLAlchemy batched pending inserts; duplicate keys within the same session violated `uq_factor_daily_metrics_run_factor`.

---

## 2. Files Changed

| File | Change |
|------|--------|
| `migrations/versions/20260602_0010_widen_factor_metric_label_columns.py` | Widen `coverage_label`, `stability_label` to VARCHAR(32) |
| `migrations/versions/20260601_0009_sprint82_factor_analytics.py` | Fresh-install columns also VARCHAR(32) |
| `app/models/factor_analytics.py` | `String(32)` for label columns |
| `app/db/repositories/factor_performance_metric_repository.py` | `flush()` after each `upsert_daily()` |
| `tests/unit/factor_analytics/test_label_column_lengths.py` | Assert label lengths |
| `tests/unit/factor_analytics/test_daily_upsert.py` | Idempotent daily upsert in-session |

---

## 3. Migration Changes

| Revision | Action |
|----------|--------|
| `20260601_0009` | Original Sprint 8.2 schema (label cols updated to 32 for fresh installs) |
| `20260602_0010` | **Corrective:** `ALTER COLUMN coverage_label, stability_label → VARCHAR(32)` |

Applied: `alembic upgrade head` → `20260602_0010 (head)`

---

## 4. ORM vs Migration Diff (FactorPerformanceMetric)

All ORM fields present in migration after fix:

| Field | Migration | ORM | Match |
|-------|-----------|-----|-------|
| `dataset_split` | VARCHAR(16) | String(16) | ✅ |
| `regime_coverage_pct` | NUMERIC(18,8) | Numeric(18,8) | ✅ |
| `stability_score` | NUMERIC(18,8) | Numeric(18,8) | ✅ |
| `stability_label` | VARCHAR(32)* | String(32)* | ✅ |
| `coverage_label` | VARCHAR(32)* | String(32)* | ✅ |
| `bootstrap_sample_count` | INTEGER | Integer | ✅ |
| `bootstrap_method` | VARCHAR(64) | String(64) | ✅ |

\*Was VARCHAR(16) in original 0009 — root cause bug.

---

## 5. Validation Commands Executed

```bash
# Tests
pytest tests/unit/factor_analytics -q          # 27 passed
pytest tests/ -q                               # 178 passed

# Migration
alembic current                                # 20260602_0010 (head)
curl http://localhost:8000/api/v1/health       # {"status":"ok",...}

# Docker rebuild (attempted)
cd docker && docker compose down && docker compose build --no-cache api && docker compose up -d
# → permission denied on docker.sock (proceeded with local API + alembic)

# Backfill (~7 min)
python scripts/backfill_sprint82_factor_analytics.py \
  --universe-code NIFTY_500 \
  --start-date 2024-01-01 \
  --end-date 2025-05-30 \
  --holdout-start-date 2025-01-01 \
  --force-recompute
# → run_id=9f61afbe-bed1-4509-9ce5-271a67d9ddb6 status=completed

# API validation
curl ".../performance?universe_code=NIFTY_500&regime_label=BULL_LOW_VOL&horizon=20&dataset_split=HOLDOUT&start_date=2024-01-01&end_date=2025-05-30"
curl ".../leaderboard?regime_label=BULL_LOW_VOL&horizon=20&universe_code=NIFTY_500&start_date=2024-01-01&end_date=2025-05-30"
curl ".../train-holdout-drift?universe_code=NIFTY_500&regime_label=BULL_LOW_VOL&horizon=20&start_date=2024-01-01&end_date=2025-05-30"
```

---

## 6. Row Counts Produced

| Table | Count |
|-------|------:|
| `factor_performance_runs` | 2 |
| `factor_daily_metrics` | 11,136 |
| `factor_performance_metrics` | 448 |

Latest run: `status=completed`, `reports_processed=349`, `metrics_written=448`, `error_message=NULL`

Split breakdown (aggregate metrics):

| dataset_split | count |
|---------------|------:|
| ALL | 160 |
| HOLDOUT | 160 |
| TRAIN | 128 |

---

## 7. Sample Leaderboard Response

```json
{
  "regime_label": "BULL_LOW_VOL",
  "horizon": 20,
  "dataset_split": "HOLDOUT",
  "strategy_name": "breakout_v1",
  "universe_code": "NIFTY_500",
  "entries": [
    {
      "factor_name": "relative_strength_acceleration",
      "current_weight": 0.05,
      "train_ic": 0.03349636,
      "holdout_ic": 0.07750318,
      "ic_drift": -0.04400682,
      "stability_score": 0.76190476,
      "stability_label": "stable",
      "regime_coverage_pct": 0.20588235,
      "coverage_label": "adequate_coverage",
      "is_statistically_significant": true,
      "confidence": "high"
    }
  ]
}
```

Performance endpoint confirms `coverage_label: "adequate_coverage"` persists successfully post-fix.

---

## 8. Remaining Risks

1. **Docker not rebuilt from agent** — Docker socket permission denied; local API used. Rebuild container before production deploy to pick up repository fix.
2. **Backfill runtime** — ~7 minutes for NIFTY_500 × 4 horizons; may timeout HTTP clients; prefer CLI script for large windows.
3. **Per-row flush on daily upserts** — Correct but slower; acceptable for current volume; consider batched `ON CONFLICT` if scale grows.
4. **Holdout sample** — Only ~21 BULL_LOW_VOL holdout days in window; IC estimates have wide confidence intervals.
5. **Partial failed run artifact** — First interrupted run left 1 failed run row; latest run completed cleanly.

---

## 9. Recommendation

**Ready for PR** — after including migration `20260602_0010` and daily upsert flush fix.

Success criteria met:
- ✅ Backfill completes (no HTTP 500)
- ✅ Metrics persist (448 aggregate, 11,136 daily)
- ✅ Leaderboard returns non-empty JSON with train/holdout/drift
- ✅ `adequate_coverage` persists correctly
- ✅ 178 tests passing
