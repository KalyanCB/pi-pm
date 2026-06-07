# Test Coverage Audit

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**Test runner:** pytest  
**Result:** **574 collected, 574 passed** in 82.27s  
**Documented claims:** 312 (`README`), 386 (`IMPLEMENTATION_SUMMARY`), 537 (`production-readiness-scorecard`) — all **stale**

---

## Executive Summary

| Dimension | Assessment |
|-----------|------------|
| Requirement coverage (Phase 1 G1–G8) | **Strong** — golden tests + integration APIs |
| Requirement coverage (Phase 2 product) | **Moderate** — unit-heavy, API integration gaps |
| Module coverage (research pipeline) | **~85%** of critical paths |
| Module coverage (portfolio/execution) | **~60%** — service unit tests, no API integration |
| Integration coverage | **Partial** — 12 integration API files |
| E2E coverage | **NOT_STARTED** — no pilot lifecycle E2E |
| Critical-path untested | Batch cron auth, multi-tenant analytics, live execution |

---

## Test Inventory

| Category | Files | Approx. tests |
|----------|-------|---------------|
| Unit | ~120 | ~480 |
| Integration API | 12 | ~60 |
| Integration ARGS | 3 | ~20 |
| Health/smoke | 1 | 1 |
| **Total** | **~136** | **574** |

---

## Coverage by Domain

### Ranking — STRONG
| Tests | Coverage |
|-------|----------|
| `test_golden_ranking.py`, `test_engine.py`, `test_momentum_v1.py`, `test_breakout_v1.py` | Determinism, strategies, factors |
| `test_rankings_api.py` | API integration |
| `test_ranking_service.py` | Service layer |

**Gap:** ranking_v2 research-only — correctly not in production tests.

### Validation — STRONG
| Tests | Coverage |
|-------|----------|
| `test_forward_returns.py`, `test_golden_validation.py`, `test_statistics.py` | Core math |
| `test_validation_api.py`, `test_full_universe_validation_api.py` | API |

**Gap:** Tail `insufficient_data` operational scenarios.

### Universe — ADEQUATE
`test_filter_engine.py`, `test_nifty500_loader.py`, `test_universe_bootstrap_service.py`

### Regime — STRONG
`test_regime_policy_api.py`, engine/metrics/replay unit tests (6 files).

### Recommendation — MODERATE
| Tests | Coverage |
|-------|----------|
| `test_engine.py` (17 tests) | Rules R-ENTRY/EXIT |
| `test_conviction_scorer.py` | AC-CS |
| `test_calculator.py`, `test_trust_metrics.py` | Analytics |

**Gap:** **No `test_recommendations_api.py`** — approve/reject/why-not untested at HTTP layer.

### Portfolio — MODERATE
| Tests | Coverage |
|-------|----------|
| `test_portfolio_service.py` (15) | Core service |
| `test_analytics.py` (17) | Performance, attribution |
| `test_reconciliation.py`, `test_position_sizing.py`, `test_exit_triggers.py` | AC-PE, AC-EX |

**Gap:** **No portfolio API integration tests**; multi-tenant recon untested.

### Committee / ARGS — STRONG
63+ unit tests across ARGS packet, evidence, registry, effectiveness; `test_research_api.py` integration.

### Copilot — MODERATE
| Tests | Coverage |
|-------|----------|
| `test_copilot_service.py` | Refusal, logging |
| `test_intent.py` | 8 refuse patterns |
| `test_citations.py`, `test_lineage.py` | Grounding |

**Gap:** No API integration; no golden Q&A fixture suite (AC-CP-01).

### Auth — ADEQUATE
| Tests | Coverage |
|-------|----------|
| `test_jwt.py`, `test_constants.py` | Token + RBAC matrix |
| `test_auth_api.py` | Login, refresh rotation, 401 |
| `test_tenant_isolation.py` | Cross-portfolio 403 |

**Gap:** No login rate-limit tests; permission enforcement only tested on execution.

### Execution — MODERATE
`test_execution_service.py`, `test_state_machine.py`, zerodha adapter test.

**Gap:** No HTTP integration; live adapter stub untested end-to-end.

### Pilot Ops — MODERATE
`test_paper_pilot_ops.py`, `test_pilot_command_center.py`, `test_pilot_alerting.py`, `test_daily_batch_portfolio_schema.py`

**Gap:** No E2E 90-day pilot simulation; no pilot API integration.

### Daily Batch — WEAK
`test_daily_batch_planner.py` only — **no full pipeline E2E**.

### Frontend — MINIMAL
`frontend/packages/navigation/src/__tests__/routes.test.ts`, UI component tests (ConvictionBadge, RecommendationCard). **No screen integration or E2E tests.**

### Risk Controls — NOT_STARTED
No tests — `AC-RISK-01..06` not implemented.

---

## Critical Business Paths — Test Status

| Path | Unit | Integration | E2E | Verdict |
|------|------|-------------|-----|---------|
| Rank → Validate → Recommend | ✓ | Partial | ✗ | **PARTIAL** |
| Recommend → Approve → Paper fill | ✓ | ✗ | ✗ | **PARTIAL** |
| Exit monitor → Approve → Paper exit | ✓ | ✗ | ✗ | **PARTIAL** |
| NAV snapshot → Reconciliation | ✓ | ✗ | ✗ | **PARTIAL** |
| Daily batch full pipeline | Planner only | ✗ | ✗ | **WEAK** |
| Multi-tenant portfolio isolation | assert_access | 1 test | ✗ | **PARTIAL** |
| Copilot refuse trade/override | ✓ | ✗ | ✗ | **ADEQUATE** |
| Live broker execution | stub test | ✗ | ✗ | **NOT_STARTED** |
| Emergency risk stop | — | — | — | **NOT_STARTED** |

---

## Untested Business-Critical Paths (Priority Order)

1. **Daily batch HTTP → full portfolio phases with pilot flags** — documented cron path has no auth in script
2. **Recommendation approve → execution order → paper fill chain** — no integration test
3. **Reconciliation FAIL → 409 on performance API** — unit only, no API test
4. **Multi-tenant NAV/attribution isolation** — tables lack `portfolio_id`
5. **Pilot alerting on consecutive batch failures** — alerting unit tests only
6. **HIGH_CONCERN soft-block on live entry** — not implemented (AC-HITL-L03)
7. **Approval audit CSV export** — not implemented
8. **Frontend HITL approve/reject against live API** — no E2E

---

## CI / Coverage Metrics

`docs/ops/production-readiness-scorecard.md` claims **73% pytest-cov** — not re-verified in this audit run. Recommend `pytest --cov=app` in CI artifact for ongoing tracking.

---

## Recommendations (audit-only — not implemented)

| Priority | Action |
|----------|--------|
| P0 | Add `test_recommendations_api.py` + `test_portfolio_api.py` |
| P0 | E2E test: batch with `pilot_auto_*` flags through fill + recon |
| P1 | `test_execution_api.py` with paper adapter |
| P1 | `test_pilot_ops_api.py` smoke |
| P2 | Copilot golden Q&A fixture suite |
| P2 | Frontend Detox/Maestro smoke for login → dashboard |

---

*Evidence: `tests/` tree, pytest run 2026-06-05.*
