import { useQuery } from '@tanstack/react-query';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';

/** Foundation hook — wired in Phase 2. Query disabled until feature phase. */
export function useDashboardQuery(enabled = false) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.dashboard(),
    queryFn: () => api.portfolio.getDashboard(),
    enabled,
  });
}
