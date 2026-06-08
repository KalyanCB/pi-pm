import type { RegimeCurrent } from '@pipm/types';
import { defaultStrategyName } from './dates';

/**
 * Regime → ranking-strategy mapping.
 *
 * Grounded in each strategy's documented design regime (see the strategy
 * module docstrings + context/canonical/design/VALIDATION_DESIGN.md):
 *   - breakout_v1 — 20d alpha concentrated in BULL_LOW_VOL
 *   - momentum_v1 — platform default trend-follower (bull / high-vol bull)
 *   - reversal_v1 — "Designed for BEAR_LOW_VOL regime"
 *   - low_vol_v1  — defensive; for bear regimes where momentum/breakout invert
 *
 * Keyed on the regime_label ("<TREND>_<VOL>"). Adjust here to change policy.
 */
export const REGIME_STRATEGY_MAP: Record<string, string> = {
  BULL_LOW_VOL: 'breakout_v1',
  BULL_HIGH_VOL: 'momentum_v1',
  BEAR_LOW_VOL: 'reversal_v1',
  BEAR_HIGH_VOL: 'low_vol_v1',
};

type RegimeLike = Pick<RegimeCurrent, 'trend_regime' | 'vol_regime' | 'regime_label'>;

/** Normalised "<TREND>_<VOL>" label, or null when regime is unknown. */
export function regimeLabel(regime?: RegimeLike | null): string | null {
  if (!regime) return null;
  if (regime.regime_label) return regime.regime_label.toUpperCase();
  if (regime.trend_regime && regime.vol_regime) {
    return `${regime.trend_regime}_${regime.vol_regime}`.toUpperCase();
  }
  return null;
}

/**
 * Pick the ranking strategy for a regime. Falls back to the static default
 * (env `EXPO_PUBLIC_DEFAULT_STRATEGY`) when the regime is unknown/unmapped.
 */
export function strategyForRegime(regime?: RegimeLike | null): string {
  const label = regimeLabel(regime);
  return (label && REGIME_STRATEGY_MAP[label]) || defaultStrategyName();
}
