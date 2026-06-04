# Ranking Calibration Root Cause

## Executive summary (Phase 5 headlines)

### Why Top 20 works

- breakout_v1: top-20 avg 20d α 1.13% — pool selection adds value vs benchmark.
- momentum_v1: top-20 avg 20d α 0.83% — pool selection adds value vs benchmark.

### Why rank ordering fails

- breakout_v1: inverted Spearman(rank, α)=0.623 at 20d.
- breakout_v1: ranks 6–10 α 1.27% > ranks 1–5 0.51%.
- breakout_v1: ranks 11–20 (1.37%) > ranks 1–5 (0.51%).
- momentum_v1: inverted Spearman(rank, α)=0.376 at 20d.
- momentum_v1: ranks 6–10 α 1.13% > ranks 1–5 0.31%.
- momentum_v1: ranks 11–20 (0.93%) > ranks 1–5 (0.31%).

### Root causes

- breakout_v1: score compression — Q1 α 0.31% < Q5 2.03%.
- momentum_v1: score compression — Q1 α 0.15% < Q5 1.16%.
- breakout_v1: composite scores rarely exceed 0.97 — rank driven by factor blend, not fine score separation.
- momentum_v1: scores ≥0.97 underperform 0.92–0.94 by 3.21% 20d α.
- breakout_v1: factors anticorrelate with winners (volatility_adjusted_momentum, relative_strength, trend_quality).
- momentum_v1: factors anticorrelate with winners (volatility_adjusted_momentum, volume_expansion, trend_quality).

### Simplest fix (research-only)

- Research-only isotonic rank → expected 20d α per (strategy, regime).
- Shrink top-score quintile toward run median composite before sort.
- Walk-forward OOS validation before any ranking v2 promotion.

## Evidence links

- [Rank reliability](docs/rank-reliability-report.md)
- [Factor reliability](docs/factor-reliability-report.md)
- [Regime rank reliability](docs/regime-rank-reliability-report.md)
- [Score compression](docs/score-compression-analysis.md)

## Scope

- Runs: 990
- Window: 2024-06-01 → 2026-06-04
