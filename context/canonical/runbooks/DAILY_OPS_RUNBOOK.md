# Daily Ops Runbook — Paper Trading Pilot

**Audience:** Product Operations  
**Frequency:** Every trading day post-close

---

## 1. Trigger daily batch

```bash
python scripts/run_daily_nifty500_batch.py \
  --portfolio \
  --pilot-auto-approve \
  --pilot-auto-execute
```

Or via API: `POST /api/v1/ops/daily-batch/runs` with portfolio flags (see ADR-028).

---

## 2. Check command center

```bash
curl -s http://localhost:8000/api/v1/pilot/command-center | jq .
```

**Green:** `status: "healthy"`, `alert_summary.critical: 0`

---

## 3. Review dashboards (5 min)

| Dashboard | Endpoint | Check |
|-----------|----------|-------|
| Pilot | `/pilot/dashboard/pilot` | NAV trend, daily activity |
| Health | `/pilot/dashboard/health` | Recon PASS, analytics gate open |
| Recommendations | `/pilot/dashboard/recommendations` | BUY/EXIT counts sane |
| Operational | `/pilot/dashboard/operational` | Batch completed |

---

## 4. Resolve alerts

```bash
curl -s http://localhost:8000/api/v1/pilot/alerts | jq .
```

| Alert | Action |
|-------|--------|
| `batch_failed` | Check batch error; re-run or fix ingest |
| `reconciliation_fail` | Investigate cash ledger; do not trade until PASS |
| `nav_missing` | Run `POST /portfolio/nav-snapshot` or re-run batch portfolio phase |
| `recommendation_zero` | Check ranking/validation completed for target day |

---

## 5. Generate daily report

```bash
python scripts/generate_pilot_reports.py daily --as-of-date $(date +%Y-%m-%d)
```

Output: `docs/paper-pilot/reports/DAILY_REPORT_*.md`

---

## 6. Weekly (Fridays)

```bash
python scripts/generate_pilot_reports.py weekly
curl -s http://localhost:8000/api/v1/pilot/dashboard/trust | jq .
curl -s http://localhost:8000/api/v1/pilot/dashboard/committee | jq .
```

---

## Kill switch

If `reconciliation_fail` persists 2 days:

1. Disable `pilot_auto_execute` on batch
2. File incident in ops log
3. Resume only after manual recon PASS
