# ARGS Design

**Status:** Production Phase 1 + committee Phase 2 · **Owner:** `app/args/`

---

## Purpose

**A**utomated **R**esearch **G**overnance **S**ystem — investment review packets, five specialist committees + CRO, deterministic QRC quant brief, LLM narrative under strict evidence rules.

---

## Flow

```mermaid
sequenceDiagram
  participant R as Ranking run
  participant P as Packet builder
  participant C as Committees
  participant API as /research API
  R --> P
  P --> C
  C --> API
```

---

## API

`/api/v1/research/run`, `/latest`, `/{id}`, `/packet`, `/explain`, `/lineage`

---

## Committees

TARC, QRC, FRC, NRCC, RC + CRO synthesis — see [aics-ai-investment-committee-architecture.md](../../aics-ai-investment-committee-architecture.md).

---

## Phase 2 independence (shipped)

| Metric | Before | After |
|--------|--------|-------|
| Effective independence | ~14% | **~79%** |
| Evidence overlap | ~60% | **~0%** |

[committee-independence-phase2-results.md](../../committee-independence-phase2-results.md)

**Phase 3:** not started.

---

## Scripts

`scripts/run_args_top20.py` — always document `ARGS_QRC_USE_SQE` for ops.

Legacy: [args-implementation-plan.md](../../args-implementation-plan.md), [args-gap-analysis.md](../../args-gap-analysis.md).
