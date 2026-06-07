# API Audit Report

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**Base prefix:** `/api/v1` (`app/main.py`)  
**OpenAPI:** `/docs` (FastAPI auto-generated)  
**Tests:** 574 passed

---

## Executive Summary

| Classification | Count | % of ~130 routes |
|----------------|-------|------------------|
| **Implemented** | 108 | 83% |
| **Partial** | 14 | 11% |
| **Missing** | 4 | 3% |
| **Broken** | 0 | 0% |
| **Deprecated** | 6 | 5% |

**Critical finding:** `docs/po-discovery/04_API_CATALOG.md` documents ~67 routes with **no auth**. Code reality (`app/api/router.py`): all domain routes require JWT except health and auth login/refresh/register/logout.

---

## Auth Enforcement Matrix

| Router group | Router-level auth | Per-route elevation | Evidence |
|--------------|-------------------|---------------------|----------|
| health | None | — | `router.py:30` |
| auth | None (login public) | `CurrentUser` on `/me`, `/logout-all` | `auth.py` |
| stocks–copilot | `get_current_user` | See per-route below | `router.py:33-125` |
| daily-batch | `get_current_user` + `require_owner` | OWNER/ADMIN only | `router.py:84-88` |
| recommendations approve/reject | Authenticated | `OwnerUser` | `recommendations.py` |
| portfolio mutations | Authenticated | `OwnerUser` + `PortfolioScope` | `portfolio.py` |
| execution | Authenticated | `OwnerUser` + `PortfolioScope` + `Permission` | `execution.py` |

**Dev bypass:** `auth_enabled=false` or `auth_bypass_for_tests=true` injects fixed dev owner (`auth_deps.py:124-135`).

---

## Endpoint Inventory by Domain

### Health — IMPLEMENTED (3/3)

| Method | Path | Auth | Schema | Tests |
|--------|------|------|--------|-------|
| GET | `/health/live` | None | inline | `test_health.py` |
| GET | `/health/ready` | None | inline | same |
| GET | `/health` | None | inline | same |

### Auth — IMPLEMENTED (6/6)

| Method | Path | Auth | Schema | Tests |
|--------|------|------|--------|-------|
| POST | `/auth/login` | Public | `LoginRequest/Response` | `test_auth_api.py` |
| POST | `/auth/refresh` | Public | rotation | `test_refresh_token_rotation` |
| POST | `/auth/logout` | Public | — | integration |
| POST | `/auth/register` | Public | — | integration |
| POST | `/auth/logout-all` | CurrentUser | — | — |
| GET | `/auth/me` | CurrentUser | `UserProfile` | integration |

### Ranking — IMPLEMENTED (4/4)

| Method | Path | Auth | Schema | Tests |
|--------|------|------|--------|-------|
| POST | `/rankings/run` | JWT | `RankingRunRead` | `test_rankings_api.py` |
| GET | `/rankings/latest` | JWT | same | same |
| GET | `/rankings/{run_id}` | JWT | same | same |
| GET | `/rankings/{run_id}/top` | JWT | `RankingTopRead` | same |

### Validation — IMPLEMENTED (8/8)

All routes in `validation.py` — schemas in `app/schemas/validation.py`. Integration: `test_validation_api.py`, `test_full_universe_validation_api.py`.

### Universe / Stocks / Market Data — IMPLEMENTED (6/6)

| Module | Endpoints | Tests |
|--------|-----------|-------|
| `stocks.py` | 4 (incl. bootstrap) | market data integration |
| `market_data.py` | 2 | `test_market_data` patterns |

### Regime Policy — IMPLEMENTED (8/8)

`regime_policy.py` — `test_regime_policy_api.py`.

### Observability — IMPLEMENTED (13/13)

Lineage, score reconstruction, experiments, regime perf — unit tests for traceability.

### Factor / Exit / Research Intelligence Analytics — IMPLEMENTED (20/20)

Integration tests for factor and exit APIs.

### Investment Committee — IMPLEMENTED (7/7)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/investment-committee/review` | OwnerUser | Triggers ARGS |
| GET | `/investment-committee/latest` | JWT | |
| GET | `/investment-committee/{review_id}` | JWT | |
| GET | `.../packets` | JWT | |
| GET | `.../report` | JWT | |
| GET | `.../explain` | JWT | |
| GET | `/committees/members` | JWT | |

No dedicated integration test file.

### Research (deprecated) — DEPRECATED (6/6)

`research.py` mounted with tag `research-deprecated`. Superseded by `/investment-committee/*`.

### Stock Setup Research — IMPLEMENTED (2/2)

`test_stock_setup_research_api.py`.

### Daily Batch — PARTIAL (4/4 exist, ops gap)

| Method | Path | Auth | Gap |
|--------|------|------|-----|
| POST | `/ops/daily-batch/runs` | OWNER/ADMIN | `scripts/run_daily_nifty500_batch.py` POSTs **without** Authorization header |

### Pilot Ops — IMPLEMENTED (10/10, no integration tests)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/pilot/command-center` | Aggregate |
| GET | `/pilot/dashboard/pilot` | Pilot dashboard |
| GET | `/pilot/dashboard/health` | Health |
| GET | `/pilot/dashboard/recommendations` | Rec dashboard |
| GET | `/pilot/dashboard/committee` | Committee |
| GET | `/pilot/dashboard/trust` | Trust |
| GET | `/pilot/dashboard/operational` | Ops |
| GET | `/pilot/alerts` | Alert codes |
| GET | `/pilot/metrics/success` | KPI metrics |
| GET | `/pilot/reports/{report_type}` | Reports |

### Recommendations — IMPLEMENTED (9/9, no integration tests)

| Method | Path | Auth | Schema |
|--------|------|------|--------|
| POST | `/recommendations/run` | OwnerUser | `RecommendationRunRead` |
| GET | `/recommendations/latest` | JWT | same |
| GET | `/recommendations/queue` | JWT | HITL queue |
| GET | `/recommendations/daily` | JWT | daily feed |
| GET | `/recommendations/{run_id}` | JWT | run detail |
| GET | `/recommendations/{run_id}/stocks/{symbol}` | JWT | per-stock |
| GET | `/recommendations/why-not/{symbol}` | JWT | reason codes |
| POST | `/recommendations/{result_id}/approve` | OwnerUser | approval |
| POST | `/recommendations/{result_id}/reject` | OwnerUser | rejection |

### Recommendation Analytics — IMPLEMENTED (6/6)

`/analytics/recommendations/*` — summary, conviction, regime, committee, trust, symbol.

### Portfolio — PARTIAL (22/22 exist, scoping gaps)

| Method | Path | PortfolioScope | Gap |
|--------|------|----------------|-----|
| GET | `/portfolio/summary` | ✓ | — |
| GET | `/portfolio/positions` | ✓ | — |
| GET | `/portfolio/limits` | ✓ | — |
| GET | `/portfolio/allocation` | ✓ | — |
| POST | `/portfolio/config` | ✓ + Owner | — |
| POST | `/portfolio/recompute` | ✓ + Owner | — |
| POST | `/portfolio/trades/entry` | ✓ + Owner | delegates to ExecutionService |
| POST | `/portfolio/trades/exit` | ✓ + Owner | same |
| GET | `/portfolio/performance` | ✗ | **Global** — no tenant filter |
| GET | `/portfolio/risk` | ✗ | Global |
| GET | `/portfolio/attribution` | ✗ | Global; 409 on recon FAIL ✓ |
| GET | `/portfolio/benchmark` | ✗ | Global |
| GET | `/portfolio/nav-history` | ✗ | Global |
| GET | `/portfolio/cash-ledger` | ✗ | Global |
| GET | `/portfolio/reconciliation` | ✗ | Global |
| POST | `/portfolio/reconcile` | Owner only | No PortfolioScope |
| GET | `/portfolio/exits` | ✗ | Global |
| POST | `/portfolio/exits/run` | Owner | — |
| POST | `/portfolio/exits/{id}/confirm` | Owner | — |
| POST | `/portfolio/exits/{id}/reject` | Owner | — |
| POST | `/portfolio/nav-snapshot` | Owner | — |
| GET | `/portfolio/dashboard` | ✗ | Global aggregate |

### Execution — IMPLEMENTED (8/8, paper only)

Full RBAC with `EXECUTION_READ`/`EXECUTION_WRITE` permissions. Zerodha live adapter stub.

### Copilot — IMPLEMENTED (2/2)

| Method | Path | Auth | Tests |
|--------|------|------|-------|
| POST | `/copilot/ask` | JWT | unit only |
| GET | `/copilot/audit` | OwnerUser | unit only |

### Backtest — IMPLEMENTED (2/2)

`test_backtest_api.py`.

---

## Documented but Missing Endpoints

| Documented requirement | Expected endpoint | Status |
|------------------------|-------------------|--------|
| AC-HITL-02 approval CSV export | `GET /recommendations/approvals/export` | **MISSING** |
| AC-RISK-03 emergency stop | `POST /risk/emergency-stop` | **MISSING** |
| Risk pre-trade checks | risk middleware | **MISSING** |
| Live broker status | broker health beyond execution health | **MISSING** |

---

## OpenAPI Exposure

All mounted routers appear in OpenAPI via FastAPI auto-generation. Deprecated `/research/*` tagged `research-deprecated`.

---

## Integration Test Coverage Gaps

| API module | Integration test |
|------------|------------------|
| portfolio | **MISSING** |
| recommendations | **MISSING** |
| execution | **MISSING** |
| pilot_ops | **MISSING** |
| copilot | **MISSING** |
| investment_committee | **MISSING** (covered partially via `test_research_api.py`) |

---

*Evidence: `app/api/router.py`, `app/api/v1/*.py`, `tests/integration/api/`.*
