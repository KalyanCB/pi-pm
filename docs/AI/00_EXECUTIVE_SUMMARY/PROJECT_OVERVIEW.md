# Pi-PM — Project Overview

**Personal Intelligence Portfolio Manager** — deterministic quant pipeline for Indian NSE equities with LLM-assisted **research governance** (ARGS), not LLM ranking.

---

## Mission

Rank a configurable universe (`NIFTY_500` in ops), validate predictive power (IC, deciles, regimes), maintain audit traceability, and support research on exits, factors, regime policy, and investment committees — without letting models touch money logic.

---

## Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI 0.115+, `/api/v1` |
| DB | PostgreSQL 16, SQLAlchemy 2.0, Alembic |
| Data | Yahoo Finance (`yfinance`), benchmark `^NSEI` |
| Tests | pytest (312) |
| Deploy | Docker Compose (`docker/`) |

---

## Current maturity

| Stage | Status |
|-------|--------|
| Core ranking + validation | Production |
| Sprint 7 traceability | Production |
| Sprint 8.1–8.6 analytics + daily batch | Production APIs |
| ARGS + SEE v2 + SQE observability | Production on `feature/see-v2` |
| Portfolio / paper trading | Deferred |
| Ranking calibration v2 | Research only |

---

## Critical product truths

1. **Rankings generate alpha** at bucket level (especially top-20 vs benchmark).
2. **Fine-grained rank order is unreliable** — do not treat rank 3 vs rank 7 as calibrated.
3. **Validation** needs forward-return tail; latest sessions may show `insufficient_data`.
4. **Governance:** five committees + CRO; Phase 2 independence shipped; Phase 3 not started.
5. **QRC:** legacy quant brief default; `ARGS_QRC_USE_SQE=false`.

---

## Documentation map

| Audience | Entry |
|----------|--------|
| AI agent | [AI_AGENT_HANDOVER.md](../12_HANDOVER/AI_AGENT_HANDOVER.md) |
| Developer | [HANDOFF.md](../../HANDOFF.md) |
| PO / platform | [PLATFORM-HANDOFF-2026.md](../../PLATFORM-HANDOFF-2026.md) |
| Full index | [docs/README.md](../../README.md) |

Legacy executive doc: [PROJECT_MASTER.md](../../PROJECT_MASTER.md).
