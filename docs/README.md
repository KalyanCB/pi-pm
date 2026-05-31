# Pi-PM Documentation Index

**For any developer, AI, or LLM taking over this project — start with [`HANDOFF.md`](./HANDOFF.md).**

---

## Essential (read in order)

| # | Document | Purpose |
|---|----------|---------|
| 1 | [**HANDOFF.md**](./HANDOFF.md) | Current state, setup, gotchas, takeover checklist |
| 2 | [AI_CONTEXT.md](./AI_CONTEXT.md) | AI assistant onboarding — pipeline, defaults, anti-patterns |
| 3 | [ARCHITECTURE.md](./ARCHITECTURE.md) | System design, diagrams, data flows |
| 4 | [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | Tables, migrations, indexes |
| 5 | [API_REFERENCE.md](./API_REFERENCE.md) | All REST endpoints |
| 6 | [domain-boundaries.md](./domain-boundaries.md) | What each package may/may not do |

---

## Project management

| Document | Purpose |
|----------|---------|
| [PROJECT_MASTER.md](./PROJECT_MASTER.md) | Executive summary and status |
| [SPRINT_HISTORY.md](./SPRINT_HISTORY.md) | Completed sprints chronology |
| [ROADMAP.md](./ROADMAP.md) | Planned work (8.2+) |
| [DECISION_LOG.md](./DECISION_LOG.md) | Architecture decision records (ADRs) |

---

## Sprint runbooks

| Sprint | Document |
|--------|----------|
| 6.1 | [sprint61-full-universe-validation-report.md](./sprint61-full-universe-validation-report.md) |
| 7 | [sprint7-platform-traceability.md](./sprint7-platform-traceability.md) |
| 7.1 | [sprint71-traceability-operationalization.md](./sprint71-traceability-operationalization.md) |
| 8.1 | [sprint81-regime-aware-trading.md](./sprint81-regime-aware-trading.md) |
| 8.1 results | [sprint81-results-template.md](./sprint81-results-template.md) *(fill after backtest)* |

---

## Historical / reference

| Document | Notes |
|----------|-------|
| [architecture.md](./architecture.md) | Legacy stub → see ARCHITECTURE.md |
| [sprint3-code-review-package.md](./sprint3-code-review-package.md) | Sprint 3 review artifact (historical) |
| [sprint4-implementation-plan.md](./sprint4-implementation-plan.md) | Sprint 4 plan |
| [sprint42-implementation-plan.md](./sprint42-implementation-plan.md) | Sprint 4.2 plan |
| [sprint51-nifty500-report.md](./sprint51-nifty500-report.md) | NIFTY 500 rollout report |

---

## Quick commands

```bash
cd /Users/kalyancb/pi-pm
git checkout feature/sprint8
alembic upgrade head
pytest tests/ -q
python scripts/init_regime_policy_presets.py
```

**Repo:** `https://github.com/KalyanCB/pi-pm.git`  
**Branch:** `feature/sprint8` | **Migration head:** `20260531_0008` | **Tests:** 150
