# Security Audit Report

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**ADR:** ADR-027 (Authentication & Multi-Tenant)  
**PRD:** `20_RISK_CONTROL_PRD.md` (risk — separate from auth)

---

## Executive Summary

| Area | Status |
|------|--------|
| Authentication (JWT) | **IMPLEMENTED** with production hardening gaps |
| Authorization (RBAC) | **PARTIALLY_IMPLEMENTED** — fine-grained permissions on execution only |
| Portfolio isolation | **PARTIALLY_IMPLEMENTED** — scoped routes OK; analytics global |
| JWT handling | **IMPLEMENTED** — HS256, 15min access, refresh rotation |
| Refresh rotation | **IMPLEMENTED** — tested |
| Audit trails | **IMPLEMENTED** — execution, copilot, approvals, refresh tokens |
| Risk controls (AC-RISK) | **NOT_STARTED** |

**Production readiness (auth):** ~72/100 — functional but checklist items remain.

---

## Authentication

### JWT access tokens
- **Algorithm:** HS256 (`app/auth/jwt.py`)
- **Expiry:** 15 minutes (`jwt_access_token_minutes` in config)
- **Claims:** `sub`, `email`, `roles`, `portfolio_id`, `type=access`
- **Test:** `tests/unit/auth/test_jwt.py`

### Refresh tokens
- Stored hashed SHA-256 in `refresh_tokens` table
- **Rotation:** old token revoked on refresh; reuse → 401
- **Test:** `test_refresh_token_rotation` in `test_auth_api.py`

### Registration / login
- `POST /auth/register`, `POST /auth/login` — public
- `GET /auth/me` — authenticated profile with portfolios

### Production risks

| Risk | Severity | Evidence |
|------|----------|----------|
| Default JWT secret | **P0** | `app/core/config.py:83` — `"change-me-in-production-use-openssl-rand"` |
| HS256 symmetric key | P2 | ADR-027 allows; RS256 deferred |
| No login rate limiting | P1 | `docs/ops/security-review-track-e.md` |
| InsecureKeyLengthWarning in tests | P3 | 23-byte test key in pytest warnings |
| AUTH_BYPASS in tests | P3 | `conftest.py` autouse — must be false in prod |

---

## Authorization (RBAC)

### Roles (`app/auth/constants.py`)
| Role | Key permissions |
|------|-----------------|
| ADMIN | All permissions |
| OWNER | Execution write, recommendation approve, portfolio mutate |
| VIEWER | Read-only |

### Permission enforcement

| Route group | Enforcement mechanism |
|-------------|----------------------|
| Daily batch | `require_owner` (OWNER/ADMIN) |
| Recommendations approve/reject | `OwnerUser` |
| Portfolio mutations | `OwnerUser` + `PortfolioScope` |
| Execution | `OwnerUser` + `PortfolioScope` + `require_permission(EXECUTION_*)` |
| All other routes | `get_current_user` only — **no fine-grained Permission check** |

**Gap:** 14 permissions defined; only execution routes use `require_permission`. Recommendations/portfolio rely on role enum only.

**Test:** `test_viewer_lacks_execution_write_permission` — execution only.

---

## Portfolio / Tenant Isolation

### Implemented
- `Portfolio`, `UserPortfolioMembership` models (`app/models/auth.py`)
- `get_portfolio_scope()` resolves `X-Portfolio-Id` header or JWT default (`auth_deps.py:95-118`)
- `auth_service.assert_portfolio_access()` — 403 on cross-portfolio
- Scoped: `portfolio_configs`, `portfolio_positions`, `execution_orders`

### Gaps

| Component | Gap | Severity |
|-----------|-----|----------|
| `portfolio_nav_history` | No `portfolio_id`; unique on `as_of_date` | P1 |
| `portfolio_cash_ledger` | Global | P1 |
| `portfolio_reconciliation_reports` | Global | P1 |
| `paper_trades` | No `portfolio_id` | P1 |
| Portfolio performance/risk/attribution APIs | No `PortfolioScope` | P1 |
| Daily batch / pilot ops | Global queries | P2 (single-pilot OK) |
| Copilot retriever | No portfolio filter | P2 |
| Recommendation pipeline | Global (by design for research) | Acceptable |

**Test:** `tests/integration/api/test_tenant_isolation.py` — portfolio summary 403 cross-tenant.

---

## Audit Trails

| Domain | Storage | Fields | Writable by |
|--------|---------|--------|-------------|
| Execution | `execution_orders`, `execution_events`, `execution_audit` | status transitions, actor | ExecutionService |
| HITL approvals | `recommendation_approvals` | `actor_id` from JWT | API layer |
| Copilot | `copilot_query_logs` | question, intent, citations, refused | CopilotService (append-only) |
| Auth sessions | `refresh_tokens` | hash, rotation chain | AuthService |
| ARGS LLM | `llm_execution_records` | model, tokens | ARGS workflow |

**Gap:** AC-HITL-02 CSV export of approval audit — **not implemented**.

**Test:** `test_submit_order_persists_audit_and_events`

---

## G8 / Governance Boundaries (Security-relevant)

| Boundary | Enforced | Evidence |
|----------|----------|----------|
| LLM cannot rank | Yes | Ranking module isolated |
| LLM cannot set conviction | Yes | No LLM in `conviction_scorer.py`; AC-CS-05 |
| LLM cannot approve trades | Yes | OwnerUser on approve; Copilot read-only |
| Committee cannot mutate action | Yes | R-ARGS-01..04 in engine |
| Copilot cannot write state | Yes | No mutation imports in copilot module |

---

## Risk Controls (AC-RISK) — NOT_STARTED

| ID | Requirement | Status |
|----|-------------|--------|
| AC-RISK-01 | No live BUY over deployable capital | **NOT_STARTED** |
| AC-RISK-02 | Daily loss breach blocks entries | **NOT_STARTED** |
| AC-RISK-03 | Emergency stop 1 API call | **NOT_STARTED** |
| AC-RISK-04 | Manual override audit row | **NOT_STARTED** |
| AC-RISK-05 | SELL under ENTRIES_BLOCKED | **NOT_STARTED** |
| AC-RISK-06 | Risk does not modify conviction | N/A — no risk module |

---

## Security Test Coverage

| Test file | Coverage |
|-----------|----------|
| `test_jwt.py` | Token create/validate |
| `test_constants.py` | RBAC matrix |
| `test_auth_api.py` | Login, refresh rotation, 401, register |
| `test_tenant_isolation.py` | Cross-portfolio 403 |
| `test_execution_service.py` | Viewer permission denial |
| `test_intent.py` / `test_copilot_service.py` | Prompt injection refusal |

**Missing:** rate limiting, permission matrix on all routes, portfolio-scoped analytics tests, penetration test results.

---

## Recommendations (audit-only)

| Priority | Item |
|----------|------|
| P0 | Enforce strong `JWT_SECRET_KEY` in deployment checklist |
| P0 | Add auth to `run_daily_nifty500_batch.py` or document Python-only cron |
| P1 | Add `portfolio_id` to NAV/cash/recon/paper_trades tables + migration |
| P1 | Extend `require_permission` to recommendation approve, portfolio mutate |
| P1 | Implement AC-RISK emergency stop before live S1 |
| P2 | Login rate limiting |
| P2 | Scope copilot retriever by portfolio |

---

*Evidence: `app/auth/`, `app/api/auth_deps.py`, `app/services/auth_service.py`, security review doc.*
