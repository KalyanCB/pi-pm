import type { CommitteeExplainResponse, CommitteePacket, CommitteeReviewSummary } from '@pipm/types';
import { ApiError } from './errors';
import type { ApiClient } from './client';

export function createCommitteeApi(client: ApiClient) {
  return {
    async getLatest(
      universeCode = 'NIFTY_500',
      strategyName?: string,
    ): Promise<CommitteeReviewSummary | null> {
      try {
        return await client.get<CommitteeReviewSummary>('/investment-committee/latest', {
          params: strategyName
            ? { universe_code: universeCode, strategy_name: strategyName }
            : { universe_code: universeCode },
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
