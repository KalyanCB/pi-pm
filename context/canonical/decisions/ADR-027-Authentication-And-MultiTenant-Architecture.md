# ADR-027: Authentication and Multi-Tenant Architecture

**Status:** Accepted  
**Date:** 2026-06-05  
**Deciders:** Principal Security Architect, Platform Engineering  
**Supersedes:** N/A — implements [AUTHENTICATION_PREPARATION.md](../design/domain-boundaries.md) backend contract  
**Related:** [ADR-024](./ADR-024-Portfolio-State-Source-Of-Truth.md), [ADR-026](./ADR-026-Frontend-Architecture.md)

---

## Context

Pi-PM operated as a trusted single-user system with no backend authentication. All portfolio, recommendation, committee, and copilot data was globally scoped. The production readiness scorecard (Track A) identified missing authentication as a P0 blocker.

We must evolve to a **secure, multi-user-ready, portfolio-ownership-aware** platform without modifying investment logic (ranking, validation, recommendation engine, conviction scoring, portfolio calculations, committee logic, copilot grounding).

---

## Ownership Review (Pre-Implementation)

| Domain | Prior State | Ownership Gap |
|--------|-------------|---------------|
| **Portfolio** | Singleton `portfolio_configs` + global positions | No `user_id` or `portfolio_id`; any client saw all capital data |
| **Recommendations** | Platform-wide runs; HITL `actor_id` client-supplied | Spoofable audit trail; no auth gate on approve/reject |
| **Committee (ARGS)** | Global research runs | No access control on expensive LLM `/review` trigger |
| **Copilot** | Global audit log; retriever unscoped | All users' queries visible; Q&A reads full platform state |

---

## Decision

Implement **additive authentication and RBAC** with **portfolio-scoped multi-tenancy** as the first isolation boundary.

### 1. Identity Model

| Entity | Table | Purpose |
|--------|-------|---------|
| `User` | `users` | Email/password identity |
| `Role` | `roles` | Catalog: admin, owner, viewer |
| `PermissionRecord` | `permissions` | Fine-grained permission catalog |
| `RolePermission` | `role_permissions` | Role ↔ permission mapping |
| `UserPreference` | `user_preferences` | Timezone, locale, settings JSON |
| `Portfolio` | `portfolios` | Logical portfolio container |
| `UserPortfolioMembership` | `user_portfolio_memberships` | User ↔ portfolio with scoped role |
| `RefreshToken` | `refresh_tokens` | Hashed refresh tokens with rotation |

### 2. Roles

| Role | Capabilities |
|------|--------------|
| **ADMIN** | Full platform access; sees all copilot audit logs |
| **OWNER** | Read/write portfolio, approve recommendations, run committee, copilot ask + audit |
| **VIEWER** | Read portfolio, recommendations, committee, analytics; copilot ask only |

Permissions enforced via static `ROLE_PERMISSIONS` matrix in `app/auth/constants.py`.

### 3. JWT Authentication

- **Access token:** HS256, 15-minute expiry, claims: `sub`, `email`, `roles`, `portfolio_id`
- **Refresh token:** Opaque UUID, SHA-256 hashed in DB, 7-day expiry
- **Rotation:** Refresh revokes prior token and issues new pair
- **Logout:** Revokes refresh token; `/logout-all` revokes all sessions
- **Session invalidation:** `revoked_at` timestamp on refresh token rows

Endpoints: `POST /auth/login`, `/auth/register`, `/auth/refresh`, `/auth/logout`, `/auth/logout-all`, `GET /auth/me`

### 4. RBAC Enforcement

- Router-level `Depends(get_current_user)` on all non-health routes
- Mutation routes require `OwnerUser` (owner or admin)
- Ops routes (`/ops/daily-batch`) require owner/admin
- Permission matrix checked via `AuthContext.has_permission()`

### 5. Multi-Tenant Portfolio Isolation

- `portfolio_id` added to `portfolio_configs` and `portfolio_positions` (nullable, backfilled to default portfolio)
- `PortfolioScope` dependency resolves user's authorized portfolio (via JWT claim or `X-Portfolio-Id` header)
- `PortfolioService` accepts optional `portfolio_id` — **filter-only**, no calculation changes
- User A cannot access User B portfolio via `assert_portfolio_access()`

### 6. Copilot Ownership (Additive)

- `user_id` added to `copilot_query_logs` for audit scoping
- `get_audit_logs(user_id=...)` filters by user; admins see all
- **Retriever and grounding logic unchanged**

### 7. Recommendation HITL

- `actor_id` bound from authenticated `owner.user_id` — client-supplied value ignored

---

## Invariants

1. Ranking, validation, recommendation engine, conviction scoring, portfolio **calculation** formulas unchanged
2. Committee LLM workflow and copilot retriever **grounding logic** unchanged
3. Auth is additive: `AUTH_BYPASS_FOR_TESTS=true` preserves existing test suite behavior
4. Health endpoints remain public
5. All investment mutations require authenticated OWNER or ADMIN role

---

## Consequences

### Positive

- Perimeter security for all APIs
- Portfolio tenant isolation foundation
- Non-spoofable HITL audit trail
- JWT refresh rotation and session revocation
- Frontend auth contract (`/auth/*`) ready for implementation

### Negative / Deferred

- Recommendations and committee data remain platform-scoped (not per-portfolio) — acceptable for MVP multi-user
- Copilot retriever still reads global platform state — scoped audit only
- OAuth/SSO not in scope (future Track)
- Row-level security policies in PostgreSQL not yet applied

---

## Migration

`20260610_0025_auth_foundation.py` — creates auth tables, adds `portfolio_id` to portfolio entities, adds `user_id` to copilot logs, seeds default portfolio for legacy data.
