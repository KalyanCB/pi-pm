import type { DateRange } from '@pipm/types';

export const queryKeys = {
  dashboard: (portfolioId?: string | null) =>
    ['portfolio', 'dashboard', portfolioId] as const,
  trust: (params?: DateRange, portfolioId?: string | null) =>
    ['analytics', 'trust', params, portfolioId] as const,
  stocks: {
    list: () => ['stocks', 'list'] as const,
  },
  recommendations: {
    dates: (strategy?: string) => ['recommendations', 'dates', strategy] as const,
    daily: (date: string, action?: string, strategy?: string) =>
      ['recommendations', 'daily', date, action, strategy] as const,
    run: (runId: string, action?: string) =>
      ['recommendations', 'run', runId, action] as const,
    queue: () => ['recommendations', 'queue'] as const,
    detail: (runId: string, symbol: string) =>
      ['recommendations', 'detail', runId, symbol] as const,
  },
  pilot: {
    health: () => ['pilot', 'health'] as const,
    recommendations: () => ['pilot', 'recommendations'] as const,
    trust: () => ['pilot', 'trust'] as const,
  },
  portfolio: {
    navHistory: (portfolioId?: string | null) =>
      ['portfolio', 'nav-history', portfolioId] as const,
    summary: (portfolioId?: string | null) =>
      ['portfolio', 'summary', portfolioId] as const,
    positions: (portfolioId?: string | null) =>
      ['portfolio', 'positions', portfolioId] as const,
    attribution: (range?: DateRange, portfolioId?: string | null) =>
      ['portfolio', 'attribution', range, portfolioId] as const,
    performance: (range?: DateRange, portfolioId?: string | null) =>
      ['portfolio', 'performance', range, portfolioId] as const,
    exits: (asOfDate?: string, includeResolved?: boolean) =>
      ['portfolio', 'exits', asOfDate, includeResolved] as const,
  },
  committee: {
    latest: (universe?: string) => ['committee', 'latest', universe] as const,
    packets: (id: string) => ['committee', 'packets', id] as const,
    report: (id: string) => ['committee', 'report', id] as const,
  },
  copilot: {
    audit: (limit: number) => ['copilot', 'audit', limit] as const,
  },
  regime: {
    current: (asOfDate?: string) => ['regime', 'current', asOfDate] as const,
  },
};
