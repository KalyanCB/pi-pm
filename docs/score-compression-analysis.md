# Score Compression Analysis

## Executive summary

Within-run composite score buckets for top-20 names. Tests whether tighter high scores (e.g. ≥0.97) outperform mid scores (e.g. 0.92–0.94).

## Scope

- Universe: `NIFTY_500`
- Strategies: breakout_v1, momentum_v1
- Date window: 2024-06-01 → 2026-06-04
- Ranking runs analyzed: 990
- Runs with 20d forward data: 950

## Score bucket curves (ALL_REGIMES)

### breakout_v1

#### Score buckets (5d) — breakout_v1

| Score bucket | Hit rate | Avg return | Alpha | Sharpe | Max DD | Obs |
|--------------|----------|------------|-------|--------|--------|-----|
| score_ge_0.97 | — | — | — | — | — | 0 |
| score_0.94_0.97 | — | — | — | — | — | 0 |
| score_0.92_0.94 | 20.00% | -3.34% | -3.90% | -5.765 | 12.95% | 5 |
| score_0.90_0.92 | 53.85% | 0.38% | -0.31% | 0.724 | 23.78% | 91 |
| score_lt_0.90 | 52.30% | 0.40% | 0.35% | 1.018 | 64.02% | 9701 |

#### Score buckets (10d) — breakout_v1

| Score bucket | Hit rate | Avg return | Alpha | Sharpe | Max DD | Obs |
|--------------|----------|------------|-------|--------|--------|-----|
| score_ge_0.97 | — | — | — | — | — | 0 |
| score_0.94_0.97 | — | — | — | — | — | 0 |
| score_0.92_0.94 | 40.00% | -1.38% | -2.63% | -3.067 | 6.55% | 5 |
| score_0.90_0.92 | 49.45% | 0.86% | -0.73% | 0.902 | 16.74% | 91 |
| score_lt_0.90 | 53.20% | 0.80% | 0.71% | 1.077 | 83.17% | 9601 |

#### Score buckets (20d) — breakout_v1

| Score bucket | Hit rate | Avg return | Alpha | Sharpe | Max DD | Obs |
|--------------|----------|------------|-------|--------|--------|-----|
| score_ge_0.97 | — | — | — | — | — | 0 |
| score_0.94_0.97 | — | — | — | — | — | 0 |
| score_0.92_0.94 | 20.00% | -5.83% | -7.85% | -2.469 | 22.34% | 5 |
| score_0.90_0.92 | 57.14% | 1.16% | -0.27% | 0.597 | 32.81% | 91 |
| score_lt_0.90 | 53.90% | 1.27% | 1.14% | 0.870 | 97.16% | 9401 |

#### Score buckets (60d) — breakout_v1

| Score bucket | Hit rate | Avg return | Alpha | Sharpe | Max DD | Obs |
|--------------|----------|------------|-------|--------|--------|-----|
| score_ge_0.97 | — | — | — | — | — | 0 |
| score_0.94_0.97 | — | — | — | — | — | 0 |
| score_0.92_0.94 | 80.00% | 6.13% | -4.18% | 2.090 | 0.16% | 5 |
| score_0.90_0.92 | 77.11% | 5.89% | -1.15% | 1.090 | 31.58% | 83 |
| score_lt_0.90 | 49.30% | 0.83% | 0.91% | 0.209 | 99.98% | 8625 |

### momentum_v1

#### Score buckets (5d) — momentum_v1

| Score bucket | Hit rate | Avg return | Alpha | Sharpe | Max DD | Obs |
|--------------|----------|------------|-------|--------|--------|-----|
| score_ge_0.97 | 50.26% | 0.42% | 0.41% | 0.443 | 87.56% | 756 |
| score_0.94_0.97 | 51.78% | 0.30% | 0.26% | 0.470 | 83.85% | 2194 |
| score_0.92_0.94 | 54.79% | 0.70% | 0.64% | 1.084 | 80.08% | 1827 |
| score_0.90_0.92 | 49.88% | 0.06% | 0.02% | 0.118 | 85.60% | 2103 |
| score_lt_0.90 | 50.87% | 0.25% | 0.19% | 0.530 | 64.19% | 2917 |

#### Score buckets (10d) — momentum_v1

| Score bucket | Hit rate | Avg return | Alpha | Sharpe | Max DD | Obs |
|--------------|----------|------------|-------|--------|--------|-----|
| score_ge_0.97 | 48.73% | 0.18% | 0.22% | 0.115 | 98.10% | 749 |
| score_0.94_0.97 | 52.25% | 0.51% | 0.43% | 0.403 | 95.92% | 2159 |
| score_0.92_0.94 | 56.13% | 1.19% | 1.09% | 0.954 | 95.47% | 1803 |
| score_0.90_0.92 | 49.44% | 0.40% | 0.32% | 0.369 | 97.20% | 2071 |
| score_lt_0.90 | 52.52% | 0.63% | 0.57% | 0.645 | 78.55% | 2915 |

#### Score buckets (20d) — momentum_v1

| Score bucket | Hit rate | Avg return | Alpha | Sharpe | Max DD | Obs |
|--------------|----------|------------|-------|--------|--------|-----|
| score_ge_0.97 | 47.59% | -1.07% | -1.13% | -0.343 | 99.96% | 727 |
| score_0.94_0.97 | 52.59% | 0.29% | 0.19% | 0.121 | 99.84% | 2082 |
| score_0.92_0.94 | 56.32% | 2.24% | 2.07% | 0.868 | 99.31% | 1763 |
| score_0.90_0.92 | 52.04% | 1.03% | 0.91% | 0.455 | 99.69% | 2012 |
| score_lt_0.90 | 51.98% | 0.86% | 0.86% | 0.454 | 97.69% | 2911 |

#### Score buckets (60d) — momentum_v1

| Score bucket | Hit rate | Avg return | Alpha | Sharpe | Max DD | Obs |
|--------------|----------|------------|-------|--------|--------|-----|
| score_ge_0.97 | 39.64% | -2.90% | -3.34% | -0.303 | 100.00% | 671 |
| score_0.94_0.97 | 45.74% | 0.43% | 0.54% | 0.057 | 100.00% | 1924 |
| score_0.92_0.94 | 49.19% | 2.27% | 2.32% | 0.358 | 99.99% | 1612 |
| score_0.90_0.92 | 47.67% | 1.78% | 1.83% | 0.248 | 100.00% | 1865 |
| score_lt_0.90 | 50.72% | 1.06% | 1.41% | 0.184 | 99.98% | 2642 |

- **0.97 vs 0.92–0.94 (20d):** ≥0.97 bucket underperforms 0.92–0.94 by 3.21% alpha.

## Methodology

Buckets: `score_ge_0.97` [0.97, 1.01), `score_0.94_0.97` [0.94, 0.97), `score_0.92_0.94` [0.92, 0.94), `score_0.90_0.92` [0.9, 0.92), `score_lt_0.90` [0.0, 0.9).
Metrics pooled across all top-20 observations in scope.
