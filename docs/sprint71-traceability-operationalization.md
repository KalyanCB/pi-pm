# Sprint 7.1 — Traceability Operationalization

Operationalizes Sprint 7 traceability by backfilling from existing persisted artifacts and ensuring reuse paths populate traceability tables without reranking or revalidating.

## Design Summary

| Phase | What | How |
|-------|------|-----|
| 1A | `ranking_factor_contributions` | `sync_from_results()` from `ranking_results.score_components` |
| 1B | `validation_horizon_metrics` / `validation_decile_metrics` | `replace_for_report()` from `ranking_validation_reports.horizon_metrics` JSONB |
| 1C | `ranking_runs` metadata columns | Derived from `metadata` JSONB + linked validation report |
| 1D | `regime_history` | Copied from stored validation regime fields |
| 1E | `run_lineage_records` | Best-effort links via `ensure_validation_lineage()` |
| 2F–H | Forward paths | `ensure_*` on ranking/validation reuse early returns |

**No business logic changes.** Reuse decisions unchanged. Idempotent writes safe to rerun.

## Files Modified

| File | Change |
|------|--------|
| `app/services/traceability_service.py` | Added `ensure_ranking_traceability`, `ensure_validation_traceability`, `ensure_validation_lineage` |
| `app/services/ranking_service.py` | Call `ensure_ranking_traceability` on reuse path |
| `app/services/signal_validation_service.py` | Call `ensure_validation_traceability` on reuse paths |
| `app/db/repositories/ranking_factor_contribution_repository.py` | Added `has_for_run()` |
| `app/db/repositories/validation_metrics_repository.py` | Added `has_for_report()` |
| `scripts/backfill_sprint7_traceability.py` | **New** historical backfill CLI |
| `tests/unit/services/test_sprint71_traceability.py` | **New** tests |
| `docs/sprint71-traceability-operationalization.md` | **New** this document |

## Migration Impact

**None.** Uses existing Sprint 7 schema (`20260530_0007`).

## Verification SQL

### Before backfill (baseline)

```sql
SELECT 'ranking_factor_contributions' AS t, COUNT(*) FROM ranking_factor_contributions
UNION ALL SELECT 'validation_horizon_metrics', COUNT(*) FROM validation_horizon_metrics
UNION ALL SELECT 'validation_decile_metrics', COUNT(*) FROM validation_decile_metrics
UNION ALL SELECT 'regime_history', COUNT(*) FROM regime_history
UNION ALL SELECT 'run_lineage_records', COUNT(*) FROM run_lineage_records
UNION ALL SELECT 'ranking_runs.weight_config_hash set', COUNT(*)
  FROM ranking_runs WHERE weight_config_hash IS NOT NULL
UNION ALL SELECT 'ranking_runs.ranked_stock_count set', COUNT(*)
  FROM ranking_runs WHERE ranked_stock_count IS NOT NULL;
```

**Expected before:** all zeros (or near-zero).

### Source data available

```sql
SELECT COUNT(*) AS total_reports,
       COUNT(*) FILTER (WHERE horizon_metrics IS NOT NULL AND horizon_metrics != '{}'::jsonb)
FROM ranking_validation_reports;

SELECT COUNT(*) AS total_results,
       COUNT(*) FILTER (WHERE score_components IS NOT NULL AND score_components != '{}'::jsonb)
FROM ranking_results;
```

### After backfill (expected)

| Table / column | Expected approximate count |
|----------------|---------------------------|
| `ranking_factor_contributions` | multiple rows per ranking result (factors × stocks) |
| `validation_horizon_metrics` | ~410 reports × 4 horizons ≈ **1640** |
| `validation_decile_metrics` | ~410 × 4 × 10 deciles ≈ **16400** (varies) |
| `regime_history` | distinct (as_of_date, benchmark) from completed validations |
| `run_lineage_records` | ≥ 410 `validates_ranking` links |
| `ranking_runs.weight_config_hash` | completed runs with `metadata.effective_weights` |
| `ranking_runs.ranked_stock_count` | completed runs with results or metadata |

### Coverage gap checks (should return 0)

```sql
SELECT COUNT(*) AS missing_factor_backfill
FROM ranking_runs rr
WHERE rr.status = 'completed'
  AND EXISTS (
    SELECT 1 FROM ranking_results r
    WHERE r.ranking_run_id = rr.id
      AND r.score_components IS NOT NULL
      AND r.score_components != '{}'::jsonb
  )
  AND NOT EXISTS (
    SELECT 1 FROM ranking_factor_contributions fc WHERE fc.ranking_run_id = rr.id
  );

SELECT COUNT(*) AS missing_horizon_backfill
FROM ranking_validation_reports rvr
WHERE rvr.status = 'completed'
  AND rvr.horizon_metrics IS NOT NULL
  AND rvr.horizon_metrics != '{}'::jsonb
  AND NOT EXISTS (
    SELECT 1 FROM validation_horizon_metrics vhm
    WHERE vhm.validation_report_id = rvr.id
  );

SELECT ranking_run_id, stock_id, factor_name, COUNT(*)
FROM ranking_factor_contributions
GROUP BY 1, 2, 3
HAVING COUNT(*) > 1;

SELECT validation_report_id, horizon, COUNT(*)
FROM validation_horizon_metrics
GROUP BY 1, 2
HAVING COUNT(*) > 1;
```

## Production Runbook

### Step 1 — Snapshot baseline

```bash
docker compose exec db psql -U pipm -d pipm -c "
SELECT 'ranking_factor_contributions' AS t, COUNT(*) FROM ranking_factor_contributions
UNION ALL SELECT 'validation_horizon_metrics', COUNT(*) FROM validation_horizon_metrics;
"
```

### Step 2 — Deploy Sprint 7.1 code

```bash
docker compose build api && docker compose up -d api
docker compose exec api grep -n ensure_ranking_traceability app/services/ranking_service.py
```

### Step 3 — Dry run

```bash
docker compose exec api python scripts/backfill_sprint7_traceability.py --all --dry-run
```

### Step 4 — Backfill

```bash
docker compose exec api python scripts/backfill_sprint7_traceability.py --ranking
docker compose exec api python scripts/backfill_sprint7_traceability.py --validation
docker compose exec api python scripts/backfill_sprint7_traceability.py --regime
docker compose exec api python scripts/backfill_sprint7_traceability.py --lineage
```

### Step 5 — Verify gap checks return 0

### Step 6 — Regime performance refresh

```bash
curl -X POST "http://localhost:8000/api/v1/observability/regime/performance/refresh?strategy_name=breakout_v1&strategy_version=1.0.0&horizon=20"
```

## Test Results

```bash
.venv/bin/python -m pytest tests/unit/services/test_sprint71_traceability.py -v
.venv/bin/python -m pytest -q
```
