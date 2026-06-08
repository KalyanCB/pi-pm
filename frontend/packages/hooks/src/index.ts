export { AppProviders, useApi, queryClient } from './ApiProvider';
export { createQueryClient } from './queryClient';
export { queryKeys } from './queryKeys';
export { useAuthStore, mapRoles, type Role, type UserProfile } from './stores/authStore';
export { useUiStore } from './stores/uiStore';
export { useCopilotStore } from './stores/copilotStore';
export { AuthProvider, useAuth } from './auth/AuthProvider';
export { AuthGate } from './auth/AuthGate';
export { useDashboardQuery, useTrustQuery, useDashboard } from './queries/useDashboard';
export {
  useDailyRecommendationsQuery,
  useRecommendationCards,
  useRecommendationDatesQuery,
} from './queries/useRecommendations';
export type {
  RecommendationCardModel,
  RecommendationTabCounts,
} from './queries/useRecommendations';
export { useStocksQuery, useStockSymbolMap } from './queries/useStocks';
export { usePortfolioScreen } from './queries/usePortfolio';
export { useCommitteeScreen } from './queries/useCommittee';
export { useAskCopilot } from './mutations/useAskCopilot';
export {
  useApproveRecommendation,
  useRejectRecommendation,
  useConfirmExit,
  useRejectExit,
} from './mutations/useApproval';
export { useNavHistory, useNavHistoryQuery } from './queries/useNavHistory';
export {
  usePilotHealthQuery,
  usePilotRecommendationsQuery,
  useTrustDashboardQuery,
} from './queries/usePilotHealth';
export { useRecommendationDetail } from './queries/useRecommendationDetail';
export { useRegimeQuery } from './queries/useRegime';
export { useExitMonitorQuery } from './queries/useExitMonitor';
export { defaultStrategyName, todayIsoDate } from './utils/dates';
export { formatTrendRegime, formatVolRegime } from './utils/regime';
export type { SelectedRecommendation } from './stores/uiStore';
