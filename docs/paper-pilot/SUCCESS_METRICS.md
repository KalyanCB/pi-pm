# Pilot Success Metrics

**API:** `GET /api/v1/pilot/metrics/success?from_date=&to_date=`  
**Computation:** `app/ops/pilot/reporting.py::compute_success_metrics`

---

## Primary KPIs (90-day pilot)

| Metric | Formula | Target | Gate |
|--------|---------|--------|------|
| Batch completion rate | completed_batches / total_batches | ≥ 95% | **Yes** |
| Reconciliation pass rate | PASS_recons / total_recons | ≥ 98% | **Yes** |
| NAV coverage | nav_snapshots / trading_days | ≥ 95% | **Yes** |
| Win rate | wins / closed_outcomes | Document | No |
| Cumulative alpha | sum(nav.alpha_pct) | Document | No |

---

## Secondary KPIs (observation)

| Metric | Source | Purpose |
|--------|--------|---------|
| Trust calibration | `/pilot/dashboard/trust` | Conviction band predictiveness |
| Committee advisory value | `/pilot/dashboard/committee` | ARGS observation |
| Exit performance | Recommendation dashboard | Exit timing quality |
| Approval throughput | Daily report | HITL efficiency (if enabled) |
| Churn rate | Trust stability | Recommendation stability |

---

## Dashboard mapping

| KPI | Dashboard |
|-----|-----------|
| Daily recommendations | `/pilot/dashboard/recommendations` |
| Daily approvals | Daily report `sections.approvals` |
| Paper trades | `/pilot/dashboard/pilot` → `today_activity` |
| Portfolio performance | `/pilot/dashboard/health` + NAV trend |
| Alpha vs benchmark | `/pilot/dashboard/pilot` → `nav_trend_30d` |
| Exit performance | `/pilot/dashboard/recommendations` → `exit_performance` |
| Committee value | `/pilot/dashboard/committee` |
| Trust trend | `/pilot/dashboard/trust` → `trend_weekly` |

---

## Go / No-Go (Day 90)

| Criterion | Required |
|-----------|----------|
| Batch completion ≥ 95% | Yes |
| Zero unresolved recon FAIL days in last 14 | Yes |
| NAV coverage ≥ 95% | Yes |
| PO review of trust + committee dashboards | Yes |
| Positive cumulative alpha | No (document only) |

---

## Status evaluation

```bash
curl -s "http://localhost:8000/api/v1/pilot/metrics/success" | jq .
curl -s "http://localhost:8000/api/v1/pilot/command-center" | jq '.success_metrics'
```
