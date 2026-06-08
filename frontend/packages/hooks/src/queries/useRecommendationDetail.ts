import { useQuery } from '@tanstack/react-query';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';
import { useAuthStore } from '../stores/authStore';
import { useUiStore } from '../stores/uiStore';
import { todayIsoDate } from '../utils/dates';
import { useActiveStrategy } from './useActiveStrategy';
import { useStockSymbolMap } from './useStocks';
import { useRecommendationDatesQuery } from './useRecommendations';

export function useRecommendationDetail(symbol: string, runId?: string) {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');
  const selectedAsOfDate = useUiStore((s) => s.recommendationAsOfDate);
  const datesQuery = useRecommendationDatesQuery();
  const asOfDate = selectedAsOfDate ?? datesQuery.data?.latest_date ?? todayIsoDate();
  // Strategy chosen dynamically from the regime of the viewed date.
  const { strategy } = useActiveStrategy(asOfDate);
  const { symbolMap } = useStockSymbolMap();

  const dailyQuery = useQuery({
    queryKey: queryKeys.recommendations.daily(asOfDate, undefined, strategy),
    queryFn: () => api.recommendations.getDaily({ asOfDate }),
    enabled: isAuthenticated && !runId,
  });

  const resolvedRunId =
    runId ??
    dailyQuery.data?.strategies.find((s) => s.strategy_name === strategy)?.recommendation_run_id ??
    dailyQuery.data?.strategies[0]?.recommendation_run_id;

  const detailQuery = useQuery({
    queryKey: queryKeys.recommendations.detail(resolvedRunId ?? 'none', symbol),
    queryFn: () => api.recommendations.getStockResult(resolvedRunId!, symbol),
    enabled: isAuthenticated && !!resolvedRunId && !!symbol,
  });

  const committeeQuery = useQuery({
    queryKey: queryKeys.committee.latest(undefined, strategy),
    queryFn: () => api.committee.getLatest(undefined, strategy),
    enabled: isAuthenticated,
  });

  const reviewId = committeeQuery.data?.run_id;
  const packetQuery = useQuery({
    queryKey: queryKeys.committee.packets(reviewId ?? 'none'),
    queryFn: () => api.committee.getPackets(reviewId!, symbol),
    enabled: isAuthenticated && !!reviewId,
  });

  const explainQuery = useQuery({
    queryKey: queryKeys.committee.explain(reviewId ?? 'none'),
    queryFn: () => api.committee.getExplain(reviewId!),
    enabled: isAuthenticated && !!reviewId,
  });

  const packet = packetQuery.data?.[0];
  const result = detailQuery.data;

  const stockId = result?.stock_id;
  const resolvedSymbol = stockId ? (symbolMap.get(stockId) ?? symbol) : symbol;

  // Per-committee findings for this symbol from the explain endpoint
  const committeeFindings = (explainQuery.data?.committee_reviews ?? []).filter(
    (r) => r.symbol === symbol || r.symbol === resolvedSymbol,
  );

  return {
    result,
    symbol: resolvedSymbol,
    runId: resolvedRunId,
    strategy,
    committeeAdvisory: packet?.payload.committee_advisory ?? null,
    committeeFindings,
    machineAction: packet?.payload.recommendation?.action,
    isLoading: detailQuery.isLoading || packetQuery.isLoading,
    isError: detailQuery.isError,
    error: detailQuery.error,
    refetch: () => Promise.all([detailQuery.refetch(), packetQuery.refetch(), explainQuery.refetch()]),
  };
}
