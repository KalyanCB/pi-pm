# Pilot Alerting Framework

**Implementation:** `app/ops/pilot/alerting.py`  
**API:** `GET /api/v1/pilot/alerts`

---

## Design principles

1. **Read-only** — alerts evaluate state; they never mutate portfolio or recommendations
2. **In-app first** — API returns alerts; external delivery is ops-configured
3. **Severity-gated** — critical alerts should block pilot progression

---

## Alert catalogue

| Code | Severity | Trigger | Operator action |
|------|----------|---------|-----------------|
| `batch_failed` | critical | Latest batch `status=failed` | Fix root cause; re-run batch |
| `reconciliation_fail` | critical | Latest recon `status=FAIL` | Stop auto-execute; fix ledger |
| `portfolio_cash_negative` | critical | Cash ledger < 0 | Audit trades; correct entries |
| `batch_stale` | warning | No batch within 3 days | Run batch manually |
| `batch_missing_portfolio` | warning | Portfolio flag on but no portfolio phases in results | Check batch config |
| `reconciliation_missing` | warning | No recon for expected date | Run `POST /portfolio/reconcile` |
| `nav_missing` | warning | No NAV for as-of date | Run nav snapshot |
| `recommendation_zero` | warning | Rec runs exist but zero results | Check ranking linkage |
| `recommendation_run_failed` | warning | Rec run not completed | Check rec service logs |
| `approval_backlog` | info | >10 BUY candidates unapproved | Review queue (if HITL mode) |
| `exit_backlog` | info | >5 pending exit recs | Review exit monitor output |

---

## External delivery (recommended)

Configure outside the app:

| Channel | Monitor | Threshold |
|---------|---------|-----------|
| Cron + curl | `/pilot/alerts` | Any `critical` |
| Slack webhook | Parse alerts JSON | `batch_failed`, `reconciliation_fail` |
| Email | Daily digest | All warnings + critical |

Example monitor script:

```bash
#!/bin/bash
ALERTS=$(curl -s http://localhost:8000/api/v1/pilot/alerts)
CRITICAL=$(echo "$ALERTS" | jq '[.[] | select(.severity=="critical")] | length')
if [ "$CRITICAL" -gt 0 ]; then
  echo "$ALERTS" | mail -s "Pi-PM Pilot CRITICAL" ops@example.com
  exit 1
fi
```

---

## Escalation

| Level | Condition | Response time |
|-------|-----------|---------------|
| L1 | Any critical | Same day |
| L2 | 2+ warnings | Next trading day |
| L3 | Info only | Weekly review |
