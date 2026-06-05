# Pi-PM Frontend — Track F Architecture Report

**Date:** 2026-06-05  
**Track:** F — Frontend Monorepo Foundation  
**ADR:** [ADR-026](../../docs/architecture/ADR-026-Frontend-Architecture.md)

---

## 1. Summary

Track F implemented the **frontend monorepo foundation** per ADR-026. No business features or live API integration were added. The codebase is a single TypeScript monorepo using React Native + React Native Web, pnpm workspaces, and Turborepo.

---

## 2. Repository Structure

```
frontend/
├── apps/
│   ├── web/          @pipm/web   — Expo Web (primary)
│   └── mobile/       @pipm/mobile — Expo native shell
├── packages/
│   ├── types/        @pipm/types
│   ├── theme/        @pipm/theme
│   ├── api/          @pipm/api
│   ├── hooks/        @pipm/hooks
│   ├── navigation/   @pipm/navigation
│   └── ui/           @pipm/ui
├── metro.config.base.js
├── package.json
├── pnpm-workspace.yaml
└── turbo.json
```

---

## 3. Technology Stack (Implemented)

| Layer | Package | Status |
|-------|---------|--------|
| Types | `@pipm/types` | ✅ API + component prop types |
| Theme | `@pipm/theme` | ✅ Dark terminal palette, breakpoints |
| API | `@pipm/api` | ✅ Typed clients, errors, retry helpers |
| Hooks | `@pipm/hooks` | ✅ Zustand stores, TanStack Query, providers |
| Navigation | `@pipm/navigation` | ✅ Sidebar, TabBar, AppShell, routes |
| UI | `@pipm/ui` | ✅ 10 components + 6 screen shells |
| Web app | `@pipm/web` | ✅ Expo Router, responsive shell |
| Mobile app | `@pipm/mobile` | ✅ Expo native, mirrored routes |

---

## 4. State Management

| Concern | Implementation |
|---------|----------------|
| Server state | TanStack Query v5 via `createQueryClient()` |
| Auth (stub) | `useAuthStore` — dev owner session |
| UI filters | `useUiStore` |
| Copilot session | `useCopilotStore` |
| API access | `AppProviders` + `useApi()` |

Query hooks (`useDashboardQuery`, `useDailyRecommendationsQuery`) are **disabled by default** until Phase 2.

---

## 5. Navigation

| Breakpoint | Chrome |
|------------|--------|
| `< 1024px` | Bottom `TabBar` (5 tabs) |
| `≥ 1024px` | Fixed `Sidebar` (240px) |

`AppShell` in `@pipm/navigation` switches layout via `useBreakpoint()`.

Routes: `/`, `/recommendations`, `/portfolio`, `/committee`, `/copilot`, `/settings`

---

## 6. Components Delivered

| Component | Package | Tests |
|-----------|---------|-------|
| RecommendationCard | ui | ✅ |
| PortfolioPositionCard | ui | — |
| ConvictionBadge | ui | ✅ |
| RiskIndicator | ui | — |
| TrustScoreCard | ui | — |
| CommitteeAdvisoryCard | ui | — |
| HighConcernBanner | ui | — |
| CopilotMessage | ui | — |
| CitationPanel | ui | — |
| RecommendationReasonList | ui | — |

---

## 7. Screen Shells (Empty)

| Screen | Route | Status |
|--------|-------|--------|
| Dashboard | `/` | Placeholder |
| Recommendations | `/recommendations` | Placeholder |
| Portfolio | `/portfolio` | Placeholder |
| Committee | `/committee` | Placeholder |
| Copilot | `/copilot` | Static sample message |
| Settings | `/settings` | Placeholder |

---

## 8. API Layer (Foundation Only)

- `createPipmApi()` aggregates domain clients
- Endpoints typed for recommendations, portfolio, committee, copilot, analytics
- `ApiError`, `ReconciliationGateError`, `shouldRetry`, `retryDelay`
- **No screens call live APIs** — hooks use `enabled: false`

---

## 9. Commands

```bash
cd frontend
pnpm install
pnpm dev:web          # Start web dev server
pnpm dev:mobile       # Start Expo native
pnpm typecheck        # TypeScript all packages
pnpm test             # Unit tests (api, navigation, ui)
pnpm build            # Export web + mobile bundles
```

**Note:** `.npmrc` uses `node-linker=hoisted` for Expo Metro compatibility with pnpm workspaces.

## 9.1 Build validation (2026-06-05)

| Target | Command | Result |
|--------|---------|--------|
| Web | `pnpm --filter @pipm/web build` | ✅ `apps/web/dist` |
| Mobile | `pnpm --filter @pipm/mobile build` | ✅ iOS + Android + web bundles |
| Typecheck | `pnpm typecheck` | ✅ 14/14 packages |
| API tests | 6 passed | ✅ |
| Navigation tests | 5 passed | ✅ |
| UI tests | 4 passed | ✅ |

---

## 10. Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Single codebase | ✅ |
| Web builds | ✅ `pnpm --filter @pipm/web build` |
| Mobile builds | ✅ `pnpm --filter @pipm/mobile build` |
| Shared components operational | ✅ + unit tests |
| No backend changes | ✅ |

---

## 11. Next Phase (Phase 2)

1. Enable `useDashboard` composite hook with live API
2. Wire Recommendations list with committee join
3. Portfolio 409 gate handling
4. Playwright E2E for web

---

## 12. Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-05 | Track F foundation complete |
