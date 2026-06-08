# Platform Readiness Scorecard

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**Method:** Independent code + test verification (NOT derived from existing doc scores)  
**Tests:** 574/574 passed

Scale: 0 = absent, 50 = partial/shippable-with-gaps, 100 = production-complete per PRD/ADR

---

## Scores

| Dimension | Score | Status | Key evidence |
|-----------|-------|--------|--------------|
| **Research Platform** (G1–G7) | **88** | IMPLEMENTED | Ranking golden tests, validation API, ARGS, SEE v2, 574 tests |
| **Recommendation Engine** (P1–P2) | **68** | PARTIAL | Full engine + APIs; no API integration tests; lifecycle state machine informal |
| **Portfolio Engine** (P4) | **58** | PARTIAL | Service + recon + sizing; global NAV/cash; no tenant on analytics |
| **Investment Committee** (G6/ADR-023) | **76** | IMPLEMENTED | Real LLM plugins, packet builder, 63+ tests; HIGH_CONCERN live path gap |
| **Copilot** (P7) | **74** | IMPLEMENTED | Refusal + grounding + audit; frontend citation nav gap |
| **Authentication** (ADR-027) | **70** | PARTIAL | JWT + rotation + tenant on core routes; default secret; permissions narrow |
| **Frontend** (ADR-026) | **62** | PARTIAL | 8/10 screens, auth live; missing /exits, /analytics |
| **Paper Trading** (P5/ADR-028) | **68** | PARTIAL | Full lifecycle with flags; cron auth gap; no E2E |
| **Operations / Pilot** (ADR-029) | **72** | IMPLEMENTED | Command center, alerting, reporting; external deps |
| **Security** (incl. risk) | **55** | PARTIAL | Auth OK; AC-RISK not started; multi-tenant analytics gap |
| **Live Execution** (ADR-030/031) | **22** | NOT_STARTED | Paper works; Zerodha stub; no risk gates |
| **Maintainability** | **75** | GOOD | Clean module boundaries, Alembic, monorepo; stale docs hurt onboarding |
| **Documentation accuracy** | **48** | POOR | Multiple stale handoffs; code ahead of RTM/API catalog |

---

## Composite Scores (audit-derived)

| Scope | Score | Calculation |
|-------|-------|-------------|
| **Phase 1 research platform only** | **88** | G1–G7 weighted |
| **Phase 2 investable product** | **58** | Rec + Portfolio + Paper + Frontend + Auth + HITL |
| **Full platform vision** (incl. live + risk) | **61** | All dimensions weighted |
| **90-day paper pilot readiness** | **68** | Paper + Ops + Security (pilot mode) |
| **Production live investing readiness** | **28** | Live + Risk + Security production |

---

## Claimed vs Audit Scores

| Source | Claimed | Audit | Delta |
|--------|---------|-------|-------|
| `PRODUCT_MATURITY_SCORECARD` weighted | ~72 | 61 (full) | −11 |
| `PRODUCT_MATURITY_SCORECARD` recommendation | 25 | 68 | +43 (stale) |
| `PRODUCT_MATURITY_SCORECARD` portfolio | 12 | 58 | +46 (stale) |
| `production-readiness-scorecard` | 85 | 61 (full) / 88 (research only) | Misleading for Phase 2 |
| `PILOT_READINESS_REPORT` unattended | 78 | 68 | −10 |
| `COPILOT_EVALUATION_REPORT` | 78 | 74 | −4 |
| `IMPLEMENTATION_SUMMARY` implied | ~80+ Phase 2 | 58 Phase 2 | Overstated |

---

## Evidence Highlights per Dimension

### Research Platform (88)
- ✓ G1 golden ranking: `test_golden_ranking.py`
- ✓ G2 validation: 8 API endpoints + integration tests
- ✓ G4 lineage: `/observability/lineage/*`
- ✓ G6 ARGS: real plugins in `registry.py:15-21`
- ✓ G7 SEE v2: `stock_setup_research` migration + API
- △ G3 batch: planner tests only, cron auth gap

### Recommendation Engine (68)
- ✓ R-ENTRY/EXIT rules in `engine.py`
- ✓ conv_v1.1.0 scorer with unit tests
- ✓ 9 REST endpoints
- △ No HTTP integration tests
- △ AC-LC-01 no formal state machine module

### Portfolio Engine (58)
- ✓ Reconciliation, sizing, exit monitor
- ✓ 22 API endpoints
- ✗ NAV/cash/recon not portfolio-scoped
- ✗ `paper_trades` no portfolio_id

### Security (55)
- ✓ JWT + refresh rotation tested
- ✓ Tenant isolation on summary/positions
- ✗ AC-RISK entirely missing
- ✗ Default JWT secret
- ✗ Analytics APIs global

---

## Readiness Gates

| Gate | Threshold | Audit result |
|------|-----------|--------------|
| Research staging | ≥80 | **PASS** (88) |
| Paper pilot (conditional) | ≥65 | **PASS** (68) |
| Investor MVP (mobile+web) | ≥70 | **FAIL** (62 frontend, 58 product) |
| Live investing S1 | ≥75 | **FAIL** (28) |
| Multi-tenant production | ≥80 | **FAIL** (55 security) |

---

*Scores are independent of PO maturity scorecard and reflect 2026-06-05 codebase state.*
