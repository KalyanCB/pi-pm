# Pi-PM Document Inventory

**Generated:** 2026-06-04  
**Scope:** `docs/`, `app/`, `tests/`, `migrations/`, `scripts/`, `docker/`, CI  
**Purpose:** Phase 1 handover — every documented artifact with location, purpose, status, owner subsystem.

---

## Legend

| Status | Meaning |
|--------|---------|
| **Current** | Authoritative; align with `feature/see-v2` / migration `20260609_0018` |
| **Legacy** | Historical sprint plan or superseded numbers; cross-check before use |
| **Research** | Analytics output; not production contract |
| **Ops log** | Dated operational record |

| Owner subsystem | Primary code owner |
|-----------------|-------------------|
| Core / Platform | `app/core`, `app/db`, `app/main.py` |
| Market data | `app/providers`, `app/services/market_data*` |
| Universe | `app/universe` |
| Ranking | `app/ranking`, `app/ranking_research` |
| Validation | `app/validation` |
| Traceability | `app/services/platform_traceability`, Sprint 7 models |
| Regime policy | `app/regime_policy` |
| Factor analytics | `app/factor_analytics` |
| Exit research | `app/workspace_exit_research`, exit services |
| Research intelligence | `app/services/research_intelligence*` |
| Daily batch | `app/ops/daily_batch` |
| ARGS / Governance | `app/args` |
| SEE | `app/stock_setup_evidence` |
| Outcome attribution | `app/outcome_attribution` |
| Backtest | `app/backtest` |

---

## docs/ (markdown)

| Location | Purpose | Status | Owner |
|----------|---------|--------|-------|
| [PLATFORM-HANDOFF-2026.md](../../PLATFORM-HANDOFF-2026.md) | Single platform entry point | Current | Core |
| [HANDOFF.md](../../HANDOFF.md) | Sprint 8 gotchas, takeover checklist | Current | Core |
| [README.md](../../README.md) | Doc index | Current | Core |
| [AI_CONTEXT.md](../../AI_CONTEXT.md) | AI onboarding (some counts stale) | Legacy partial | Core |
| [architecture.md](../../architecture.md) | Layers, flows | Current | Core |
| [DATABASE_SCHEMA.md](../../DATABASE_SCHEMA.md) | Tables, ER (head may lag) | Current | Core |
| [API_REFERENCE.md](../../API_REFERENCE.md) | REST catalog | Current | Core |
| [domain-boundaries.md](../../domain-boundaries.md) | Package constraints | Current | Core |
| [PROJECT_MASTER.md](../../PROJECT_MASTER.md) | Executive summary | Current | Core |
| [ROADMAP.md](../../ROADMAP.md) | Backlog | Current | Core |
| [DECISION_LOG.md](../../DECISION_LOG.md) | ADRs | Current | Core |
| [SPRINT_HISTORY.md](../../SPRINT_HISTORY.md) | Sprint chronology | Current | Core |
| [daily-nifty500-batch-runbook.md](../../daily-nifty500-batch-runbook.md) | Daily ops | Current | Daily batch |
| [daily-nifty500-batch-plan.md](../../daily-nifty500-batch-plan.md) | Batch design | Current | Daily batch |
| [args-implementation-plan.md](../../args-implementation-plan.md) | ARGS Phase 1 | Current | ARGS |
| [args-gap-analysis.md](../../args-gap-analysis.md) | PO ARGS design | Current | ARGS |
| [aics-ai-investment-committee-architecture.md](../../aics-ai-investment-committee-architecture.md) | Original committee design | Legacy ref | ARGS |
| [committee-*](../../README.md#args--committees) | Independence Phase 1–2 | Research/Current | ARGS |
| [qrc-*](../../README.md#qrc-sqe--quant-evidence), [sqe-*](../../README.md#qrc-sqe--quant-evidence) | QRC/SQE research | Research | ARGS |
| [see-v2-*](../../README.md#see-v2-stock-setup-evidence) | SEE v2 | Current | SEE |
| [outcome-attribution-report.md](../../outcome-attribution-report.md) | Rank → returns | Research | Outcome attribution |
| [rank-*](../../README.md#ranking--outcome-research), [factor-reliability*](../../factor-reliability-report.md), [calibrated-ranking*](../../calibrated-ranking-research.md) | Ranking research | Research | Ranking |
| [sprint61–sprint83*](../../README.md#sprint-runbooks-8x-and-earlier) | Sprint runbooks | Mixed | Per sprint |
| [dailyruns/04-jun-2026/](../../dailyruns/04-jun-2026/) | Example daily run log | Ops log | Ops |
| [docs/AI/](../README.md) | AI handover tree (this package) | **New** | Handover |

**Dated ARGS exports:** `args-breakout-2026-06-*.md`, `args-momentum-2026-06-*.md`, `args-legacy-*`, `args-sqe-*` — Ops log / Research, ARGS.

---

## app/ (code-as-documentation)

| Location | Purpose | Status | Owner |
|----------|---------|--------|-------|
| `app/main.py` | FastAPI app, exception handlers | Current | Core |
| `app/api/router.py` | Route mounting `/api/v1` | Current | Core |
| `app/api/v1/*.py` | 14 routers | Current | Per domain |
| `app/core/config.py` | Settings (`ARGS_QRC_USE_SQE`, universe defaults) | Current | Core |
| `app/ranking/` | Deterministic strategies (frozen) | Production | Ranking |
| `app/validation/` | Forward returns, IC, regimes | Production | Validation |
| `app/args/` | Packets, committees, LLM plugins | Production | ARGS |
| `app/stock_setup_evidence/` | SEE v2 engine | Production | SEE |
| `app/regime_policy/` | Replay/backtest (research) | Research API | Regime |
| `app/factor_analytics/` | Factor IC persistence | Production API | Factor |
| `app/workspace_exit_research/` | Exit simulators | Production API | Exit |
| `app/outcome_attribution/` | Read-only attribution | Production analytics | Outcome |
| `app/ops/daily_batch/` | NIFTY 500 orchestration | Production | Daily batch |
| `app/models/` | 22 ORM modules | Current | Core |
| `app/schemas/` | 14 Pydantic modules | Current | Core |
| `app/services/` | Orchestration layer | Current | Core |

---

## tests/

| Location | Purpose | Status | Owner |
|----------|---------|--------|-------|
| `tests/test_health.py` | Smoke health | Current | Core |
| `tests/unit/ranking/` | Engine, factors, golden | Current | Ranking |
| `tests/unit/validation/` | Stats, regimes, golden | Current | Validation |
| `tests/unit/args/` | Packets, committees, QRC flag | Current | ARGS |
| `tests/unit/stock_setup_evidence/` | SEE profiles, similarity | Current | SEE |
| `tests/unit/regime_policy/` | Engine, replay, metrics | Current | Regime |
| `tests/unit/factor_analytics/` | IC engine, backfill | Current | Factor |
| `tests/unit/workspace_exit_research/` | Simulators, indices | Current | Exit |
| `tests/unit/outcome_attribution/` | Service, statistics | Current | Outcome |
| `tests/unit/ranking_research/` | Reliability, calibration | Current | Ranking |
| `tests/integration/api/` | HTTP contract tests | Current | Core |
| `tests/integration/args/` | Lineage, research API | Current | ARGS |

**Count:** 312 tests collected (`pytest --collect-only`).

---

## migrations/

| Location | Purpose | Status | Owner |
|----------|---------|--------|-------|
| `migrations/versions/20260530_0001` … `20260609_0018` | 18 Alembic revisions | Current | Core |
| Head `20260609_0018` | SEE v2 metrics columns | Current | SEE |

See [08_DATA_MODEL/DATABASE_SCHEMA.md](../08_DATA_MODEL/DATABASE_SCHEMA.md).

---

## scripts/

| Script | Purpose | Owner |
|--------|---------|-------|
| `run_daily_nifty500_batch.py` | Daily production batch | Daily batch |
| `run_args_top20.py` | ARGS top-20 committees | ARGS |
| `backfill_sprint7_traceability.py` | Traceability backfill | Traceability |
| `init_regime_policy_presets.py` | Regime presets | Regime |
| `backfill_sprint82_factor_analytics.py` | Factor IC backfill | Factor |
| `backfill_sprint83_exit_research.py` | Exit research backfill | Exit |
| `generate_ranking_root_cause_reports.py` | Five ranking reports | Ranking |
| `generate_outcome_attribution_report.py` | Outcome report | Outcome |
| `generate_see_v2_validation_report.py` | SEE validation doc | SEE |
| `qrc_sqe_ab_experiment.py` | QRC SQE A/B | ARGS |
| `analyze_committee_effectiveness.py` | Committee metrics | ARGS |
| Others | Recovery, reingest, PDF guide | Ops / Core |

---

## docker/

| Location | Purpose | Status |
|----------|---------|--------|
| `docker/Dockerfile` | API image | Current |
| `docker/docker-compose.yml` | Postgres + API | Current |
| `docker/docker-compose.dev.yml` | Dev overrides | Current |

---

## CI

| Location | Purpose | Status |
|----------|---------|--------|
| `.github/` | **Not present** in repo | N/A |

CI is local: `pytest`, `alembic upgrade head`, Docker compose per [06_OPERATIONS/ENVIRONMENT_SETUP.md](../06_OPERATIONS/ENVIRONMENT_SETUP.md).

---

## README.md (repo root)

| Location | Purpose | Status |
|----------|---------|--------|
| `/README.md` | Quick start, links to docs | Current (test count may lag) |

---

## Cross-reference

Full AI handover index: [../README.md](../README.md) → [12_HANDOVER/AI_AGENT_HANDOVER.md](../12_HANDOVER/AI_AGENT_HANDOVER.md).
