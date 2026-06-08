# Track F2 — Feature Integration Report

**Date:** 2026-06-05  
**Scope:** Frontend only — auth, dashboard, recommendations, portfolio, committee, copilot  
**Platforms:** Web (`@pipm/web`) + Mobile (`@pipm/mobile`) via shared packages

---

## Summary

The frontend monorepo foundation (Track F) has been wired to live backend APIs. All six feature phases use TanStack Query for server state and Zustand for client state. No mock data is used in production paths.

---

## Phase 1 — Authentication

| Capability | Implementation |
|------------|----------------|
| Login | `POST /auth/login` via `packages/api/src/auth.ts` |
| Logout | `POST /auth/logout` + local session clear |
| Session persistence | `@react-native-async-storage/async-storage` in `packages/hooks/src/storage/sessionStorage.ts` |
| Refresh token | `POST /auth/refresh` on 401 via `refreshAccessToken.ts` + proactive expiry check on bootstrap |
| Portfolio selection | Client-side `activePortfolioId` + `X-Portfolio-Id` header on all API calls |
| Protected routes | `AuthGate` in `packages/hooks/src/auth/AuthGate.tsx` redirects to `/login` |

**Routes:** `apps/web/app/login.tsx`, `apps/mobile/app/login.tsx`  
**UI:** `packages/ui/src/screens/LoginScreen.tsx`  
**Settings:** Portfolio picker + sign out in `SettingsScreen.tsx`

**Env:**
- `EXPO_PUBLIC_API_BASE_URL` — API base (default `http://localhost:8000/api/v1`)
- `EXPO_PUBLIC_AUTH_BYPASS=true` — skip login UI (backend auth bypass still required)

---

## Phase 2 — Dashboard

| Endpoint | Hook |
|----------|------|
| `GET /portfolio/dashboard` | `useDashboardQuery()` |
| `GET /analytics/recommendations/trust` | `useTrustQuery()` |

**Composite:** `useDashboard()`  
**Screen:** `DashboardScreen.tsx` — NAV, Cash %, Alpha, Risk, Trust Score, Pending Exits

---

## Phase 3 — Recommendations

| Endpoint | Usage |
|----------|-------|
| `GET /recommendations/daily` | BUY / WATCH tabs |
| `GET /recommendations/{run_id}?action=EXIT_APPROVED` | EXIT tab |
| `GET /investment-committee/latest` + `/packets` | Committee advisory overlay |
| `GET /stocks` | `stock_id` → `symbol` mapping |

**Hook:** `useRecommendationCards()`  
**Screen:** `RecommendationsScreen.tsx` — tabs, conviction, reason codes, committee overlay

---

## Phase 4 — Portfolio

| Endpoint | Hook |
|----------|------|
| `GET /portfolio/summary` | `usePortfolioScreen()` |
| `GET /portfolio/positions` | `usePortfolioScreen()` |
| `GET /portfolio/performance` | `usePortfolioScreen()` |
| `GET /portfolio/attribution` | `usePortfolioScreen()` (409 gate handled) |

**Screen:** `PortfolioScreen.tsx` — summary, positions, performance, attribution by sector

---

## Phase 5 — Committee

| Endpoint | Usage |
|----------|-------|
| `GET /investment-committee/latest` | Review status (polls while RUNNING) |
| `GET /investment-committee/{id}/packets` | Advisory overlays |
| `GET /investment-committee/{id}/report` | Governance narratives |

**Hook:** `useCommitteeScreen()`  
**Screen:** `CommitteeScreen.tsx` — HIGH_CONCERN filter, all advisories, report

---

## Phase 6 — Copilot

| Endpoint | Hook |
|----------|------|
| `POST /copilot/ask` | `useAskCopilot()` mutation |

**Screen:** `CopilotScreen.tsx` — chat UI, citations (`CitationPanel`), lineage (`LineagePanel`)

---

## Architecture

```
apps/web|mobile
  └── AppProviders (ApiClient + AuthProvider + React Query)
        └── AuthGate
              └── AppShell (except /login)
                    └── Screen → @pipm/hooks → @pipm/api → Backend
```

**New API modules:** `auth.ts`, `stocks.ts`  
**Extended:** `portfolio.ts` (summary, attribution), `client.ts` (`X-Portfolio-Id`)

---

## Demo Walkthrough

1. Start backend: `uvicorn app.main:app --reload` (port 8000)
2. Set `frontend/apps/web/.env`: `EXPO_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`
3. Run web: `cd frontend && pnpm dev:web`
4. **Login** — use registered investor credentials
5. **Dashboard** — verify NAV, trust score, risk, pending exits
6. **Recommendations** — switch BUY / WATCH / EXIT tabs
7. **Portfolio** — review positions and attribution (or reconciliation gate message)
8. **Committee** — review HIGH_CONCERN symbols and report
9. **Copilot** — ask a grounded question, inspect citations and lineage
10. **Settings** — switch portfolio (if multiple), sign out

---

## Screenshots

Capture after running against a seeded backend:

| Screen | Path |
|--------|------|
| Login | `/login` |
| Dashboard | `/` |
| Recommendations | `/recommendations` |
| Portfolio | `/portfolio` |
| Committee | `/committee` |
| Copilot | `/copilot` |
| Settings | `/settings` |

> Screenshots require a running backend with data. Use OS screenshot tools during the demo walkthrough above.

---

## Known Client Workarounds (unchanged from Track B)

- Recommendations return `stock_id`; client joins `GET /stocks` for symbols
- Committee advisory requires client join (daily recs + committee packets)
- `EXIT_APPROVED` fetched via separate run endpoint, not `/daily` filter
- Portfolio attribution returns 409 when reconciliation fails — surfaced in UI

---

## Validation

```bash
cd frontend
pnpm install
pnpm typecheck
pnpm test
pnpm --filter @pipm/web build
```

---

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Investor can login | ✅ |
| View recommendations | ✅ |
| View portfolio | ✅ |
| View committee advisory | ✅ |
| Use copilot | ✅ |
| No mock data | ✅ |
| Web + mobile shared codebase | ✅ |

---

## Known gaps (2026-06-05)

| Gap | Status | Notes |
|-----|--------|-------|
| Exit Approval Queue (`/exits`) | Missing screen | `getExits`, `useConfirmExit`/`useRejectExit` not wired in UI |
| Performance Analytics (`/analytics`) | Missing screen | Only trust metrics wired elsewhere |
| HITL queue modal | Missing | `GET /recommendations/queue` not in client |
| Copilot audit history | Missing | `GET /copilot/audit` not wired |
| Citation deep links | Partial | `resolveCitationRoute` exists; `CitationPanel` onPress missing |
| Portfolio risk API | Missing | `GET /portfolio/risk` not in hooks |
| Pull-to-refresh | Missing | No `RefreshControl` |
| Settings in mobile TabBar | Missing | Desktop sidebar footer only |

See [`docs/audit/FRONTEND_AUDIT_REPORT.md`](../../docs/audit/FRONTEND_AUDIT_REPORT.md) for full matrix.
