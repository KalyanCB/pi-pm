# Operations Runbook

Primary legacy runbook: [daily-nifty500-batch-runbook.md](../../daily-nifty500-batch-runbook.md).

---

## Daily NIFTY 500 batch

```bash
# Dry run
python scripts/run_daily_nifty500_batch.py --dry-run

# Production-style (session already done)
python scripts/run_daily_nifty500_batch.py --assume-session-done

# Force rebuild from date
python scripts/run_daily_nifty500_batch.py \
  --force-from-date 2026-05-20 \
  --force-regenerate-rankings
```

**API:** `POST /api/v1/ops/daily-batch/runs` · `GET .../runs/{id}` · `GET .../trace`

---

## ARGS top-20

```bash
ARGS_QRC_USE_SQE=false python scripts/run_args_top20.py --as-of-date 2026-06-04
```

Document flag in ops logs ([dailyruns/08-args.md](../../dailyruns/04-jun-2026/08-args.md)).

---

## Ingestion recovery

```bash
python scripts/reingest_symbols_since.py --since 2026-05-01
python scripts/run_recovery_batch.py
```

**Benchmark:** Ensure `^NSEI` ingested through target `as_of_date`.

---

## Traceability backfill

```bash
python scripts/backfill_sprint7_traceability.py --all
```

---

## Ranking research reports

```bash
python scripts/generate_ranking_root_cause_reports.py
```

---

## Regime presets

```bash
python scripts/init_regime_policy_presets.py
```

---

## Gotchas

| Issue | Action |
|-------|--------|
| Default universe `PI_PM_CORE` | Pass `NIFTY_500` in API/scripts |
| Docker stale code | Rebuild image, restart API |
| Validation `insufficient_data` | Wait for forward tail or backfill bars |
| Batch `already_current` | `force_from_date` + `force_regenerate_rankings` |
| O(n²) validation pooling | Use pooled metrics API path |

---

## Example daily log structure

`docs/dailyruns/<DD-mon-YYYY>/00-prerequisites.md` … `09-best-bets.md`

See [04-jun-2026 example](../../dailyruns/04-jun-2026/00-prerequisites.md).
