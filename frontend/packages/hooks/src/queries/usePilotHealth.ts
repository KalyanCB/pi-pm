import { useQuery } from '@tanstack/react-query';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';
import { useAuthStore } from '../stores/authStore';

export function usePilotHealthQuery() {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');

  return useQuery({
    queryKey: queryKeys.pilot.health(),
    queryFn: () => api.pilot.getHealthDashboard(),
    enabled: isAuthenticated,
  });
}

export function usePilotRecommendationsQuery() {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');

  return useQuery({
    queryKey: queryKeys.pilot.recommendations(),
    queryFn: () => api.pilot.getRecommendationDashboard(),
    enabled: isAuthenticated,
  });
}

export function useTrustDashboardQuery() {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');

  return useQuery({
    queryKey: queryKeys.pilot.trust(),
    queryFn: () => api.pilot.getTrustDashboard(),
    enabled: isAuthenticated,
  });
}
