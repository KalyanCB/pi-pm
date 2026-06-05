import type { TrustMetricsDTO } from '@pipm/types';
import type { DateRange } from '@pipm/types';
import type { ApiClient } from './client';

export function createAnalyticsApi(client: ApiClient) {
  return {
    getTrustMetrics(params?: DateRange & { strategyName?: string }) {
      return client.get<TrustMetricsDTO>('/analytics/recommendations/trust', {
        params: {
          from_date: params?.from,
          to_date: params?.to,
          strategy_name: params?.strategyName,
        },
      });
    },
  };
}

export type AnalyticsApi = ReturnType<typeof createAnalyticsApi>;
