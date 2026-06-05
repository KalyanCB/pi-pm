# PO Backlog — Epics, Features, Stories

**Version:** Phase 2.1 (PO sign-off 2026-06-04)  
**Date:** 2026-06-05  
**Priority:** PO implementation order **P1–P7** (below); legacy P0 ops track unchanged

---

## PO implementation priority (P1–P7)

| Priority | Scope | Epics / PRDs |
|----------|--------|----------------|
| **P1** | Recommendation domain — tables, APIs, lifecycle | E-REC, E-LC, [03](./03_RECOMMENDATION_DATA_MODEL.md), [04](./04_RECOMMENDATION_LIFECYCLE.md) |
| **P2** | Deterministic recommendation generation + conviction engine | E-REC, E-CONV, [01](./01_RECOMMENDATION_ENGINE_PRD.md), [02](./02_CONVICTION_SCORING_PRD.md), [16_WHY_NOT](./16_WHY_NOT_RECOMMENDED_FRAMEWORK.md) |
| **P3** | Outcome tracking, performance analytics, trust metrics | E-OUT (new), [16_RECOMMENDATION_PERFORMANCE](./16_RECOMMENDATION_PERFORMANCE_PRD.md), [17_TRUST_DASHBOARD](./17_TRUST_DASHBOARD_VISION.md) |
| **P4** | Portfolio engine — sizing, allocation, cash | E-PORT, [05](./05_PORTFOLIO_ENGINE_PRD.md) |
| **P5** | Paper trading — simulation, reconciliation, attribution | E-PAPER, [06](./06_PAPER_TRADING_PRD.md) |
| **P6** | Mobile — portfolio, recommendations, queue, research | E-MOB, [09](./09_MOBILE_APP_PRD.md) |
| **P7** | AI Copilot — grounded retrieval, explainability, audit | E-COP, [10](./10_AI_COPILOT_PRD.md) |

**Gate:** [PO_SIGNOFF_2026_06_04.md](./PO_SIGNOFF_2026_06_04.md), [ADR-021](../architecture/ADR-021-Recommendation-Platform-Architecture.md).

---

## Epic index

| Epic ID | Title | Priority | Milestone |
|---------|-------|----------|-----------|
| E-OPS | Operations & data quality | P0 | Pre-M1 |
| E-REC | Recommendation Engine | P0 | M1 |
| E-CONV | Conviction scoring | P0 | M1 |
| E-LC | Recommendation lifecycle | P0 | M1 |
| E-PORT | Portfolio engine | P1 | M2 |
| E-PAPER | Paper trading | P1 | M2 |
| E-EXIT | Exit decision framework | P1 | M2 |
| E-ARGS | AI Investment Committee evolution | P1–P2 | M2–M3 |
| E-HITL | Human-in-the-loop execution | P2 | M3 |
| E-AUTH | Auth & security | P2 | M3 |
| E-MOB | Mobile app | P3 | M4 |
| E-COP | AI Copilot | P3 | M4 |
| E-CI | CI & quality gates | P0 | Pre-M1 |
| E-OUT | Recommendation outcomes & performance | P3 | M1 schema / M2 populate |
| E-WNR | Why-not-recommended | P2 | M1 |

---

## E-OUT — Recommendation outcomes (P3)

| Feature | Story | Priority |
|---------|-------|----------|
| F-OUT-1 Schema | `recommendation_outcomes` per [03](./03_RECOMMENDATION_DATA_MODEL.md) §3.4 | P1 (table) / P3 (populate) |
| F-OUT-2 Closure | On exit fill set WIN/LOSS/BREAKEVEN | P3 |
| F-OUT-3 Performance APIs | Summary, conviction, regime, committee effectiveness | P3 |
| F-OUT-4 Trust dashboard | Panels per [17](./17_TRUST_DASHBOARD_VISION.md) | P3+ |

---

## E-WNR — Why not recommended (P2)

| Feature | Story | Priority |
|---------|-------|----------|
| F-WNR-1 Codes | Emit canonical reason codes on every non-BUY | P2 |
| F-WNR-2 API | `GET .../why-not/{symbol}` | P2 |
| F-WNR-3 Copilot | Grounded HFCL-style answers | P7 |

---

## E-OPS — Operations & data quality (P0)

| Feature | Story | AC |
|---------|-------|-----|
| F-OPS-1 Validation tail | Ingest forward bars through T+60 | No `insufficient_data` on T-5 sessions |
| F-OPS-2 Daily batch | Automate post-close NIFTY_500 | 5 green sessions |
| F-OPS-3 Seed data | Clean dummy NIFTY tickers | Ingest 100% real symbols |
| F-OPS-4 Branch | Merge `feature/see-v2` → `main` | Alembic head aligned |

*Source: [po-discovery 13](../po-discovery/13_ROADMAP_RECOMMENDATION.md) P0.1–P0.7*

---

## E-REC — Recommendation Engine (P0, M1)

| Feature | Story | Priority |
|---------|-------|----------|
| F-REC-1 Data model | As PO I want `recommendation_runs` / `results` spec signed off | P0 |
| F-REC-2 Engine rules | As owner I receive BUY/WATCH/HOLD/EXIT/REJECT per top pool + ACTIVE | P0 |
| F-REC-3 Batch phase | As ops I want RE after validation in daily batch | P0 |
| F-REC-4 APIs | As client I GET latest recommendations and queue | P0 |
| F-REC-5 ARGS packet | As ARGS I receive `recommendation` block in packet | P0 |
| F-REC-6 Rank guard | As PO rank 1–5 cannot get EXCEPTIONAL until v2 promoted | P0 |

**Stories detail — F-REC-2:**

- **S-REC-2.1:** Given completed validation, top-20 names get `action` + `conviction_score`.
- **S-REC-2.2:** Given `insufficient_data`, max action WATCH.
- **S-REC-2.3:** Given ACTIVE position, emit HOLD or EXIT_APPROVED per [07](./07_EXIT_DECISION_FRAMEWORK.md).

---

## E-CONV — Conviction scoring (P0, M1)

| Feature | Story | Priority |
|---------|-------|----------|
| F-CONV-1 Formula v1.1 | Five-factor weights; **no committee** — [02](./02_CONVICTION_SCORING_PRD.md) | P2 |
| F-CONV-2 Golden tests | Quant verifies fixture scores | P0 |
| F-CONV-3 Explain API | Mobile/desktop shows `conviction_components` | P1 |

---

## E-LC — Lifecycle (P0, M1)

| Feature | Story | Priority |
|---------|-------|----------|
| F-LC-1 States | Implement CANDIDATE→APPROVED→ACTIVE→EXIT→CLOSED | P0 |
| F-LC-2 Approvals | `recommendation_approvals` audit | P0 |
| F-LC-3 Expiry | Stale CANDIDATE auto-close | P1 |

---

## E-PORT — Portfolio engine (P1, M2)

| Feature | Story | Priority |
|---------|-------|----------|
| F-PORT-1 Summary API | NAV, cash, slots | P1 |
| F-PORT-2 Regime slots | Defensive caps enforced on BUY | P1 |
| F-PORT-3 Allocation | Conviction-weighted notional | P1 |
| F-PORT-4 ARGS context | `portfolio_context` from live book | P1 |

---

## E-PAPER — Paper trading (P1, M2)

| Feature | Story | Priority |
|---------|-------|----------|
| F-PAPER-1 CRUD API | Idempotent paper trades | P1 |
| F-PAPER-2 Reconcile | Positions = fills | P1 |
| F-PAPER-3 Attribution | Performance by strategy/conviction | P2 |

*Gaps: [11_PORTFOLIO](../po-discovery/11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md)*

---

## E-EXIT — Exit framework (P1, M2)

| Feature | Story | Priority |
|---------|-------|----------|
| F-EXIT-1 PO policy | Sign default exit policy from research API | P1 |
| F-EXIT-2 Monitor | Daily job for ACTIVE positions | P1 |
| F-EXIT-3 Human confirm | EXIT_APPROVED queue | P1 |

---

## E-ARGS — Committee evolution (P1–P2)

| Feature | Story | Priority |
|---------|-------|----------|
| F-ARGS-1 Post-RE run | Research only after recommendation_run_id | P1 |
| F-ARGS-2 Advisory enum | APPROVE/WATCH/REJECT/EXIT_APPROVED UI field | P2 |
| F-ARGS-3 SQE decision | PO A/B `ARGS_QRC_USE_SQE` | P0 |
| F-ARGS-4 Phase 3 | Independence ≥85% design | P2 |

---

## E-HITL — Execution (P2, M3)

| Feature | Story | Priority |
|---------|-------|----------|
| F-HITL-1 Queue | Unified approval queue | P2 |
| F-HITL-2 Broker contract | Adapter interface + mock | P2 |
| F-HITL-3 Defer limits | Max 3 exit defers | P2 |

---

## E-AUTH — Security (P2, M3)

| Feature | Story | Priority |
|---------|-------|----------|
| F-AUTH-1 JWT | Owner login for mobile | P2 |
| F-AUTH-2 API scope | Read vs approve roles | P2 |

---

## E-MOB — Mobile (P3, M4)

| Feature | Story | Priority |
|---------|-------|----------|
| F-MOB-1 Shell | 5 screens + nav | P3 |
| F-MOB-2 Queue screen | Approve from phone | P3 |
| F-MOB-3 DTOs | Slim recommendation cards | P3 |

*Gaps: [12_MOBILE](../po-discovery/12_MOBILE_READINESS_ASSESSMENT.md)*

---

## E-COP — Copilot (P3, M4)

| Feature | Story | Priority |
|---------|-------|----------|
| F-COP-1 Ask API | Grounded Q&A with citations | P3 |
| F-COP-2 Audit log | Query retention | P3 |

---

## E-CI — Quality (P0)

| Feature | Story | Priority |
|---------|-------|----------|
| F-CI-1 Workflow | pytest + alembic on PR | P0 |
| F-CI-2 Batch E2E | One integration daily batch test | P1 |

---

## M1 top 3 epics (for executive summary)

1. **E-REC + E-LC (P1)** — recommendation domain, lifecycle, APIs.
2. **E-REC + E-CONV (P2)** — deterministic actions + five-factor conviction (no committee).
3. **E-WNR (P2)** — why-not-recommended codes and explain APIs.

*(E-OPS is parallel prerequisite but is operations, not product feature delta.)*

---

## References

- [12_PRODUCT_ROADMAP_2026_2027.md](./12_PRODUCT_ROADMAP_2026_2027.md)
- [PO_SIGNOFF_2026_06_04.md](./PO_SIGNOFF_2026_06_04.md)
- [po-discovery 13_ROADMAP_RECOMMENDATION.md](../po-discovery/13_ROADMAP_RECOMMENDATION.md)
