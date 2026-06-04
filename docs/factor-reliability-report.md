# Factor Reliability Report

## Executive summary

Top-20 `ranking_results.score_components` vs forward return sign/magnitude. Winners = at or above run median return; losers = below. Spread = winner mean normalized − loser mean normalized.

## Scope

- Universe: `NIFTY_500`
- Strategies: breakout_v1, momentum_v1
- Date window: 2024-06-01 → 2026-06-04
- Ranking runs analyzed: 990
- Runs with 20d forward data: 950

## Factor spreads by strategy and horizon (ALL_REGIMES)

### breakout_v1

#### breakout_v1 / ALL_REGIMES (5d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| relative_strength_acceleration | 0.860 | 0.864 | -0.004 | 4899 | 4898 |
| trend_quality | 0.941 | 0.945 | -0.003 | 4899 | 4898 |
| relative_strength | 0.942 | 0.945 | -0.003 | 4899 | 4898 |
| consolidation_breakout | 0.340 | 0.338 | 0.001 | 4899 | 4898 |
| high_proximity | 0.914 | 0.913 | 0.001 | 4899 | 4898 |
| volatility_adjusted_momentum | 0.946 | 0.947 | -0.001 | 4899 | 4898 |
| volume_surge | 0.842 | 0.842 | 0.001 | 4899 | 4898 |
| atr_expansion | 0.729 | 0.729 | 0.000 | 4899 | 4898 |

#### breakout_v1 / ALL_REGIMES (10d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| volume_surge | 0.839 | 0.845 | -0.006 | 4849 | 4848 |
| high_proximity | 0.915 | 0.912 | 0.003 | 4849 | 4848 |
| atr_expansion | 0.730 | 0.727 | 0.003 | 4849 | 4848 |
| volatility_adjusted_momentum | 0.945 | 0.948 | -0.003 | 4849 | 4848 |
| relative_strength | 0.942 | 0.944 | -0.002 | 4849 | 4848 |
| trend_quality | 0.942 | 0.944 | -0.002 | 4849 | 4848 |
| consolidation_breakout | 0.340 | 0.339 | 0.001 | 4849 | 4848 |
| relative_strength_acceleration | 0.862 | 0.862 | -0.000 | 4849 | 4848 |

#### breakout_v1 / ALL_REGIMES (20d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| volume_surge | 0.837 | 0.846 | -0.009 | 4749 | 4748 |
| consolidation_breakout | 0.344 | 0.340 | 0.005 | 4749 | 4748 |
| trend_quality | 0.940 | 0.945 | -0.005 | 4749 | 4748 |
| volatility_adjusted_momentum | 0.944 | 0.948 | -0.004 | 4749 | 4748 |
| relative_strength_acceleration | 0.862 | 0.859 | 0.003 | 4749 | 4748 |
| relative_strength | 0.942 | 0.945 | -0.003 | 4749 | 4748 |
| atr_expansion | 0.729 | 0.726 | 0.003 | 4749 | 4748 |
| high_proximity | 0.915 | 0.912 | 0.002 | 4749 | 4748 |

#### breakout_v1 / ALL_REGIMES (60d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| high_proximity | 0.918 | 0.908 | 0.010 | 4357 | 4356 |
| trend_quality | 0.938 | 0.946 | -0.008 | 4357 | 4356 |
| relative_strength | 0.939 | 0.946 | -0.007 | 4357 | 4356 |
| atr_expansion | 0.734 | 0.731 | 0.003 | 4357 | 4356 |
| volatility_adjusted_momentum | 0.944 | 0.947 | -0.003 | 4357 | 4356 |
| volume_surge | 0.841 | 0.844 | -0.003 | 4357 | 4356 |
| relative_strength_acceleration | 0.858 | 0.858 | -0.000 | 4357 | 4356 |
| consolidation_breakout | 0.332 | 0.332 | 0.000 | 4357 | 4356 |

### momentum_v1

#### momentum_v1 / ALL_REGIMES (5d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| volatility_adjusted_momentum | 0.941 | 0.938 | 0.002 | 4899 | 4898 |
| trend_quality | 0.941 | 0.943 | -0.001 | 4899 | 4898 |
| relative_strength | 0.943 | 0.944 | -0.001 | 4899 | 4898 |
| volume_expansion | 0.860 | 0.859 | 0.001 | 4899 | 4898 |

#### momentum_v1 / ALL_REGIMES (10d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| volatility_adjusted_momentum | 0.938 | 0.940 | -0.002 | 4849 | 4848 |
| relative_strength | 0.943 | 0.945 | -0.002 | 4849 | 4848 |
| volume_expansion | 0.860 | 0.859 | 0.002 | 4849 | 4848 |
| trend_quality | 0.942 | 0.942 | -0.001 | 4849 | 4848 |

#### momentum_v1 / ALL_REGIMES (20d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| trend_quality | 0.941 | 0.943 | -0.002 | 4748 | 4747 |
| relative_strength | 0.943 | 0.944 | -0.001 | 4748 | 4747 |
| volume_expansion | 0.858 | 0.859 | -0.001 | 4748 | 4747 |
| volatility_adjusted_momentum | 0.939 | 0.939 | -0.001 | 4748 | 4747 |

#### momentum_v1 / ALL_REGIMES (60d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| relative_strength | 0.940 | 0.947 | -0.007 | 4358 | 4356 |
| trend_quality | 0.939 | 0.945 | -0.005 | 4358 | 4356 |
| volume_expansion | 0.860 | 0.859 | 0.001 | 4358 | 4356 |
| volatility_adjusted_momentum | 0.938 | 0.939 | -0.000 | 4358 | 4356 |

## Regime-split factor spreads (20d)

#### breakout_v1 / BEAR_HIGH_VOL (20d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| consolidation_breakout | 0.420 | 0.467 | -0.048 | 270 | 270 |
| atr_expansion | 0.692 | 0.668 | 0.024 | 270 | 270 |
| trend_quality | 0.947 | 0.928 | 0.019 | 270 | 270 |
| high_proximity | 0.917 | 0.901 | 0.017 | 270 | 270 |
| relative_strength_acceleration | 0.870 | 0.858 | 0.013 | 270 | 270 |
| volatility_adjusted_momentum | 0.944 | 0.953 | -0.008 | 270 | 270 |
| volume_surge | 0.796 | 0.801 | -0.005 | 270 | 270 |
| relative_strength | 0.948 | 0.945 | 0.003 | 270 | 270 |

#### breakout_v1 / BEAR_LOW_VOL (20d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| consolidation_breakout | 0.505 | 0.446 | 0.060 | 1009 | 1008 |
| atr_expansion | 0.687 | 0.713 | -0.027 | 1009 | 1008 |
| volume_surge | 0.818 | 0.844 | -0.026 | 1009 | 1008 |
| trend_quality | 0.939 | 0.955 | -0.016 | 1009 | 1008 |
| relative_strength_acceleration | 0.847 | 0.833 | 0.014 | 1009 | 1008 |
| relative_strength | 0.946 | 0.952 | -0.006 | 1009 | 1008 |
| high_proximity | 0.943 | 0.937 | 0.006 | 1009 | 1008 |
| volatility_adjusted_momentum | 0.951 | 0.955 | -0.004 | 1009 | 1008 |

#### breakout_v1 / BULL_HIGH_VOL (20d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| consolidation_breakout | 0.208 | 0.284 | -0.075 | 280 | 280 |
| relative_strength_acceleration | 0.908 | 0.853 | 0.055 | 280 | 280 |
| atr_expansion | 0.790 | 0.736 | 0.054 | 280 | 280 |
| volume_surge | 0.853 | 0.806 | 0.047 | 280 | 280 |
| high_proximity | 0.860 | 0.888 | -0.028 | 280 | 280 |
| trend_quality | 0.933 | 0.915 | 0.018 | 280 | 280 |
| relative_strength | 0.940 | 0.930 | 0.010 | 280 | 280 |
| volatility_adjusted_momentum | 0.934 | 0.942 | -0.009 | 280 | 280 |

#### breakout_v1 / BULL_LOW_VOL (20d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| volume_surge | 0.844 | 0.853 | -0.009 | 3190 | 3190 |
| atr_expansion | 0.740 | 0.735 | 0.006 | 3190 | 3190 |
| relative_strength_acceleration | 0.863 | 0.868 | -0.006 | 3190 | 3190 |
| trend_quality | 0.941 | 0.946 | -0.005 | 3190 | 3190 |
| relative_strength | 0.940 | 0.943 | -0.003 | 3190 | 3190 |
| volatility_adjusted_momentum | 0.943 | 0.946 | -0.003 | 3190 | 3190 |
| high_proximity | 0.910 | 0.908 | 0.003 | 3190 | 3190 |
| consolidation_breakout | 0.299 | 0.300 | -0.002 | 3190 | 3190 |

#### momentum_v1 / BEAR_HIGH_VOL (20d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| trend_quality | 0.941 | 0.922 | 0.019 | 270 | 270 |
| volume_expansion | 0.830 | 0.843 | -0.013 | 270 | 270 |
| relative_strength | 0.944 | 0.936 | 0.008 | 270 | 270 |
| volatility_adjusted_momentum | 0.938 | 0.941 | -0.003 | 270 | 270 |

#### momentum_v1 / BEAR_LOW_VOL (20d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| trend_quality | 0.939 | 0.950 | -0.010 | 1008 | 1007 |
| relative_strength | 0.943 | 0.948 | -0.005 | 1008 | 1007 |
| volume_expansion | 0.863 | 0.859 | 0.004 | 1008 | 1007 |
| volatility_adjusted_momentum | 0.942 | 0.946 | -0.004 | 1008 | 1007 |

#### momentum_v1 / BULL_HIGH_VOL (20d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| trend_quality | 0.933 | 0.911 | 0.023 | 280 | 280 |
| volatility_adjusted_momentum | 0.923 | 0.938 | -0.015 | 280 | 280 |
| volume_expansion | 0.866 | 0.860 | 0.006 | 280 | 280 |
| relative_strength | 0.941 | 0.935 | 0.006 | 280 | 280 |

#### momentum_v1 / BULL_LOW_VOL (20d)

| Factor | Winner norm | Loser norm | Spread | Winners | Losers |
|--------|-------------|------------|--------|---------|--------|
| trend_quality | 0.942 | 0.945 | -0.004 | 3190 | 3190 |
| volume_expansion | 0.858 | 0.861 | -0.003 | 3190 | 3190 |
| volatility_adjusted_momentum | 0.939 | 0.937 | 0.002 | 3190 | 3190 |
| relative_strength | 0.943 | 0.945 | -0.002 | 3190 | 3190 |

## Methodology

1. Universe: top-20 picks per completed run.
2. Per run, median split on forward return at horizon.
3. Compare `score_components[factor].normalized` for winners vs losers.
4. Research only — no production factor weight changes.
