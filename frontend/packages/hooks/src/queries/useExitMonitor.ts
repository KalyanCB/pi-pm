import { useQuery } from '@tanstack/react-query';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';
import { useAuthStore } from '../stores/authStore';

export function useExitMonitorQuery(asOfDate: string, includeResolved = false) {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');

  return useQuery({
    queryKey: queryKeys.portfolio.exits(asOfDate, includeResolved),
    queryFn: () =>
      api.portfolio.getExits(asOfDate, includeResolved ? { includeResolved: true } : undefined),
    enabled: isAuthenticated && !!asOfDate,
    staleTime: 30_000,
  });
}
