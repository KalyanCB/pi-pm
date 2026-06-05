# Track E Security Review — Authentication & Multi-Tenant Foundation

**Date:** 2026-06-05  
**Reviewer:** Principal Security Architect  
**ADR:** [ADR-027](../architecture/ADR-027-Authentication-And-MultiTenant-Architecture.md)

---

## Summary

Track E delivers JWT authentication, RBAC (ADMIN/OWNER/VIEWER), portfolio ownership mapping, and tenant isolation at the API boundary. Investment logic remains unchanged.

**Verdict:** Approved for staging deployment with documented deferred items.

---

## Controls Implemented

| Control | Status | Notes |
|---------|--------|-------|
| JWT access tokens (15 min) | ✅ | HS256, claims include roles + portfolio_id |
| Refresh token rotation | ✅ | Old token revoked on refresh |
| Session invalidation | ✅ | Logout + logout-all |
| Password hashing | ✅ | bcrypt |
| RBAC on all non-health routes | ✅ | Router-level `get_current_user` |
| Owner-only mutations | ✅ | Portfolio POST, HITL, committee run |
| Portfolio tenant isolation | ✅ | `X-Portfolio-Id` + membership check |
| Copilot audit scoping | ✅ | Per-user filter; admin sees all |
| HITL actor binding | ✅ | `actor_id` from JWT, not client |
| Auth bypass for tests | ✅ | `AUTH_BYPASS_FOR_TESTS=true` |

---

## Threat Mitigation

| Threat | Mitigation |
|--------|------------|
| Unauthenticated API access | 401 on missing/invalid Bearer token |
| Privilege escalation | Server-side role checks; viewer cannot POST |
| Cross-tenant portfolio access | `assert_portfolio_access()` on scope resolution |
| Refresh token theft | Rotation + revocation; hashed at rest |
| Audit trail spoofing | `actor_id` bound to authenticated user UUID |
| Session fixation | New refresh token on each refresh |

---

## Residual Risks (Deferred)

| Risk | Severity | Recommendation |
|------|----------|----------------|
| HS256 symmetric key | Medium | Migrate to RS256 for multi-service deployments |
| Default JWT secret in config | High | Require `JWT_SECRET_KEY` in production |
| Copilot retriever reads global data | Medium | Scope retriever by portfolio in future track |
| Recommendations/committee platform-scoped | Low | Acceptable for single-org multi-user MVP |
| No rate limiting on `/auth/login` | Medium | Add reverse-proxy or middleware throttling |
| No OAuth/SSO | Low | Future track per frontend auth prep doc |

---

## Production Checklist

- [ ] Set `JWT_SECRET_KEY` to 32+ byte random value
- [ ] Set `AUTH_ENABLED=true`
- [ ] Set `AUTH_BYPASS_FOR_TESTS=false`
- [ ] Run migration `20260610_0025`
- [ ] Create admin user via register + DB superuser flag
- [ ] Verify tenant isolation tests pass in CI

---

## Protected API Surface

All routes under `/api/v1/*` except:

- `GET /health`, `/health/live`, `/health/ready`
- `POST /auth/login`, `/auth/register`, `/auth/refresh`

Mutations require OWNER or ADMIN role.
