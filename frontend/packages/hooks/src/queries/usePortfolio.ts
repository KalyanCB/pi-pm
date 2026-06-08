import { useQuery } from '@tanstack/react-query';
import { ReconciliationGateError } from '@pipm/api';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';
import { useAuthStore } from '../stores/authStore';

export function usePortfolioScreen(includeClosed = false) {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');
  const portfolioId = useAuthStore((s) => s.activePortfolioId);

  const summary = useQuery({
    queryKey: queryKeys.portfolio.summary(portfolioId),
    queryFn: () => api.portfolio.getSummary(),
    enabled: isAuthenticated,
  });

  const positions = useQuery({
    queryKey: [...queryKeys.portfolio.positions(portfolioId), { includeClosed }],
    queryFn: () => api.portfolio.getPositions(includeClosed),
    enabled: isAuthenticated,
  });

  const performance = useQuery({
    queryKey: queryKeys.portfolio.performance(undefined, portfolioId),
    queryFn: () => api.portfolio.getPerformance(),
    enabled: isAuthenticated,
  });

  const attribution = useQuery({
    queryKey: queryKeys.portfolio.attribution(undefined, portfolioId),
    queryFn: () => api.portfolio.getAttribution(),
    enabled: isAuthenticated,
    retry: (count, error) => {
      if (error instanceof ReconciliationGateError) return false;
      return count < 2;
    },
  });

  const reconciliationBlocked = attribution.error instanceof ReconciliationGateError;

  return {
    summary: summary.data,
    positions: positions.data ?? [],
    performance: performance.data,
    attribution: attribution.data,
    reconciliationBlocked,
    isLoading:
      summary.isLoading || positions.isLoading || performance.isLoading || attribution.isLoading,
    isError: summary.isError || positions.isError,
    error: summary.error ?? positions.error ?? attribution.error,
    refetch: () =>
      Promise.all([summary.refetch(), positions.refetch(), performance.refetch(), attribution.refetch()]),
  };
}
