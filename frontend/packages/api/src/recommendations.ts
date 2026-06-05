import type {
  ApproveRequest,
  DailyRecommendationsRead,
  RecommendationResultRead,
} from '@pipm/types';
import type { ApiClient } from './client';

export function createRecommendationsApi(client: ApiClient) {
  return {
    getDaily(params: { asOfDate: string; action?: string }) {
      return client.get<DailyRecommendationsRead>('/recommendations/daily', {
        params: { as_of_date: params.asOfDate, action: params.action },
      });
    },
    getRunResults(runId: string, action?: string) {
      return client.get<RecommendationResultRead[]>(`/recommendations/${runId}`, {
        params: { action },
      });
    },
    getStockResult(runId: string, symbol: string) {
      return client.get<RecommendationResultRead>(
        `/recommendations/${runId}/stocks/${symbol}`,
      );
    },
    getQueue() {
      return client.get<RecommendationResultRead[]>('/recommendations/queue');
    },
    approve(resultId: string, body: ApproveRequest) {
      return client.post<{ status: string; decision: string }>(
        `/recommendations/${resultId}/approve`,
        body,
      );
    },
    reject(resultId: string, params?: { note?: string; actorId?: string }) {
      return client.post<{ status: string }>(`/recommendations/${resultId}/reject`, undefined, {
        params: { note: params?.note, actor_id: params?.actorId ?? 'owner' },
      });
    },
  };
}

export type RecommendationsApi = ReturnType<typeof createRecommendationsApi>;
