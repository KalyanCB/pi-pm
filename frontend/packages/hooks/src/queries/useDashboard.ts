import { useQuery } from '@tanstack/react-query';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';
import { useAuthStore } from '../stores/authStore';

export function useDashboardQuery() {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');
  const portfolioId = useAuthStore((s) => s.activePortfolioId);

  return useQuery({
    queryKey: queryKeys.dashboard(portfolioId),
    queryFn: () => api.portfolio.getDashboard(),
    enabled: isAuthenticated,
  });
}

export function useTrustQuery(strategyName?: string) {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');
  const portfolioId = useAuthStore((s) => s.activePortfolioId);
  const strategy = strategyName ?? 'reversal_v1';

  return useQuery({
    queryKey: queryKeys.trust(strategy, portfolioId),
    queryFn: () => api.analytics.getTrustMetrics({ strategyName: strategy }),
    enabled: isAuthenticated,
  });
}

export function useDashboard() {
  const dashboard = useDashboardQuery();
  const trust = useTrustQuery();

  return {
    dashboard: dashboard.data,
    trustScore: trust.data?.overall_trust_score ?? null,
    isLoading: dashboard.isLoading || trust.isLoading,
    isError: dashboard.isError || trust.isError,
    error: dashboard.error ?? trust.error,
    refetch: () => Promise.all([dashboard.refetch(), trust.refetch()]),
  };
}
