# Current Priorities

Synthesized from [ROADMAP.md](../../ROADMAP.md) and [PLATFORM-HANDOFF-2026.md](../../PLATFORM-HANDOFF-2026.md) as of 2026-06-04.

---

## P0 — Immediate

| Priority | Item | Owner |
|----------|------|-------|
| P0 | Merge / stabilize `feature/see-v2` | Eng |
| P0 | Schedule daily batch post-close (`assume_session_done`) | Ops |
| P0 | PO decision: ranking v2 promotion criteria | PO |
| P0 | PO decision: `ARGS_QRC_USE_SQE` promotion criteria | PO |
| P0 | Ingest validation tail through forward window | Ops |
| P0 | Remove bad NIFTY_500 seed symbols (e.g. dummy tickers) | Eng |

---

## P1 — Next engineering

| Priority | Item | Notes |
|----------|------|-------|
| P1 | Complete exit research backfill at NIFTY_500 scale | Gate for portfolio work |
| P1 | Committee Phase 3 design | After Phase 2 sign-off |
| P1 | AI research agent (Sprint 8.4 plan) | Hypothesis → experiment; human gates |
| P1 | Add CI (`pytest` + migration check) | Gap documented in TEST_GAPS |

---

## P2 — Deferred

| Item | Blocker |
|------|---------|
| Portfolio construction | Exit framework + ranking calibration PO |
| Paper trading wiring | Services stubbed |
| Live broker | Out of scope |
| Ranking factor changes | Research gate |

---

## Research track (non-blocking)

- Calibrated ranking backtest analysis  
- Further QRC/SQE live evals with `ARGS_QRC_USE_SQE=true` per run  
- Regime-conditioned strategy selection (research only)  

---

## Success criteria (near term)

| Metric | Target |
|--------|--------|
| Daily batch green for NIFTY_500 | 5 consecutive sessions |
| Validation tail | No `insufficient_data` on T-5 sessions |
| Committee Phase 2 | Maintain ≥40% effective independence |
| Documentation | AI package complete ([COMPLETENESS_REPORT](../12_HANDOVER/DOCUMENTATION_COMPLETENESS_REPORT.md)) |

Legacy roadmap: [ROADMAP.md](../../ROADMAP.md).
