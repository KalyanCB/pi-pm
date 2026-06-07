import type {
  PilotHealthDashboard,
  RecommendationPilotDashboard,
  TrustDashboard,
} from '@pipm/types';
import type { DateRange } from '@pipm/types';
import type { ApiClient } from './client';

export function createPilotApi(client: ApiClient) {
  return {
    getHealthDashboard(asOfDate?: string) {
      return client.get<PilotHealthDashboard>('/pilot/dashboard/health', {
        params: { as_of_date: asOfDate },
      });
    },
    getRecommendationDashboard(asOfDate?: string, range?: DateRange) {
      return client.get<RecommendationPilotDashboard>('/pilot/dashboard/recommendations', {
        params: {
          as_of_date: asOfDate,
          from_date: range?.from,
          to_date: range?.to,
        },
      });
    },
    getTrustDashboard(range?: DateRange) {
      return client.get<TrustDashboard>('/pilot/dashboard/trust', {
        params: { from_date: range?.from, to_date: range?.to },
      });
    },
    getCommitteeDashboard(range?: DateRange) {
      return client.get<Record<string, unknown>>('/pilot/dashboard/committee', {
        params: { from_date: range?.from, to_date: range?.to },
      });
    },
  };
}

export type PilotApi = ReturnType<typeof createPilotApi>;
