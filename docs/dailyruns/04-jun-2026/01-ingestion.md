# Step 01 — Ingestion (2026-06-04)


**Daily batch run:** `f4f7bf42-8d7a-432e-a9f5-13156de861ea`  
**Target date:** 2026-06-04  
**Benchmark:** `^NSEI` (included in batch universe ingest; no separate remediation required)

## Request

```json
POST /api/v1/ops/daily-batch/runs
{"target_date":"2026-06-04","from_date":"2026-06-04","force_from_date":true,"force_recompute":true,"force_regenerate_rankings":true,"allow_partial_ingest":true}
```

## Phase result

```json
{
  "batches": 21,
  "rows_updated": 497,
  "rows_inserted": 3,
  "symbols_failed": 4,
  "symbols_succeeded": 500
}
```

## Ingestion batches (trace)

- **Count:** 21 batch IDs recorded in lineage
- **Symbols:** 500 succeeded / 4 failed
- **Rows:** 3 inserted, 497 updated

## Notes

Jun-3 lesson: ensure `^NSEI` through target day before rankings. Batch uses `benchmark_symbol: ^NSEI` by default; rankings completed for 2026-06-04 without NSEI gap remediation.

