# Pi-PM — Roadmap

**Last updated:** 2026-06-07  
**Takeover:** `docs/HANDOFF.md`

---

## Current Gate

**Exit research (Sprint 8.3) backfill on NIFTY_500** should complete with visible phase progress and persisted metrics before portfolio construction or live policy integration.

Fill exit research conclusions after holdout review. Portfolio construction remains deferred until optimal exit framework is identified.

---

## Completed (Do Not Re-Implement)

| Sprint | Deliverable |
|--------|-------------|
| 6.1 | Full-universe validation |
| 7 | Traceability tables + observability API |
| 7.1 | Backfill + ensure on reuse paths |
| 8.1 | Regime policy replay + backtest API |
| 8.2 | Factor IC analytics (`/analytics/factors`) |
| 8.3 | Exit research workspace (`/analytics/exit`) |
| 8.5 | Research intelligence / executive reporting (`/analytics/research-intelligence`) |
| 8.6 | Daily batch orchestration (`/ops/daily-batch`) + ingest `since_date` / empty-incremental fix |

---

## Prioritized Backlog

### P0 — Immediate

| Item | Description |
|------|-------------|
| Merge `feature/sprint-8.6-daily-ingestion` | After review |
| Schedule daily batch post-close | cron + `assume_session_done` |
| Remove `DUMMYVEDL*.NS` from NIFTY_500 seed | Avoid false ingest failures |

### P1 — Sprint 8.4 (Planned)

| Item | Description |
|------|-------------|
| AI research agent | Hypothesis → experiment → report (reads exit/factor/regime metrics) |
| Human approval checkpoints | No autonomous production changes |

### P2 — Portfolio / Paper Trading (Deferred)

| Item | Description |
|------|-------------|
| Portfolio construction research | After exit framework selected |
| Paper trading wiring | Tables exist; services stubbed |

### Deferred

| Item | Reason |
|------|--------|
| Live broker | Future |
| New ranking factors | Research gate |
| Regime-specific factor weights (original 8.5 scope) | Superseded by research intelligence reporting |
| LLM ranking/sizing | Never |

---

## Sprint Plan (Updated)

### Sprint 8.2 — Factor Predictive Power ✅

- Per-factor Spearman IC across horizons and regimes
- APIs under `/api/v1/analytics/factors`
- **Runbook:** `docs/sprint82-factor-ic-analytics.md`

### Sprint 8.3 — Exit Research Workspace ✅

- Isolated `workspace_exit_research` (read-only upstream)
- Five policy families + alpha decay curves
- Phased backfill with batch persistence
- **Design:** `docs/sprint83-exit-research-design.md`
- **Ops:** `docs/sprint83-backfill-performance.md`

### Sprint 8.5 — Research Intelligence ✅

- Executive / committee reporting from validation + factor outputs
- **Summary:** `docs/sprint83-85-implementation-summary.md`

### Sprint 8.4 — AI Research Agent

- Read validation + factor + regime + exit metrics
- Generate hypotheses and experiment proposals
- Human approval before any writes

---

## Technical Debt

| Item | Priority |
|------|----------|
| Full-universe campaign O(n²) aggregation | P1 |
| Async campaign + progress API (Sprint 6.2) | P1 |
| Bulk upsert for exit metric persistence (optional) | P2 |
| Postman collection for observability + analytics | P2 |
| CI/CD (GitHub Actions) | P2 |

---

## Related Documentation

- `docs/HANDOFF.md`
- `docs/SPRINT_HISTORY.md`
- `docs/sprint83-85-implementation-summary.md`
