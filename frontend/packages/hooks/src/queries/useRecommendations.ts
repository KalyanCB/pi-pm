import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type {
  CommitteeAdvisoryOverlay,
  CommitteeReviewFinding,
  RecommendationExecutionContext,
  RecommendationResultRead,
} from '@pipm/types';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';
import { useAuthStore } from '../stores/authStore';
import { useUiStore } from '../stores/uiStore';
import { defaultStrategyName, todayIsoDate } from '../utils/dates';
import { useActiveStrategy } from './useActiveStrategy';
import { useStockSymbolMap } from './useStocks';

export interface RecommendationTabCounts {
  BUY: number;
  WATCH: number;
  EXIT_APPROVED: number;
}

export interface RecommendationCardModel {
  id: string;
  symbol: string;
  action: RecommendationResultRead['action'];
  rank: number | null;
  convictionScore: number;
  convictionBand: RecommendationResultRead['conviction_band'];
  reasonCodes: string[];
  committeeAdvisory: CommitteeAdvisoryOverlay | null;
  committeeFindings: CommitteeReviewFinding[];
  runId: string;
  lifecycleState: string | null;
  execution: RecommendationExecutionContext | null;
}

function pickStrategyResults(
  strategies: {
    strategy_name: string;
    recommendation_run_id: string;
    results: RecommendationResultRead[];
    execution_context?: Record<string, RecommendationExecutionContext>;
  }[],
  strategyName: string,
) {
  const match = strategies.find((s) => s.strategy_name === strategyName);
  return match ?? strategies[0] ?? null;
}

export function useRecommendationDatesQuery() {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');
  const strategy = defaultStrategyName();

  return useQuery({
    queryKey: queryKeys.recommendations.dates(strategy),
    queryFn: () => api.recommendations.getDates(strategy),
    enabled: isAuthenticated,
    staleTime: 60_000,
  });
}

export function useDailyRecommendationsQuery(
  asOfDate: string,
  action?: string,
  enabled = true,
) {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');
  const strategy = defaultStrategyName();

  return useQuery({
    queryKey: queryKeys.recommendations.daily(asOfDate, action, strategy),
    queryFn: () => api.recommendations.getDaily({ asOfDate, action }),
    enabled: enabled && isAuthenticated && !!asOfDate,
  });
}

export function useRecommendationCards() {
  const api = useApi();
  const tab = useUiStore((s) => s.recommendationTab);
  const selectedAsOfDate = useUiStore((s) => s.recommendationAsOfDate);
  const setRecommendationAsOfDate = useUiStore((s) => s.setRecommendationAsOfDate);
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');
  const { symbolMap, isLoading: stocksLoading } = useStockSymbolMap();

  const datesQuery = useRecommendationDatesQuery();
  const latestDate = datesQuery.data?.latest_date ?? null;
  const queryAsOfDate = selectedAsOfDate ?? latestDate ?? todayIsoDate();
  const isViewingLatest = !selectedAsOfDate || selectedAsOfDate === latestDate;

  // Strategy is chosen dynamically from the regime of the viewed date.
  const { strategy } = useActiveStrategy(queryAsOfDate);

  const dailyQuery = useDailyRecommendationsQuery(queryAsOfDate, undefined, true);

  const strategyBlock = dailyQuery.data
    ? pickStrategyResults(dailyQuery.data.strategies, strategy)
    : null;

  const committeeQuery = useQuery({
    queryKey: queryKeys.committee.latest(undefined, strategy),
    queryFn: () => api.committee.getLatest(undefined, strategy),
    enabled: isAuthenticated && isViewingLatest,
  });

  const reviewId = committeeQuery.data?.run_id;
  const packetsQuery = useQuery({
    queryKey: queryKeys.committee.packets(reviewId ?? 'none'),
    queryFn: () => api.committee.getPackets(reviewId!),
    enabled: isAuthenticated && isViewingLatest && !!reviewId,
  });

  const advisoryBySymbol = useMemo(() => {
    const map = new Map<string, CommitteeAdvisoryOverlay>();
    for (const packet of packetsQuery.data ?? []) {
      const advisory = packet.payload.committee_advisory;
      if (advisory) map.set(packet.symbol, advisory);
    }
    return map;
  }, [packetsQuery.data]);

  // Per-committee findings (insights) for the latest review, grouped by symbol.
  const explainQuery = useQuery({
    queryKey: queryKeys.committee.explain(reviewId ?? 'none'),
    queryFn: () => api.committee.getExplain(reviewId!),
    enabled: isAuthenticated && isViewingLatest && !!reviewId,
  });

  const findingsBySymbol = useMemo(() => {
    const map = new Map<string, CommitteeReviewFinding[]>();
    for (const review of explainQuery.data?.committee_reviews ?? []) {
      const list = map.get(review.symbol) ?? [];
      list.push(review);
      map.set(review.symbol, list);
    }
    return map;
  }, [explainQuery.data]);

  const tabCounts = useMemo((): RecommendationTabCounts => {
    const results = strategyBlock?.results ?? [];
    return {
      BUY: results.filter((r) => r.action === 'BUY').length,
      WATCH: results.filter((r) => r.action === 'WATCH').length,
      EXIT_APPROVED: results.filter((r) => r.action === 'EXIT_APPROVED').length,
    };
  }, [strategyBlock]);

  const cards = useMemo((): RecommendationCardModel[] => {
    const tabAction = tab === 'EXIT_APPROVED' ? 'EXIT_APPROVED' : tab;
    const results = strategyBlock?.results.filter((r) => r.action === tabAction) ?? [];
    const ctxMap = strategyBlock?.execution_context ?? {};

    return results.map((r) => {
      const symbol = symbolMap.get(r.stock_id) ?? r.stock_id.slice(0, 8);
      const execution = ctxMap[r.id] ?? ctxMap[String(r.id)] ?? null;
      return {
        id: r.id,
        symbol,
        action: r.action,
        rank: r.rank,
        convictionScore: r.conviction_score,
        convictionBand: r.conviction_band,
        reasonCodes: r.reason_codes,
        committeeAdvisory: advisoryBySymbol.get(symbol) ?? null,
        committeeFindings: findingsBySymbol.get(symbol) ?? [],
        runId: r.recommendation_run_id,
        lifecycleState: r.lifecycle_state,
        execution,
      };
    });
  }, [tab, strategyBlock, symbolMap, advisoryBySymbol, findingsBySymbol]);

  const isLoading =
    stocksLoading ||
    datesQuery.isLoading ||
    dailyQuery.isLoading ||
    (isViewingLatest && (committeeQuery.isLoading || packetsQuery.isLoading));

  const isError = dailyQuery.isError || datesQuery.isError;

  return {
    cards,
    tabCounts,
    strategy,
    asOfDate: dailyQuery.data?.as_of_date ?? queryAsOfDate,
    availableDates: datesQuery.data?.dates ?? [],
    latestDate,
    selectedAsOfDate,
    setRecommendationAsOfDate,
    tab,
    isLoading,
    isError,
    error: dailyQuery.error ?? datesQuery.error,
    refetch: () =>
      Promise.all([
        datesQuery.refetch(),
        dailyQuery.refetch(),
        committeeQuery.refetch(),
        packetsQuery.refetch(),
        explainQuery.refetch(),
      ]),
  };
}
