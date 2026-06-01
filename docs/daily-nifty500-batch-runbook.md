# Daily NIFTY 500 Batch — Runbook

**Branch:** `feature/sprint-8.6-daily-ingestion`  
**API prefix:** `/api/v1/ops/daily-batch`  
**Migration:** `20260607_0015`  
**Client:** `scripts/run_daily_nifty500_batch.py`

## Prerequisites

```bash
cd docker && docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
alembic upgrade head   # 20260607_0015
curl http://127.0.0.1:8000/api/v1/health
```

## Normal daily delta (full pipeline)

```bash
python scripts/run_daily_nifty500_batch.py --assume-session-done
```

Or POST:

```json
POST /api/v1/ops/daily-batch/runs
{
  "assume_session_done": true,
  "dry_run": false
}
```

## Plan only (no side effects)

```bash
python scripts/run_daily_nifty500_batch.py --dry-run
```

## Rankings + validation + factor + exit only (skip ingest)

```json
{
  "from_date": "2026-05-29",
  "target_date": "2026-06-01",
  "force_from_date": true,
  "force_recompute": true,
  "force_regenerate_rankings": true,
  "phases": {
    "ingest": false,
    "rankings": true,
    "validation": true,
    "factor_ic": true,
    "exit_research": true,
    "research_intelligence": false
  }
}
```

## Force reprocess from a date (includes ingest)

```json
{
  "from_date": "2026-01-01",
  "target_date": "2026-05-30",
  "force_from_date": true,
  "force_recompute": true,
  "force_regenerate_rankings": true,
  "allow_partial_ingest": true
}
```

## Force re-ingest market data from a calendar date

Use when incremental ingest wrongly flagged stocks or you need to refresh OHLCV from a given day:

```json
POST /api/v1/market-data/ingest
{
  "symbols": ["RELIANCE.NS", "^NSEI"],
  "period": "5y",
  "ingestion_mode": "incremental",
  "since_date": "2026-06-01"
}
```

Bulk file of symbols:

```bash
python scripts/reingest_symbols_since.py \
  --since 2026-06-01 \
  --symbols-file docs/my-symbols.txt
```

**Always ingest `^NSEI` through the target day** before expecting rankings on that date.

## Traceability

- `GET /api/v1/ops/daily-batch/runs/{run_id}` — status and phase results  
- `GET /api/v1/ops/daily-batch/runs/{run_id}/trace` — child artifact IDs and `current_load`  
- `scripts/monitor_daily_batch.sh <run_id>` — poll every 30s (local)

## Phases (default)

1. Incremental Yahoo ingest (`ingestion_mode=incremental`)  
2. Rankings (gap days per strategy; `force_regenerate_rankings` → `RankingRunRequest.force_regenerate`)  
3. Validation backfill  
4. Factor IC backfill (requires validation `status=completed`)  
5. Exit research backfill (requires validation `status=completed`)  

## Known gotchas

| Issue | Mitigation |
|-------|------------|
| ~150 stocks `data_status=ERROR` after batch | Was caused by empty incremental when already at latest bar; fixed in `market_data_service`. Reset `ACTIVE` + optional `since_date` re-ingest. |
| Rankings only ~320 stocks | 150 were `ERROR`; after fix expect ~450+ ranked. |
| Validation `insufficient_data` on latest day | Need forward bars (≥5 trading days for 5d horizon). Ingest later sessions, then re-validate. |
| Factor IC / exit `metrics_written: 0` | No `completed` validation reports in window. |
| `DUMMYVEDL*.NS` in universe | Remove from seed; permanent Yahoo metadata failure. |
| `allow_partial_ingest: false` | Batch fails if any symbol fails; use `true` for production cron. |

## Cron example

```cron
0 16 * * 1-5 cd /path/to/pi-pm && python scripts/run_daily_nifty500_batch.py >> /var/log/pipm-daily-batch.log 2>&1
```

Ensure Docker `api` is up before the job runs.
