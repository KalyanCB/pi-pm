import type { CommitteeExplainResponse, CommitteePacket, CommitteeReviewSummary } from '@pipm/types';
import { ApiError } from './errors';
import type { ApiClient } from './client';

export function createCommitteeApi(client: ApiClient) {
  return {
    async getLatest(
      universeCode = 'NIFTY_1000',
      strategyName?: string,
      asOfDate?: string,
    ): Promise<CommitteeReviewSummary | null> {
      try {
        const params: Record<string, string> = { universe_code: universeCode };
        if (strategyName) params.strategy_name = strategyName;
        if (asOfDate) params.as_of_date = asOfDate;
        return await client.get<CommitteeReviewSummary>('/investment-committee/latest', {
          params,
        });
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return null;
        }
        throw error;
      }
    },
    getReview(reviewId: string) {
      return client.get<CommitteeReviewSummary>(`/investment-committee/${reviewId}`);
    },
    getPackets(reviewId: string, symbol?: string) {
      return client.get<CommitteePacket[]>(`/investment-committee/${reviewId}/packets`, {
        params: { symbol },
      });
    },
    getExplain(reviewId: string) {
      return client.get<CommitteeExplainResponse>(`/investment-committee/${reviewId}/explain`);
    },
    getReport(reviewId: string) {
      return client.get<{
        committee_review_id: string;
        status: string;
        reports: Array<{
          symbol: string;
          summary: string;
          narrative: string;
          confidence: number | null;
        }>;
      }>(`/investment-committee/${reviewId}/report`);
    },
  };
}

export type CommitteeApi = ReturnType<typeof createCommitteeApi>;
