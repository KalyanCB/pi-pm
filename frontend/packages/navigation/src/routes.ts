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
