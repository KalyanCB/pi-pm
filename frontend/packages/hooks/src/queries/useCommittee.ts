import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { CommitteePacket } from '@pipm/types';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';
import { useAuthStore } from '../stores/authStore';

export function useCommitteeScreen() {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');

  const latest = useQuery({
    queryKey: queryKeys.committee.latest(),
    queryFn: () => api.committee.getLatest(),
    enabled: isAuthenticated,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'RUNNING' || status === 'PENDING' ? 5000 : false;
    },
  });

  const reviewId = latest.data?.run_id;

  const packets = useQuery({
    queryKey: queryKeys.committee.packets(reviewId ?? 'none'),
    queryFn: () => api.committee.getPackets(reviewId!),
    enabled: isAuthenticated && !!reviewId,
  });

  const report = useQuery({
    queryKey: queryKeys.committee.report(reviewId ?? 'none'),
    queryFn: () => api.committee.getReport(reviewId!),
    enabled: isAuthenticated && !!reviewId && latest.data?.status === 'COMPLETED',
  });

  const highConcernPackets = useMemo(
    () =>
      (packets.data ?? []).filter(
        (p) => p.payload.committee_advisory?.high_concern === true,
      ),
    [packets.data],
  );

  const allPackets = packets.data ?? [];

  return {
    review: latest.data,
    packets: allPackets,
    highConcernPackets,
    report: report.data,
    isLoading: latest.isLoading || packets.isLoading,
    isError: latest.isError || packets.isError,
    error: latest.error ?? packets.error,
    refetch: () => Promise.all([latest.refetch(), packets.refetch(), report.refetch()]),
  };
}

export type { CommitteePacket };
