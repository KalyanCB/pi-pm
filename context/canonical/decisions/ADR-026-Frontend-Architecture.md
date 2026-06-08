# ADR-026: Frontend Architecture — React Native + React Native Web

**Status:** Accepted  
**Date:** 2026-06-05  
**Deciders:** Lead Frontend Architect, Product Owner  
**Supersedes:** N/A — first governing frontend architecture document  
**Related:** [ADR-021](./ADR-021-Recommendation-Platform-Architecture.md), [Mobile PRD](../product/09_MOBILE_APP_PRD.md), [Design system](../frontend/DESIGN_SYSTEM.md)

---

## Context

Pi-PM is a portfolio operations platform — not a retail trading app. The owner needs a responsive web application that surfaces portfolio health, machine recommendations, committee advisory, and grounded copilot Q&A. A future native mobile app (Android/iOS) must share the same product surface without duplicating business logic or UI components.

The backend exposes rich REST APIs across recommendations, portfolio, investment committee, analytics, and copilot. Track B documented mobile API contracts and DTO gaps. Track D establishes the **frontend architecture** before any UI implementation.

---

## Decision

Adopt a **single TypeScript codebase** using **React Native + React Native Web** in a **monorepo**, with:

1. **Web as primary deployment target** (responsive Bloomberg Terminal Lite aesthetic)
2. **Shared component library** across web and native shells
3. **Layout adapters** per breakpoint — same data, different presentation
4. **Backend as sole source of truth** — frontend never computes conviction, allocation, alpha, ranking, validation, or risk metrics
5. **TanStack Query** for server state; **Zustand** for client/UI state
6. **Future-ready native packaging** via `apps/mobile` without forking product code

---

## 1. Why React Native + React Native Web

| Factor | Rationale |
|--------|-----------|
| Single component model | `View`, `Text`, `Pressable` compile to DOM (web) and native views (iOS/Android) |
| TypeScript end-to-end | Aligns with backend contract typing in `packages/types` |
| Ecosystem maturity | Expo + RN Web production-ready for data-dense dashboards |
| Team velocity | One PR updates web and future mobile simultaneously |
| Bloomberg Terminal Lite | Dense tables, badges, panels map well to flexbox layouts on both targets |

**Alternatives rejected:**

| Alternative | Why rejected |
|-------------|--------------|
| React (web) + React Native (mobile) separate | Duplicate components, divergent UX, 2× maintenance |
| Flutter | No code sharing with existing TypeScript API types; team stack is React |
| Next.js only | No native path without rewrite; SSR not required for owner dashboard |
| Ionic/Capacitor | WebView wrapper inferior to RN native navigation performance |

---

## 2. Why single codebase

Pi-PM has **one owner persona** and **one API surface**. Screens (Dashboard, Recommendations, Portfolio, Committee, Copilot) render the same backend fields regardless of device. Differences are **layout and density**, not product logic.

```
packages/ui     → shared components (RecommendationCard, TrustScoreCard, …)
packages/hooks  → shared data hooks (useDashboard, useRecommendations, …)
apps/web        → sidebar layout, wide tables, multi-panel dashboard
apps/mobile     → bottom tabs, stacked cards (future native shell)
```

Forking at the screen level would guarantee drift between web and mobile advisory displays — unacceptable when committee HIGH_CONCERN must render identically.

---

## 3. Why backend owns business logic

Per ADR-021 and platform governance:

| Frontend MUST NOT | Backend owns |
|-------------------|--------------|
| Calculate conviction | `conviction_score`, `conviction_band`, `conviction_components` |
| Calculate allocation | `GET /portfolio/allocation`, position `weight_pct` |
| Calculate alpha | `GET /portfolio/performance`, `/benchmark`, `/nav-history` |
| Calculate ranking | `ranking_results` via recommendations API |
| Calculate validation metrics | Validation reports via backend |
| Calculate risk metrics | `GET /portfolio/risk`, `risk_level` on dashboard |

Frontend responsibilities: **render, visualize, filter, sort, navigate, collect user actions** (approve, reject, confirm exit, ask copilot).

Violations (e.g. client-side conviction band thresholds) would desync from deterministic engine replay — **rejected**.

---

## 4. Why layouts differ but components are shared

| Breakpoint | Layout pattern | Shared components |
|------------|----------------|-------------------|
| Mobile (<768px) | Bottom tabs, single column, bottom sheet detail | `RecommendationCard`, `ConvictionBadge` |
| Tablet (768–1024px) | Collapsible sidebar, 2-column grid | Same cards, wider grid |
| Desktop (>1024px) | Fixed sidebar + multi-panel content | Same cards in dense table rows |

**Layout shells are platform-specific** (`apps/web/layouts`, `apps/mobile/layouts`). **Data components are shared** (`packages/ui`).

Example — Dashboard:
- **Desktop:** 4-column metric strip + 2-panel (positions table | risk alerts)
- **Mobile:** Vertical scroll of `TrustScoreCard`, `PortfolioSummaryCard`, BUY preview strip

Same `DashboardScreenModel`; different `DashboardLayout` wrapper.

---

## 5. Why web is primary deployment target

| Reason | Detail |
|--------|--------|
| Owner workflow | Morning review at desk; multi-panel density favors desktop |
| Committee narratives | Markdown reports, wide tables — poor fit for phone-first |
| Copilot | Side panel on desktop; full-screen on mobile |
| Deployment speed | `apps/web` ships via static/SSR host without app store |
| API development | Web dev loop fastest for Track D → implementation phases |

Mobile web (responsive) satisfies phone access immediately. Native apps are Phase 4.

---

## 6. Why mobile packaging is future-ready

The monorepo isolates **shell concerns** in `apps/`:

| Package | Web | Native (future) |
|---------|-----|-----------------|
| `packages/ui` | ✅ shared | ✅ shared |
| `packages/api` | ✅ shared | ✅ shared |
| `packages/navigation` | Web router adapter | React Navigation adapter |
| `apps/web` | Expo Web / Metro Web | — |
| `apps/mobile` | — | Expo native build |

No business components import `react-dom` or `react-native` directly — they import from `packages/ui` which uses platform extensions (`.web.tsx` / `.native.tsx`) only where unavoidable (e.g. `Sidebar` vs `TabBar`).

---

## 7. Technology stack

| Layer | Choice |
|-------|--------|
| Framework | React 19 + React Native 0.76+ |
| Web target | React Native Web via Expo |
| Language | TypeScript 5.x strict |
| Monorepo | pnpm workspaces + Turborepo |
| Server state | TanStack Query v5 |
| Client state | Zustand v5 |
| Navigation (web) | Expo Router (file-based, web-compatible) |
| Navigation (native) | Expo Router (same routes, different layouts) |
| Styling | StyleSheet + design tokens in `packages/theme` |
| API client | Typed fetch wrapper in `packages/api` |
| Markdown | `react-native-markdown-display` (web + native) |

---

## 8. Consequences

### Positive

- One PR updates all platforms
- Typed API contracts reduce integration bugs
- Responsive web ships before app store review
- Clear boundary: backend computes, frontend presents

### Negative

- RN Web bundle size larger than pure React — mitigated by route-based code splitting
- Some web-only patterns (hover, right-click) need `.web.tsx` adapters
- Dense tables require custom `DataTable` component (no HTML `<table>` on native)

### Risks

| Risk | Mitigation |
|------|------------|
| RN Web performance on large lists | Virtualized lists (`FlashList`) |
| Layout divergence | Shared Storybook/visual regression per component |
| Auth not yet in backend | `AUTHENTICATION_PREPARATION.md` — stub layer |

---

## 9. Compliance with acceptance criteria

| ID | Requirement | Addressed |
|----|-------------|-----------|
| AC-FE-01 | Single codebase documented | §2, §7 |
| AC-FE-02 | Web and mobile layouts defined | §4, RESPONSIVE_LAYOUT_GUIDE |
| AC-FE-03 | Shared component strategy | §4, COMPONENT_LIBRARY |
| AC-FE-04 | API integration approach | API_INTEGRATION_PLAN |
| AC-FE-05 | Screen specifications | SCREEN_SPECIFICATIONS |
| AC-FE-06 | Authentication preparation | AUTHENTICATION_PREPARATION |
| AC-FE-07 | Copilot UX defined | COPILOT_EXPERIENCE |
| AC-FE-08 | Implementation roadmap | IMPLEMENTATION_ROADMAP |

---

## 10. Revision history

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-05 | Initial ADR — Track D |
