import type {
  ExitRecommendation,
  PortfolioDashboardResponse,
  PortfolioPosition,
} from '@pipm/types';
import type { DateRange } from '@pipm/types';
import type { ApiClient } from './client';

export function createPortfolioApi(client: ApiClient) {
  return {
    getDashboard() {
      return client.get<PortfolioDashboardResponse>('/portfolio/dashboard');
    },
    getPositions() {
      return client.get<PortfolioPosition[]>('/portfolio/positions');
    },
    getExits(asOfDate?: string) {
      return client.get<ExitRecommendation[]>('/portfolio/exits', {
        params: { as_of_date: asOfDate },
      });
    },
    getPerformance(range?: DateRange) {
      return client.get<Record<string, unknown>>('/portfolio/performance', {
        params: { from_date: range?.from, to_date: range?.to },
      });
    },
    getRisk() {
      return client.get<Record<string, unknown>>('/portfolio/risk');
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
