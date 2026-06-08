import { useRegimeQuery } from './useRegime';
import { strategyForRegime } from '../utils/regimeStrategy';

/**
 * The ranking strategy to use for a given date, chosen dynamically from that
 * date's market regime (e.g. BEAR_LOW_VOL → reversal_v1). Until the regime
 * loads — or when the regime has no mapping — it falls back to the static
 * default (`defaultStrategyName`).
 */
export function useActiveStrategy(asOfDate?: string) {
  const regimeQuery = useRegimeQuery(asOfDate);
  return {
    strategy: strategyForRegime(regimeQuery.data),
    regime: regimeQuery.data ?? null,
    isLoading: regimeQuery.isLoading,
  };
}
