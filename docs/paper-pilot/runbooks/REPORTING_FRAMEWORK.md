# Pilot Reporting Framework

---

## Report types

| Type | Period | API | Script |
|------|--------|-----|--------|
| Daily | T | `GET /pilot/reports/daily` | `generate_pilot_reports.py daily` |
| Weekly | T-6 → T | `GET /pilot/reports/weekly` | `generate_pilot_reports.py weekly` |
| Monthly | T-29 → T | `GET /pilot/reports/monthly` | `generate_pilot_reports.py monthly` |
| Final | Pilot start → end | `GET /pilot/reports/final` | `generate_pilot_reports.py final` |

---

## Report sections

### Daily

- Batch summary (status, phases, duration)
- Recommendations (runs, strategies)
- Approvals (count, approved/rejected)
- Paper trades (buys/sells)
- NAV snapshot
- Reconciliation status
- Active alerts

### Weekly / Monthly

- Batch completion stats
- NAV cumulative return and alpha
- Outcome wins/losses
- Paper trade volume
- Alerts

### Final (Day 90)

All monthly sections plus:

- `success_metrics` block
- Full pilot retrospective inputs for PO

---

## Output locations

| Format | Path |
|--------|------|
| Markdown reports | `docs/paper-pilot/reports/*.md` |
| Command center JSON | `docs/paper-pilot/reports/COMMAND_CENTER_*.json` |
| Legacy dashboards | `docs/paper-pilot/dashboards/` (Track G script) |

---

## Cadence

| Report | When | Owner |
|--------|------|-------|
| Daily | Post-batch, same day | Automated cron |
| Weekly | Friday close | Ops review |
| Monthly | Last trading day of month | PO + Ops |
| Final | Day 90 | PO sign-off |

---

## Generate all reports

```bash
python scripts/generate_pilot_reports.py all --as-of-date 2026-06-05
```
