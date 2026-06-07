# Pi-PM Frontend — Architecture Report

**Date:** 2026-06-05  
**Tracks:** F (foundation) + F2 (feature integration)  
**ADR:** [ADR-026](../../docs/architecture/ADR-026-Frontend-Architecture.md)

**Live integration detail:** [`FEATURE_INTEGRATION_REPORT.md`](./FEATURE_INTEGRATION_REPORT.md)  
**Audit:** [`docs/audit/FRONTEND_AUDIT_REPORT.md`](../../docs/audit/FRONTEND_AUDIT_REPORT.md)

---

## 1. Summary

The frontend is a **React Native + React Native Web monorepo** with **live backend API integration** across auth, dashboard, recommendations, portfolio, committee, and copilot. Eight screens are wired on both web and mobile; two spec screens (`/exits`, `/analytics`) are not yet implemented.

---

## 2. Repository Structure

```
frontend/
├── apps/
│   ├── web/          @pipm/web   — Expo Web
│   └── mobile/       @pipm/mobile — Expo native
├── packages/
│   ├── types/        @pipm/types
│   ├── theme/        @pipm/theme
│   ├── api/          @pipm/api    — auth, portfolio, recommendations, pilot, …
│   ├── hooks/        @pipm/hooks  — AuthProvider, TanStack Query hooks
│   ├── navigation/   @pipm/navigation
│   └── ui/           @pipm/ui     — screens + components
├── metro.config.base.js
├── package.json
└── turbo.json
```

---

## 3. Technology Stack

| Layer | Package | Status |
|-------|---------|--------|
| Types | `@pipm/types` | ✅ API + component prop types |
| Theme | `@pipm/theme` | ✅ Dark terminal palette, breakpoints |
| API | `@pipm/api` | ✅ Typed clients incl. auth, pilot |
| Hooks | `@pipm/hooks` | ✅ Auth, queries, mutations, stores |
| Navigation | `@pipm/navigation` | ✅ Sidebar, TabBar, AppShell, master-detail |
| UI | `@pipm/ui` | ✅ Screens + dashboard/portfolio molecules |
| Web app | `@pipm/web` | ✅ 8 routes + login |
| Mobile app | `@pipm/mobile` | ✅ Mirrored routes |

---

## 4. State Management

| Concern | Implementation |
|---------|----------------|
| Server state | TanStack Query v5 — all feature hooks **enabled** |
| Auth | `AuthProvider` + `AuthGate` + `sessionStorage` |
| UI filters | `useUiStore` |
| Copilot session | `useCopilotStore` |
| API access | `AppProviders` + `useApi()` with 401 refresh |

---

## 5. Routes (implemented)

| Route | Screen | API integration |
|-------|--------|-----------------|
| `/login` | LoginScreen | `POST /auth/login`, `GET /auth/me` |
| `/` | DashboardScreen | dashboard, trust, pilot health, nav-history |
| `/recommendations` | RecommendationsScreen | daily, committee overlay, stocks list |
| `/recommendations/:symbol` | RecommendationDetailScreen | stock result, approve/reject |
| `/portfolio` | PortfolioScreen | summary, positions, performance, attribution |
| `/committee` | CommitteeScreen | latest, packets, report |
| `/copilot` | CopilotScreen | `POST /copilot/ask` |
| `/settings` | SettingsScreen | portfolio picker, logout |

**Not yet implemented:** `/exits` (Exit Approval Queue), `/analytics` (Performance Analytics), `/committee/:symbol`.

---

## 6. Auth

Full JWT flow — see [`docs/frontend/AUTHENTICATION_PREPARATION.md`](../../docs/frontend/AUTHENTICATION_PREPARATION.md).

- `AuthGate` protects all routes except `/login`
- `X-Portfolio-Id` on every API call
- `EXPO_PUBLIC_AUTH_BYPASS=true` for local dev without login UI

---

## 6. Responsive layout

| Breakpoint | Chrome |
|------------|--------|
| `< 1024px` | Bottom `TabBar` (5 primary tabs) |
| `≥ 1024px` | Sidebar 240px + optional Copilot side panel 400px |

`MasterDetailLayout` on desktop recommendations; mobile pushes to `[symbol]` route.

---

## 7. Commands

```bash
cd frontend
pnpm install
pnpm dev:web
pnpm dev:mobile
pnpm typecheck
pnpm test
```

---

## 8. Known gaps

| Gap | Spec reference |
|-----|----------------|
| Exit Approval Queue screen | SCREEN_SPECIFICATIONS §4 |
| Analytics screen | SCREEN_SPEC §7 |
| HITL queue modal (`getQueue`) | APPROVAL_WORKFLOW_UX |
| Citation deep links in Copilot | COPILOT_UX |
| Pull-to-refresh | RESPONSIVE_LAYOUT_GUIDE |
| Settings not in mobile TabBar | — |

---

## 9. Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-05 | Track F foundation (placeholders) |
| 2.0 | 2026-06-05 | Track F2 live API integration; auth shipped |
