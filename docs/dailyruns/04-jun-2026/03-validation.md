# Step 03 — Validation (2026-06-04)


## Batch validation phase

```json
{
  "failed": 0,
  "reused": 0,
  "validated": 2,
  "runs_found": 2
}
```

## Per ranking run (API)

| Ranking run | Strategy | Validation status |
|-------------|----------|-------------------|
| `1ffc946f-4e09-4700-a89e-974b41b853bd` | breakout_v1 | `insufficient_data` |
| `8c4109d4-0f83-4cf4-8bf3-f2c1cf0c7d30` | momentum_v1 | `insufficient_data` |

Expected for same-day as-of: forward return horizons need future sessions (see runbook). Re-validate after additional market days ingest.

**Trace validation_report_ids:** empty in trace lineage (reports may be keyed by ranking_run_id directly).

