# Calibrated Ranking Backtest

## Executive summary

**Verdict:** `mixed` — Calibration passes some checks (e.g. Sharpe/monotonicity) but top-5 alpha or 20d alpha lift is weak — not ready for production promotion.

## Scope

- Universe: `NIFTY_500`
- Strategies: breakout_v1, momentum_v1
- Date window: 2024-06-01 → 2026-06-03
- Runs: 988

## Comparison: production Top 20 vs research calibrated Top 20

| Portfolio | Horizon | Hit rate | Avg return | Alpha | Sharpe | Max DD | Rank↔return ρ | Runs |
|-----------|---------|----------|------------|-------|--------|--------|---------------|------|
| production_top20 | 5d | 51.92% | 0.35% | 0.29% | 0.874 | 90.62% | 0.007 | 980 |
| calibrated_top20 | 5d | 51.90% | 0.35% | 0.29% | 0.872 | 90.60% | 0.004 | 980 |
| production_top20 | 10d | 52.67% | 0.72% | 0.62% | 0.911 | 98.81% | 0.012 | 970 |
| calibrated_top20 | 10d | 52.67% | 0.72% | 0.63% | 0.915 | 98.78% | 0.009 | 970 |
| production_top20 | 20d | 53.25% | 1.11% | 0.97% | 0.710 | 99.98% | 0.029 | 950 |
| calibrated_top20 | 20d | 53.25% | 1.11% | 0.97% | 0.712 | 99.98% | 0.022 | 950 |
| production_top20 | 60d | 48.71% | 0.77% | 0.81% | 0.182 | 100.00% | 0.040 | 872 |
| calibrated_top20 | 60d | 48.75% | 0.77% | 0.82% | 0.183 | 100.00% | 0.038 | 872 |

## Success criteria

| Criterion | Met |
|-----------|-----|
| Improved monotonicity (more negative Spearman at 20d) | ✓ |
| Better top-5 alpha (5d) | ✗ |
| Better top-10 alpha (10d) | ✓ |
| Better Sharpe (20d) | ✓ |

## Calibration weights (research only)

- raw_score: 1.0
- regime_reliability: 0.15
- factor_reliability: 0.1
- historical_rank_reliability: 0.2
