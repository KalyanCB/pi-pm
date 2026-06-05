import type { CommitteePacket, CommitteeReviewSummary } from '@pipm/types';
import type { ApiClient } from './client';

export function createCommitteeApi(client: ApiClient) {
  return {
    getLatest(universeCode = 'NIFTY_500') {
      return client.get<CommitteeReviewSummary>('/investment-committee/latest', {
        params: { universe_code: universeCode },
      });
    },
    getReview(reviewId: string) {
      return client.get<CommitteeReviewSummary>(`/investment-committee/${reviewId}`);
    },
    getPackets(reviewId: string, symbol?: string) {
      return client.get<CommitteePacket[]>(`/investment-committee/${reviewId}/packets`, {
        params: { symbol },
      });
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
