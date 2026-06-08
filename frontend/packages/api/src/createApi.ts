import { createApiClient, type ApiClientConfig } from './client';
import { createAuthApi } from './auth';
import { createStocksApi } from './stocks';
import { createRecommendationsApi } from './recommendations';
import { createPortfolioApi } from './portfolio';
import { createCommitteeApi } from './committee';
import { createCopilotApi } from './copilot';
import { createAnalyticsApi } from './analytics';
import { createPilotApi } from './pilot';
import { createObservabilityApi } from './observability';

export interface PipmApi {
  client: ReturnType<typeof createApiClient>;
  auth: ReturnType<typeof createAuthApi>;
  stocks: ReturnType<typeof createStocksApi>;
  recommendations: ReturnType<typeof createRecommendationsApi>;
  portfolio: ReturnType<typeof createPortfolioApi>;
  committee: ReturnType<typeof createCommitteeApi>;
  copilot: ReturnType<typeof createCopilotApi>;
  analytics: ReturnType<typeof createAnalyticsApi>;
  pilot: ReturnType<typeof createPilotApi>;
  observability: ReturnType<typeof createObservabilityApi>;
}

export function createPipmApi(config: ApiClientConfig): PipmApi {
  const client = createApiClient(config);
  return {
    client,
    auth: createAuthApi(client),
    stocks: createStocksApi(client),
    recommendations: createRecommendationsApi(client),
    portfolio: createPortfolioApi(client),
    committee: createCommitteeApi(client),
    copilot: createCopilotApi(client),
    analytics: createAnalyticsApi(client),
    pilot: createPilotApi(client),
    observability: createObservabilityApi(client),
  };
}
