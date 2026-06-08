import type { RegimeCurrent } from '@pipm/types';
import { ApiError } from './errors';
import type { ApiClient } from './client';

export function createObservabilityApi(client: ApiClient) {
  return {
    async getCurrentRegime(asOfDate?: string): Promise<RegimeCurrent | null> {
      try {
        return await client.get<RegimeCurrent>('/observability/regime/current', {
          params: asOfDate ? { as_of_date: asOfDate } : undefined,
        });
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return null;
        }
        throw error;
      }
    },
  };
}

export type ObservabilityApi = ReturnType<typeof createObservabilityApi>;
