# SQE (Stock Quality Evidence) Design

**Status:** Production observability on packets · **QRC path:** experimental, default off

---

## Purpose

Structured sections A–F on investment review packets (`stock_quality_evidence`) for committee context and QRC experiments — **does not change ranking or committee defaults** when flag is off.

---

## Phase 2 (shipped)

- SQE attached to packets in `run_args_top20` / packet builder
- QRC can consume `qrc_sqe_brief` only when **`ARGS_QRC_USE_SQE=true`**
- **Production default: `ARGS_QRC_USE_SQE=false`** (`app/core/config.py`)

---

## Docs

| Doc | Link |
|-----|------|
| Schema design | [stock-quality-evidence-design.md](../../stock-quality-evidence-design.md) |
| Implementation | [sqe-phase2-implementation-report.md](../../sqe-phase2-implementation-report.md) |
| A/B test | [qrc-sqe-ab-test-report.md](../../qrc-sqe-ab-test-report.md) |
| Live eval | [qrc-sqe-live-openai-evaluation.md](../../qrc-sqe-live-openai-evaluation.md) |

---

## PO decision

Keep legacy `quant_research_brief` until promotion criteria met ([PLATFORM-HANDOFF-2026.md](../../PLATFORM-HANDOFF-2026.md) §9.3).
