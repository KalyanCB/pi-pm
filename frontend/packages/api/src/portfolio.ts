import type {
  AttributionReport,
  ExitRecommendation,
  NavHistoryPoint,
  PerformanceMetrics,
  PortfolioDashboardResponse,
  PortfolioPosition,
  PortfolioSummary,
} from '@pipm/types';
import type { DateRange } from '@pipm/types';
import type { ApiClient } from './client';

export function createPortfolioApi(client: ApiClient) {
  return {
    getDashboard() {
      return client.get<PortfolioDashboardResponse>('/portfolio/dashboard');
    },
    getSummary(asOfDate?: string) {
      return client.get<PortfolioSummary>('/portfolio/summary', {
        params: { as_of_date: asOfDate },
      });
    },
    getPositions(includeClosed?: boolean) {
      return client.get<PortfolioPosition[]>('/portfolio/positions', {
        params: includeClosed ? { include_closed: true } : undefined,
      });
    },
    getExits(asOfDate?: string, options?: { includeResolved?: boolean }) {
      return client.get<ExitRecommendation[]>('/portfolio/exits', {
        params: {
          as_of_date: asOfDate,
          include_resolved: options?.includeResolved ? true : undefined,
        },
      });
    },
    getPerformance(range?: DateRange) {
      return client.get<PerformanceMetrics>('/portfolio/performance', {
        params: { from_date: range?.from, to_date: range?.to },
      });
    },
    getAttribution(range?: DateRange) {
      return client.get<AttributionReport>('/portfolio/attribution', {
        params: { from_date: range?.from, to_date: range?.to },
      });
    },
    getRisk() {
      return client.get<Record<string, unknown>>('/portfolio/risk');
    },
    getNavHistory(range?: DateRange) {
      return client.get<NavHistoryPoint[]>('/portfolio/nav-history', {
        params: { from_date: range?.from, to_date: range?.to },
      });
    },
    confirmExit(exitId: string) {
      return client.post<{ id: string; status: string }>(
        `/portfolio/exits/${exitId}/confirm`,
      );
    },
    rejectExit(exitId: string, reason?: string) {
      return client.post<{ id: string; status: string }>(
        `/portfolio/exits/${exitId}/reject`,
        undefined,
        { params: { reason } },
      );
    },
  };
}

export type PortfolioApi = ReturnType<typeof createPortfolioApi>;
