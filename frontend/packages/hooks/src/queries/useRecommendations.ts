import { useQuery } from '@tanstack/react-query';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';

/** Foundation hook — wired in Phase 2. */
export function useDailyRecommendationsQuery(
  asOfDate: string,
  action?: string,
  enabled = false,
) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.recommendations.daily(asOfDate, action),
    queryFn: () => api.recommendations.getDaily({ asOfDate, action }),
    enabled: enabled && !!asOfDate,
  });
}
