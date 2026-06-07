# Pi-PM Documentation Index

**For any developer, AI engineer, or Product Owner — start with [`PLATFORM-HANDOFF-2026.md`](./PLATFORM-HANDOFF-2026.md).**

Legacy onboarding: [`HANDOFF.md`](./HANDOFF.md) · AI context: [`AI_CONTEXT.md`](./AI_CONTEXT.md)

**Branch:** `feature/see-v2` · **Migration head:** `20260610_0026` · **Tests:** 574 passed

---

## Implementation audit (June 2026)

| Document | Purpose |
|----------|---------|
| [**audit/Executive_Summary.md**](./audit/Executive_Summary.md) | AUDIT-01 — claimed vs actual completion, risks, next tracks |
| [audit/REQUIREMENTS_TRACEABILITY_MATRIX.md](./audit/REQUIREMENTS_TRACEABILITY_MATRIX.md) | Per-requirement implementation status |
| [audit/API_AUDIT_REPORT.md](./audit/API_AUDIT_REPORT.md) | ~130 endpoints, auth, gaps |

---

## Primary handoff (June 2026)

| Document | One-line description |
|----------|---------------------|
| [**PLATFORM-HANDOFF-2026.md**](./PLATFORM-HANDOFF-2026.md) | Single entry point: system map, prod vs experimental, env, scripts, PO decisions, AI quickstart |
| [HANDOFF.md](./HANDOFF.md) | Sprint 8.x gotchas and takeover checklist (links to platform handoff) |
| [AI_CONTEXT.md](./AI_CONTEXT.md) | AI assistant onboarding — pipeline, defaults, anti-patterns |
| [README.md](./README.md) | This index |

---

## Architecture & reference

| Document | One-line description |
|----------|---------------------|
| [architecture.md](./architecture.md) | System design, layers, data flows |
| [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | Tables, migrations, indexes |
| [API_REFERENCE.md](./API_REFERENCE.md) | All REST endpoints |
| [domain-boundaries.md](./domain-boundaries.md) | What each package may/may not do |
| [PROJECT_MASTER.md](./PROJECT_MASTER.md) | Executive summary and status |
| [DECISION_LOG.md](./DECISION_LOG.md) | Architecture decision records (ADRs) |
| [ROADMAP.md](./ROADMAP.md) | Planned work |
| [SPRINT_HISTORY.md](./SPRINT_HISTORY.md) | Completed sprints chronology |

---

## Daily operations

| Document | One-line description |
|----------|---------------------|
| [daily-nifty500-batch-runbook.md](./daily-nifty500-batch-runbook.md) | Run daily batch: ingest, rankings, validation, gaps, ^NSEI, tail |
| [daily-nifty500-batch-plan.md](./daily-nifty500-batch-plan.md) | Daily batch design (API-first orchestration) |
| [dailyruns/04-jun-2026/](./dailyruns/04-jun-2026/) | Example operational run log (2026-06-04): prerequisites through best bets |

**Daily run folder pattern:** `docs/dailyruns/<DD-mon-YYYY>/` — numbered steps `00`–`09` plus ARGS exports.

---

## ARGS & committees

| Document | One-line description |
|----------|---------------------|
| [args-implementation-plan.md](./args-implementation-plan.md) | ARGS Phase 1 API, schema, code map, test count |
| [args-gap-analysis.md](./args-gap-analysis.md) | PO-facing ARGS design, naming (AICS→ARGS), principles |
| [aics-ai-investment-committee-architecture.md](./aics-ai-investment-committee-architecture.md) | Original committee architecture (source design) |
| [tarc-architecture-design.md](./tarc-architecture-design.md) | TARC committee design |
| [committee-effectiveness-report.md](./committee-effectiveness-report.md) | Phase 1 diagnosis: ~14% effective independence |
| [committee-independence-design.md](./committee-independence-design.md) | Phase 2 independence design |
| [committee-independence-phase2-results.md](./committee-independence-phase2-results.md) | Phase 2 results: ~79% independence, before/after metrics |
| [committee-overlap-analysis.md](./committee-overlap-analysis.md) | Committee overlap deep dive |
| [consensus-analysis.md](./consensus-analysis.md) | Cross-committee consensus patterns |
| [args-packet-evidence-audit.md](./args-packet-evidence-audit.md) | Packet evidence coverage audit |
| [args-value-validation-report.md](./args-value-validation-report.md) | ARGS value proposition validation |

**Dated ARGS exports (historical):** `args-breakout-2026-06-0*.md`, `args-momentum-2026-06-0*.md`, `args-legacy-*`, `args-sqe-*`

---

## QRC, SQE & quant evidence

| Document | One-line description |
|----------|---------------------|
| [qrc-root-cause-analysis.md](./qrc-root-cause-analysis.md) | Why QRC collapsed to 0.56 (uniform packet quant evidence) |
| [qrc-evidence-model-redesign.md](./qrc-evidence-model-redesign.md) | QRC evidence model redesign proposal |
| [qrc-information-compression-analysis.md](./qrc-information-compression-analysis.md) | Token/payload analysis of QRC inputs |
| [stock-quality-evidence-design.md](./stock-quality-evidence-design.md) | SQE sections A–F schema design |
| [sqe-phase2-implementation-report.md](./sqe-phase2-implementation-report.md) | SQE on packets (observability only) |
| [qrc-sqe-ab-test-report.md](./qrc-sqe-ab-test-report.md) | A/B: `ARGS_QRC_USE_SQE` false vs true |
| [qrc-sqe-live-openai-evaluation.md](./qrc-sqe-live-openai-evaluation.md) | Live OpenAI evaluation of SQE QRC path |
| [quant-metrics-forensic-analysis.md](./quant-metrics-forensic-analysis.md) | Forensic analysis of quant metrics in packets |
| [tarc-qrc-upgrade-validation.md](./tarc-qrc-upgrade-validation.md) | TARC/QRC upgrade validation notes |

---

## SEE v2 (stock setup evidence)

| Document | One-line description |
|----------|---------------------|
| [see-v2-momentum-support.md](./see-v2-momentum-support.md) | Strategy-aware SEE profiles (breakout vs momentum factor space) |
| [see-v2-validation-report.md](./see-v2-validation-report.md) | Generated top-20 SEE scores per strategy (migration 20260609_0018) |

---

## Ranking & outcome research

| Document | One-line description |
|----------|---------------------|
| [outcome-attribution-report.md](./outcome-attribution-report.md) | Rank buckets vs forward returns — verdict: partial / non-monotonic |
| [ranking-calibration-root-cause.md](./ranking-calibration-root-cause.md) | Why top-20 works but rank ordering fails (score compression) |
| [rank-reliability-report.md](./rank-reliability-report.md) | Spearman rank vs alpha by horizon |
| [factor-reliability-report.md](./factor-reliability-report.md) | Factor-level predictive power |
| [regime-rank-reliability-report.md](./regime-rank-reliability-report.md) | Rank reliability by regime |
| [score-compression-analysis.md](./score-compression-analysis.md) | Composite score clustering analysis |
| [calibrated-ranking-research.md](./calibrated-ranking-research.md) | Isotonic calibration research design |
| [calibrated-ranking-backtest.md](./calibrated-ranking-backtest.md) | Calibration backtest methodology |

**Regenerate five ranking reports:** `python scripts/generate_ranking_root_cause_reports.py`

---

## Sprint runbooks (8.x and earlier)

| Sprint | Document | One-line description |
|--------|----------|---------------------|
| 6.1 | [sprint61-full-universe-validation-report.md](./sprint61-full-universe-validation-report.md) | Full-universe validation campaigns |
| 7 | [sprint7-platform-traceability.md](./sprint7-platform-traceability.md) | Traceability tables and observability API |
| 7.1 | [sprint71-traceability-operationalization.md](./sprint71-traceability-operationalization.md) | Backfill scripts and verification SQL |
| 8.1 | [sprint81-regime-aware-trading.md](./sprint81-regime-aware-trading.md) | Regime policy engine and backtest |
| 8.1 results | [sprint81-results-template.md](./sprint81-results-template.md) | Template — fill after backtest |
| 8.2 | [sprint82-factor-ic-analytics.md](./sprint82-factor-ic-analytics.md) | Factor IC analytics design |
| 8.2 | [sprint82-implementation-summary.md](./sprint82-implementation-summary.md) | Sprint 8.2 PR package |
| 8.2 | [sprint82-backfill-validation-report.md](./sprint82-backfill-validation-report.md) | Factor backfill validation |
| 8.2 | [sprint82-factor-ic-results-template.md](./sprint82-factor-ic-results-template.md) | Factor IC results template |
| 8.3 | [sprint83-exit-research-design.md](./sprint83-exit-research-design.md) | Exit research workspace design |
| 8.3 | [sprint83-backfill-performance.md](./sprint83-backfill-performance.md) | Exit backfill phases and monitoring |
| 8.3/8.5 | [sprint83-85-implementation-summary.md](./sprint83-85-implementation-summary.md) | Exit research + research intelligence shipped |
| 5.1 | [sprint51-nifty500-report.md](./sprint51-nifty500-report.md) | NIFTY 500 rollout report |

---

## Historical / reference

| Document | Notes |
|----------|-------|
| [sprint4-implementation-plan.md](./sprint4-implementation-plan.md) | Sprint 4 plan |
| [sprint42-implementation-plan.md](./sprint42-implementation-plan.md) | Sprint 4.2 validation plan |

---

## Quick commands

```bash
cd /Users/kalyancb/pi-pm
git checkout feature/see-v2
alembic upgrade head
pytest tests/ -q
python scripts/run_daily_nifty500_batch.py --dry-run
ARGS_QRC_USE_SQE=false python scripts/run_args_top20.py --as-of-date 2026-06-04
```

**Repo:** `https://github.com/KalyanCB/pi-pm.git`
