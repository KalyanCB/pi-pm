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
  // Pass through undefined to request the OVERALL trust (no strategy filter) —
  // a regime-specific strategy often has too few sessions and returns a null
  // trust score, which left the dashboard's Trust card blank.
  const strategy = strategyName;

  return useQuery({
    queryKey: queryKeys.trust(strategy ?? 'all', portfolioId),
    queryFn: () => api.analytics.getTrustMetrics({ strategyName: strategy }),
    enabled: isAuthenticated,
  });
}

export function useDashboard() {
  const dashboard = useDashboardQuery();
  // Overall portfolio trust (no strategy filter) — the dashboard card shows the
  // book-level trust score, not a single regime-strategy's (which is often null).
  const trust = useTrustQuery();

  return {
    dashboard: dashboard.data,
    trustScore: trust.data?.overall_trust_score ?? null,
    // Only gate the page spinner on the PRIMARY dashboard query. The trust query
    // (regime-derived strategy) can lag or return null and must not keep the whole
    // console stuck in "Loading portfolio health…" once the data is in.
    isLoading: dashboard.isLoading,
    isError: dashboard.isError,
    error: dashboard.error ?? trust.error,
    refetch: () => Promise.all([dashboard.refetch(), trust.refetch()]),
  };
}
