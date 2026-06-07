# ADR-029: Paper Trading Pilot Command Center

**Status:** Accepted  
**Date:** 2026-06-05  
**Related:** [ADR-028](./ADR-028-Paper-Trading-Readiness.md), [ADR-024](./ADR-024-Portfolio-State-Source-Of-Truth.md)

---

## Context

The 90-day paper trading pilot (ADR-028) requires **operational visibility** without changing investment logic. Operators need a single command center to answer: *Is the pilot healthy today?*

---

## Decision

### 1. Read-only command center API

Prefix: `/api/v1/pilot/`

| Endpoint | Dashboard |
|----------|-----------|
| `GET /command-center` | Overview + alert summary |
| `GET /dashboard/pilot` | Pilot dashboard |
| `GET /dashboard/health` | Portfolio health |
| `GET /dashboard/recommendations` | Recommendation performance |
| `GET /dashboard/committee` | Committee effectiveness |
| `GET /dashboard/trust` | Trust metrics |
| `GET /dashboard/operational` | Batch ops history |
| `GET /alerts` | Active alerts |
| `GET /metrics/success` | Success KPIs |
| `GET /reports/{daily\|weekly\|monthly\|final}` | Structured reports |

Implementation: `PilotCommandCenterService` aggregates existing read-only services.

### 2. No investment logic changes

Command center:
- **Reads** from DB and existing analytics services
- **Does not** call ranking, validation, recommendation generation, conviction, committee plugins, or paper trade execution

### 3. Alerting framework

`app/ops/pilot/alerting.py` evaluates:

| Code | Severity |
|------|----------|
| `batch_failed` | critical |
| `reconciliation_fail` | critical |
| `portfolio_cash_negative` | critical |
| `batch_stale` | warning |
| `nav_missing` | warning |
| `recommendation_zero` | warning |
| `approval_backlog` | info |

Alerts are returned in API responses. External notification (Slack/email) is ops-configured outside the app.

### 4. Reporting framework

`app/ops/pilot/reporting.py` + `scripts/generate_pilot_reports.py`:

- Daily / weekly / monthly / final reports
- Markdown output to `docs/paper-pilot/reports/`

### 5. Success metrics

| Metric | Target (90-day) |
|--------|-----------------|
| `batch_completion_rate` | ≥ 0.95 |
| `reconciliation_pass_rate` | ≥ 0.98 |
| `nav_coverage_days` | ≥ trading days × 0.95 |
| `win_rate` | Documented (not gated) |

---

## Consequences

- Pilot operators have API-first visibility
- Dashboards compose existing analytics — no duplicate business logic
- Alerting is in-app evaluation; delivery channel is external
- Committee/trust dashboards remain observation-only per AC-RP-09
