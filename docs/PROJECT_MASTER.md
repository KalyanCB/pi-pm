# Pi-PM — Project Master

**Last updated:** 2026-06-01  
**Repository:** `/Users/kalyancb/pi-pm`  
**Active branch:** `feature/sprint8`  
**Migration head:** `20260531_0008`  
**Tests:** 150 passing

---

## Executive Summary

**Pi-PM** ranks Indian NSE equities using deterministic factor models, validates predictive power, maintains full operational traceability, and evaluates regime-aware trading policies in a **research-only** layer before any production deployment.

LLMs are excluded from ranking, sizing, trade approval, and risk override.

**Current phase:** Post-validation regime research (Sprint 8.1). `breakout_v1` shows regime-dependent alpha; testing whether gating improves holdout performance.

---

## Current Implementation Status

| Layer | Status |
|-------|--------|
| Foundation, market data, universes | Complete |
| Ranking (`momentum_v1`, `breakout_v1`) | Complete |
| Backtest + per-run validation | Complete |
| Full-universe validation campaigns | Complete |
| Platform traceability (Sprint 7 / 7.1) | Complete + backfilled |
| Regime policy replay (Sprint 8.1) | Complete — research only |
| Portfolio / paper trading / LLM agents | Stubs only |

---

## Current Metrics

| Metric | Value |
|--------|------:|
| Alembic migrations | 8 |
| Database tables | ~27 |
| API endpoint groups | 9 |
| Automated tests | 150 |
| Traceability: factor contributions | ~1.18M rows |
| Traceability: horizon metrics | ~1,636 rows |

---

## Completed Milestones

| Milestone | Sprint |
|-----------|--------|
| Ranking + validation | 3–4.2 |
| NIFTY 500 + breakout_v1 | 5.1 |
| Full-universe validation | 6.1 |
| Traceability foundation | 7 |
| Traceability operationalization | 7.1 |
| Regime-aware policy research | 8.1 |

---

## Current Sprint: 8.1 (Complete)

**Objective:** Test regime gating (E1–E4) on historical `breakout_v1` validation data.

**Deliverables:**
- `regime_policy_configs`, `regime_policy_decisions`, `regime_backtest_runs`
- `RegimePolicyEngine`, replay framework, backtest API
- Bootstrap CI + `research_findings` JSON
- Preset loader (not in migration)

**Not in scope:** Live ranking changes, paper trading, automatic policy activation.

**Runbook:** `docs/sprint81-regime-aware-trading.md`  
**Results template:** `docs/sprint81-results-template.md`

---

## Recent Sprints (Shipped on `feature/sprint-8.3-exit-research`)

| Sprint | Focus |
|--------|-------|
| 8.2 | Factor predictive power analytics (`/analytics/factors`) |
| 8.3 | Exit research workspace (`/analytics/exit`) |
| 8.5 | Research intelligence / executive reporting |

## Next Sprint (Planned)

| Sprint | Focus |
|--------|-------|
| 8.4 | AI research agent (human approval gates) |

See `docs/ROADMAP.md` and `docs/sprint83-85-implementation-summary.md`.

---

## Known Risks

| Risk | Mitigation |
|------|------------|
| Regime gating reduces sample size | Holdout validation + bootstrap CI |
| O(n²) validation stats at scale | Use `compute_pooled_period_metrics` in policy layer |
| Docker stale code | Rebuild after changes |
| Default universe `PI_PM_CORE` | Pass `NIFTY_500` explicitly |
| Sparse regimes (BEAR_HIGH_VOL n=4) | Min sample rules; gate only |

---

## Quick Reference

| Resource | Path |
|----------|------|
| **Takeover guide** | `docs/HANDOFF.md` |
| AI onboarding | `docs/AI_CONTEXT.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Database | `docs/DATABASE_SCHEMA.md` |
| API | `docs/API_REFERENCE.md` |
| Sprint history | `docs/SPRINT_HISTORY.md` |
| Decisions | `docs/DECISION_LOG.md` |
