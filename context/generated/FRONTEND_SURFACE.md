---
generated_at: 2026-06-28T03:28:38Z
generator: scripts/generate_context.py
---

# Frontend Surface

## Routes (`frontend/packages/navigation/src/routes.ts`)

```typescript
export const Routes = {
  dashboard: '/',
  recommendations: '/recommendations',
  recommendationDetail: (symbol: string) => `/recommendations/${symbol}`,
  portfolio: '/portfolio',
  exits: '/exits',
  committee: '/committee',
  copilot: '/copilot',
  settings: '/settings',
  analytics: '/analytics',
} as const;

export type RouteKey = keyof typeof Routes;

export interface NavItem {
  key: RouteKey;
  label: string;
  href: string;
  icon: string;
}

export const NAV_ITEMS: NavItem[] = [
  { key: 'dashboard', label: 'Dashboard', href: Routes.dashboard, icon: '◉' },
  { key: 'recommendations', label: 'Recommendations', href: Routes.recommendations, icon: '◈' },
  { key: 'portfolio', label: 'Portfolio', href: Routes.portfolio, icon: '◎' },
  { key: 'committee', label: 'Committee', href: Routes.committee, icon: '◇' },
  { key: 'copilot', label: 'Copilot', href: Routes.copilot, icon: '◆' },
];

export const SECONDARY_NAV: NavItem[] = [
  { key: 'settings', label: 'Settings', href: Routes.settings, icon: '⚙' },
];
```

## React Query hooks

- `frontend/packages/hooks/src/queries/useActiveStrategy.ts`
- `frontend/packages/hooks/src/queries/useCommittee.ts`
- `frontend/packages/hooks/src/queries/useDashboard.ts`
- `frontend/packages/hooks/src/queries/useExitMonitor.ts`
- `frontend/packages/hooks/src/queries/useNavHistory.ts`
- `frontend/packages/hooks/src/queries/usePilotHealth.ts`
- `frontend/packages/hooks/src/queries/usePortfolio.ts`
- `frontend/packages/hooks/src/queries/useRecommendationDetail.ts`
- `frontend/packages/hooks/src/queries/useRecommendations.ts`
- `frontend/packages/hooks/src/queries/useRegime.ts`
- `frontend/packages/hooks/src/queries/useStocks.ts`

## Screens (`frontend/packages/ui/src/screens/`)

- `CommitteeScreen.tsx`
- `CopilotScreen.tsx`
- `DashboardScreen.tsx`
- `LoginScreen.tsx`
- `PortfolioScreen.tsx`
- `RecommendationDetailScreen.tsx`
- `RecommendationsScreen.tsx`
- `SettingsScreen.tsx`