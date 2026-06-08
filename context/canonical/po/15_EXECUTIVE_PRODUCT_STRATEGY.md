# Executive Product Strategy — Pi-PM Phase 2

**Audience:** Board, founders, incoming PO  
**Date:** 2026-06-05  
**Status:** Product definition (not committed engineering schedule)

---

## Strategic positioning

Pi-PM evolves from a **deterministic research platform** (rank + validate + ARGS governance) into an **AI-Governed Swing Trading Operating System** for Indian equities:

| Dimension | Choice |
|-----------|--------|
| Market | NSE, NIFTY 500 universe (personal / owner use first) |
| Horizon | 15–30 trading day swing |
| Return target | ~10% per position (aspirational; not guaranteed) |
| Philosophy | Quality over quantity — selective top pool, not daily churn |
| Cash | Explicitly allowed; regime may reduce deployed slots |
| Automation boundary | Machines recommend; **human approves** entries and exits |

**Evidence today:** Core ranking/validation maturity **~88/85**; investable consumer layer **~38/100** ([PRODUCT_MATURITY_SCORECARD.md](../po-discovery/PRODUCT_MATURITY_SCORECARD.md)).

---

## What we will not do (product guardrails)

1. **LLM ranking or conviction** — violates PRD G8 and ADR-001 ([GOVERNANCE_DESIGN.md](../AI/03_DESIGN/GOVERNANCE_DESIGN.md)).
2. **Auto-execution without human confirm** — broker integration is advisory + approval queue only ([11_HUMAN_IN_LOOP_EXECUTION_PRD.md](../product/11_HUMAN_IN_LOOP_EXECUTION_PRD.md)).
3. **Market rank #1 as “best buy”** until calibration PO gate clears — rank-order inversion documented ([ranking-calibration-root-cause.md](../ranking-calibration-root-cause.md), [po-discovery 10](../po-discovery/10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md)).
4. **Treat ARGS `supportive` as BUY** — research labels only (`CommitteeResearchLabel` in `app/workspace_args/constants.py`).

---

## Phase 2 value thesis

| Layer | Investor value | Build priority |
|-------|----------------|----------------|
| **Recommendation Engine** | Explicit BUY / WATCH / HOLD / EXIT_APPROVED / REJECT with audit trail | **M1** — closes gap in [10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md](../po-discovery/10_RECOMMENDATION_ENGINE_GAP_ANALYSIS.md) |
| **Conviction scoring** | Single deterministic 0–100 for UI and sorting within top pool | **M1** |
| **Portfolio + paper** | Position-aware book, cash, regime slots | **M2** — [11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md](../po-discovery/11_PORTFOLIO_ENGINE_GAP_ANALYSIS.md) |
| **Exit framework** | Live monitoring from exit research simulators | **M2** — reuses `app/workspace_exit_research/` |
| **ARGS evolution** | Committee **advisory** alignment to recommendation actions (not override) | **M2–M3** |
| **Mobile + copilot** | Consumer UX with grounded Q&A | **M4** — [12_MOBILE_READINESS](../po-discovery/12_MOBILE_READINESS_ASSESSMENT.md) 8/100 |

---

## Competitive differentiation

1. **Deterministic core** — reproducible rankings and forward-return validation (312 tests, frozen math).
2. **Evidence-governed AI** — five committees + CRO with ~79% effective independence (Phase 2 ARGS).
3. **Honest alpha narrative** — top-20 bucket alpha with partial verdict; no false precision on rank order ([outcome-attribution-report.md](../outcome-attribution-report.md)).
4. **Separation of duties** — Recommendation (deterministic) → ARGS (research) → Human (capital).

---

## Investment ask (product, not $)

| Milestone | Outcome | Risk if skipped |
|-----------|---------|-----------------|
| **M1** (Q3 2026) | Recommendation + conviction + lifecycle spec implemented | Stakeholders confuse rankings with trades |
| **M2** (Q4 2026) | Paper portfolio + exit monitoring | ARGS `portfolio_context` stays synthetic |
| **M3** (Q1 2027) | HITL execution + ARGS advisory mapping | No path to real capital deployment |
| **M4** (Q2 2027) | Mobile MVP + copilot | Platform remains CLI/API-only |

Detail: [12_PRODUCT_ROADMAP_2026_2027.md](../product/12_PRODUCT_ROADMAP_2026_2027.md).

---

## Near-term PO decisions (P0)

1. Ranking v2 / calibration promotion criteria ([po-discovery 13](../po-discovery/13_ROADMAP_RECOMMENDATION.md) P0.3).
2. `ARGS_QRC_USE_SQE` default remains `false` until A/B sign-off (`app/core/config.py:79`).
3. Validation tail ingest through T+60 (P0.1).
4. Conviction v1.1 weights (five factors, **no committee**) — signed [PO_SIGNOFF_2026_06_04.md](../po/PO_SIGNOFF_2026_06_04.md).
5. Maximum concurrent swing positions and cash floor ([05_PORTFOLIO_ENGINE_PRD.md](../product/05_PORTFOLIO_ENGINE_PRD.md)).

---

## Success metrics (12 months)

| Metric | Target | Baseline |
|--------|--------|----------|
| Recommendation coverage | 100% of top-20 per strategy/day with deterministic action | None |
| Conviction explainability | 100% recommendations show factor breakdown | N/A |
| Paper book reconciliation | Positions = sum(fills) daily | Schema only |
| Human approval latency | < 24h owner SLA for BUY/EXIT_APPROVED | N/A |
| Mobile readiness score | ≥ 60/100 backend | 8/100 |
| Trust dashboard (future) | Six panels live per [17](../product/17_TRUST_DASHBOARD_VISION.md) | N/A |
| Rank monotonicity (PO-defined) | Pass OOS gate before “high conviction” band uses raw rank | Fail ([calibration research](../docs/calibrated-ranking-research.md)) |

---

## Trust dashboard (future)

Post-M2 analytics surface per [17_TRUST_DASHBOARD_VISION.md](../product/17_TRUST_DASHBOARD_VISION.md): recommendation win rate, conviction accuracy, exit effectiveness, strategy/regime/committee effectiveness (measure-only).

---

## References

- [PO_SIGNOFF_2026_06_04.md](../po/PO_SIGNOFF_2026_06_04.md)
- [15_EXECUTIVE_SUMMARY.md](../po-discovery/15_EXECUTIVE_SUMMARY.md)
- [context/canonical/phase1/PRD.md](../phase1/PRD.md)
- [PLATFORM-HANDOFF-2026.md](../../AGENTS.md)
