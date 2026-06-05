import type { DateRange } from '@pipm/types';

export const queryKeys = {
  dashboard: () => ['portfolio', 'dashboard'] as const,
  trust: (params?: DateRange) => ['analytics', 'trust', params] as const,
  recommendations: {
    daily: (date: string, action?: string) =>
      ['recommendations', 'daily', date, action] as const,
    queue: () => ['recommendations', 'queue'] as const,
    detail: (runId: string, symbol: string) =>
      ['recommendations', 'detail', runId, symbol] as const,
  },
  portfolio: {
    positions: () => ['portfolio', 'positions'] as const,
    exits: () => ['portfolio', 'exits'] as const,
    performance: (range?: DateRange) => ['portfolio', 'performance', range] as const,
  },
  committee: {
    latest: () => ['committee', 'latest'] as const,
    packets: (id: string) => ['committee', 'packets', id] as const,
  },
  copilot: {
    audit: (limit: number) => ['copilot', 'audit', limit] as const,
  },
};
