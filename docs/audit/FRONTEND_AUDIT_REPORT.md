# Frontend Audit Report

**Audit:** AUDIT-01  
**Date:** 2026-06-05  
**Stack:** React Native + React Native Web monorepo (`frontend/`)  
**Architecture ADR:** ADR-026

---

## Executive Summary

| Classification | Screens | API methods |
|----------------|---------|-------------|
| **Implemented** | 5 | ~18 wired |
| **Partial** | 4 | ~12 wired with gaps |
| **Stub** | 0 | — |
| **Missing** | 2 screens + 1 sub-route | ~10 unwired |

**Overall frontend completion vs SCREEN_SPECIFICATIONS.md:** ~65%

---

## Architecture Verification

| ADR-026 / AC-FE requirement | Status | Evidence |
|-----------------------------|--------|----------|
| RN + RN Web monorepo | **IMPLEMENTED** | `frontend/apps/web`, `apps/mobile`, `packages/*` |
| Shared `packages/ui` | **IMPLEMENTED** | 40+ components |
| `packages/api` typed client | **IMPLEMENTED** | `createApi.ts`, domain modules |
| `packages/hooks` queries | **IMPLEMENTED** | React Query wrappers |
| Backend owns financial math | **IMPLEMENTED** | No client-side conviction/ranking |
| Auth layer | **IMPLEMENTED** | Contradicts stale `AUTHENTICATION_PREPARATION.md` |

---

## Screen Coverage Matrix

| Screen | Route | Web | Mobile | Component | Status |
|--------|-------|-----|--------|-----------|--------|
| Login | `/login` | ✓ | ✓ | `LoginScreen` | **Implemented** |
| Dashboard | `/` | ✓ | ✓ | `DashboardScreen` | **Implemented** (partial vs spec) |
| Recommendations | `/recommendations` | ✓ | ✓ | `RecommendationsScreen` | **Partial** |
| Recommendation Detail | `/recommendations/:symbol` | ✓ | ✓ | `RecommendationDetailScreen` | **Implemented** |
| Portfolio | `/portfolio` | ✓ | ✓ | `PortfolioScreen` | **Partial** |
| Committee | `/committee` | ✓ | ✓ | `CommitteeScreen` | **Partial** |
| Copilot | `/copilot` | ✓ | ✓ | `CopilotScreen` | **Partial** |
| Settings | `/settings` | ✓ | ✓ | `SettingsScreen` | **Partial** |
| Exit Approval Queue | `/exits` | ✗ | ✗ | — | **Missing** |
| Performance Analytics | `/analytics` | ✗ | ✗ | — | **Missing** |
| Committee Detail | `/committee/:symbol` | ✗ | ✗ | — | **Missing** |

Routes defined in `packages/navigation/src/routes.ts` but no app files for `/exits`, `/analytics`, `/committee/:symbol`.

---

## API Integration Status

### Wired and used
| Client method | Hook | Screen |
|---------------|------|--------|
| `auth.login/me` | AuthProvider | Login |
| `portfolio.getDashboard` | useDashboardQuery | Dashboard |
| `portfolio.getSummary/positions/performance/attribution` | usePortfolioScreen | Portfolio, Dashboard |
| `portfolio.getNavHistory` | useNavHistoryQuery | Dashboard, Portfolio |
| `recommendations.getDaily/getStockResult` | useRecommendation* | Rec screens |
| `recommendations.approve/reject` | useApprove/Reject | Detail |
| `committee.getLatest/packets/report` | useCommitteeScreen | Committee, Dashboard |
| `copilot.ask` | useAskCopilot | Copilot, SidePanel |
| `pilot.getHealth/Recommendations/Trust` | usePilot* | Dashboard |
| `analytics.getTrustMetrics` | useTrustQuery | Dashboard, Rec |

### Client-ready but unwired in UI
| Method | Hook exists | Gap |
|--------|-------------|-----|
| `recommendations.getQueue` | ✗ | No HITL queue modal |
| `portfolio.getExits` | ✗ | No Exit screen |
| `portfolio.confirmExit/rejectExit` | ✓ hooks | **Unused** |
| `portfolio.getRisk` | ✗ | Risk only on dashboard |
| `copilot.getAudit` | ✗ | No audit history UI |
| `stocks.get` | ✗ | No per-symbol enrichment |
| `pilot.getCommitteeDashboard` | ✗ | — |
| Analytics summary/conviction/committee | ✗ no client | No Analytics screen |

---

## Auth Integration — IMPLEMENTED

| Capability | File | Status |
|------------|------|--------|
| Login UI | `LoginScreen.tsx` | ✓ |
| Session persistence | `sessionStorage.ts` | ✓ AsyncStorage |
| AuthGate | `AuthGate.tsx` | ✓ redirects to `/login` |
| Token refresh | `refreshAccessToken.ts` | ✓ 401 + proactive |
| X-Portfolio-Id header | `client.ts` | ✓ |
| Dev bypass | `authStore.ts` | ✓ `EXPO_PUBLIC_AUTH_BYPASS` |
| Logout | Settings | ✓ |

---

## Responsive Layout — PARTIAL

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Breakpoints 375/768/1024/1440 | **Partial** | `breakpoints.ts`; tablet unused for layout |
| Desktop sidebar 240px | **Implemented** | `Sidebar.tsx` |
| Mobile bottom tabs (5) | **Implemented** | `TabBar.tsx` — Settings not in tabs |
| Copilot side panel desktop | **Implemented** | `CopilotSidePanel.tsx` 400px |
| Master-detail recommendations | **Implemented** | `MasterDetailLayout.tsx` |
| Max width 1440 | **Implemented** | `InvestorScreenShell.tsx` |
| Pull-to-refresh | **Missing** | No RefreshControl |
| Fixed bottom approval bar mobile | **Missing** | ApprovalActionBar scrolls |
| WCAG 2.1 AA | **Not verified** | No a11y audit run |

---

## UX Spec Gaps (vs `docs/frontend/ui/`)

| Spec item | Status |
|-----------|--------|
| Reconciliation detail modal (FP-04) | Text banner only |
| HIGH_CONCERN filter on recommendations | Display only, no filter |
| Citation deep links (COPILOT_UX) | `resolveCitationRoute` exists; `CitationPanel` no onPress |
| Approval workflow FAB/queue (APPROVAL_WORKFLOW_UX) | Missing |
| Settings theme/strategy prefs | Not implemented |
| Trust dashboard full vision (17) | Trust card only |

---

## Mobile PRD (FR-*) Coverage

| FR group | Wired | Missing |
|----------|-------|---------|
| FR-D (Dashboard) | 6/7 | Recon modal |
| FR-R (Recommendations) | 5/7 | HITL queue, full filter |
| FR-P (Portfolio) | 4/6 | Risk detail, benchmark |
| FR-C (Committee) | 4/6 | Detail sub-route, roster |
| FR-CP (Copilot) | 4/6 | Audit, full citation nav |

---

## Test Coverage

| Tests | Location |
|-------|----------|
| Route definitions | `navigation/__tests__/routes.test.ts` |
| ConvictionBadge, RecommendationCard | `ui/__tests__/` |
| **No** screen E2E | — |
| **No** API mock integration tests | — |

---

## Stale Frontend Docs

| Document | Claim | Reality |
|----------|-------|---------|
| `docs/frontend/AUTHENTICATION_PREPARATION.md` | Not implemented | Full JWT flow |
| `frontend/docs/ARCHITECTURE_REPORT.md` | Placeholder screens | Live API screens |
| `docs/frontend/API_INTEGRATION_PLAN.md` | No auth.ts | auth.ts + pilot.ts exist |

**Accurate:** `frontend/docs/FEATURE_INTEGRATION_REPORT.md` (phases 1–6).

---

*Evidence: `frontend/apps/*/app/`, `frontend/packages/{api,hooks,ui,navigation}/`.*
