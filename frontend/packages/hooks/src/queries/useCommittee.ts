import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { CommitteePacket, CommitteeReviewFinding } from '@pipm/types';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';
import { useAuthStore } from '../stores/authStore';
import { useUiStore } from '../stores/uiStore';
import { useActiveStrategy } from './useActiveStrategy';
import { useRecommendationDatesQuery } from './useRecommendations';

export function useCommitteeScreen() {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');
  const selectedAsOfDate = useUiStore((s) => s.recommendationAsOfDate);
  const setRecommendationAsOfDate = useUiStore((s) => s.setRecommendationAsOfDate);

  const datesQuery = useRecommendationDatesQuery();
  const latestDate = datesQuery.data?.latest_date ?? null;

  // Strategy follows the regime of the viewed date (current regime when latest).
  const { strategy } = useActiveStrategy(selectedAsOfDate ?? undefined);
  // Only pin a date when one is explicitly selected; otherwise latest review.
  const asOfDateParam = selectedAsOfDate ?? undefined;

  const latest = useQuery({
    queryKey: queryKeys.committee.latest(undefined, strategy, asOfDateParam),
    queryFn: () => api.committee.getLatest(undefined, strategy, asOfDateParam),
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

  // Per-committee insights (findings) for this review, grouped by symbol.
  const explain = useQuery({
    queryKey: queryKeys.committee.explain(reviewId ?? 'none'),
    queryFn: () => api.committee.getExplain(reviewId!),
    enabled: isAuthenticated && !!reviewId,
  });

  const findingsBySymbol = useMemo(() => {
    const map = new Map<string, CommitteeReviewFinding[]>();
    for (const review of explain.data?.committee_reviews ?? []) {
      const list = map.get(review.symbol) ?? [];
      list.push(review);
      map.set(review.symbol, list);
    }
    return map;
  }, [explain.data]);

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
    findingsBySymbol,
    strategy,
    selectedAsOfDate,
    setRecommendationAsOfDate,
    availableDates: datesQuery.data?.dates ?? [],
    latestDate,
    isLoading: latest.isLoading || packets.isLoading,
    isError: latest.isError || packets.isError,
    error: latest.error ?? packets.error,
    refetch: () =>
      Promise.all([latest.refetch(), packets.refetch(), report.refetch(), explain.refetch()]),
  };
}

export type { CommitteePacket };
