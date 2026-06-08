import { useQuery } from '@tanstack/react-query';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';
import { useAuthStore } from '../stores/authStore';

export function useRegimeQuery(asOfDate?: string) {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');

  return useQuery({
    queryKey: queryKeys.regime.current(asOfDate),
    // No date → current/latest regime (used by dashboard & committee screen).
    queryFn: () => api.observability.getCurrentRegime(asOfDate),
    enabled: isAuthenticated,
    staleTime: 60_000,
  });
}
