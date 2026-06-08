import { useQuery } from '@tanstack/react-query';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';
import { useAuthStore } from '../stores/authStore';

export function useNavHistoryQuery() {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');
  const portfolioId = useAuthStore((s) => s.activePortfolioId);

  return useQuery({
    queryKey: queryKeys.portfolio.navHistory(portfolioId),
    queryFn: () => api.portfolio.getNavHistory(),
    enabled: isAuthenticated,
    staleTime: 60_000,
  });
}

export function useNavHistory() {
  const query = useNavHistoryQuery();
  const points = query.data ?? [];
  const navSeries = points.map((p) => p.total_equity);
  const alphaSeries = points.map((p) => p.alpha_pct).filter((v): v is number => v != null);
  const returnSeries = points.map((p) => p.day_return_pct).filter((v): v is number => v != null);
  const trustFromNav = points; // alpha/return from same series

  return {
    points,
    navSeries,
    alphaSeries,
    returnSeries,
    latest: points[points.length - 1] ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
