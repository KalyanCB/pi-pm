import { createApiClient, type ApiClientConfig } from './client';
import { createRecommendationsApi } from './recommendations';
import { createPortfolioApi } from './portfolio';
import { createCommitteeApi } from './committee';
import { createCopilotApi } from './copilot';
import { createAnalyticsApi } from './analytics';

export interface PipmApi {
  client: ReturnType<typeof createApiClient>;
  recommendations: ReturnType<typeof createRecommendationsApi>;
  portfolio: ReturnType<typeof createPortfolioApi>;
  committee: ReturnType<typeof createCommitteeApi>;
  copilot: ReturnType<typeof createCopilotApi>;
  analytics: ReturnType<typeof createAnalyticsApi>;
}

export function createPipmApi(config: ApiClientConfig): PipmApi {
  const client = createApiClient(config);
  return {
    client,
    recommendations: createRecommendationsApi(client),
    portfolio: createPortfolioApi(client),
    committee: createCommitteeApi(client),
    copilot: createCopilotApi(client),
    analytics: createAnalyticsApi(client),
  };
}
