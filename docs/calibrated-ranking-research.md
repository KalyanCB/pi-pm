# Calibrated Ranking Research

## Final answer

**Can ranking calibration improve alpha and restore monotonic rank ordering?**

**Verdict: `PARTIAL`** — In-sample re-ranking improves rank↔return correlation and Sharpe slightly but does **not** materially lift 20d portfolio alpha (production 0.97% vs calibrated 0.97%). Monotonic rank curves remain inverted in ALL_REGIMES (breakout 20d: rank-1 α -0.51%, rank-20 α 2.13%; Spearman positive). Calibration is a research hypothesis, not production-ready.

## Architecture

Read-only pipeline over `ranking_results`, `ranking_performance_snapshots`, `ranking_validation_reports`. No production ranking writes.

```
scripts/generate_rank_reliability_reports.py
  → docs/rank-reliability-report.md
  → docs/regime-rank-reliability-report.md
  → docs/calibrated-ranking-research.md (+ backtest section)
```

Modules: `app/ranking_research/` (data_loader, rank_reliability, factor_reliability, calibration, backtest, reports).

## Proposed calibration (research-only)

### Layer 1 — Isotonic rank→expected return

Fit per (strategy, regime) isotonic regression: production rank → mean 20d alpha from historical runs. Replace displayed rank with calibrated expected-return order (does not change raw factor scores).

### Layer 2 — Regime-conditional weights

Current research blend (in-sample tables):

```
calibrated_score =
  1.0  * raw_rank_score
  + 0.15 * regime_reliability[regime][rank]
  + 0.10 * factor_reliability
  + 0.20 * historical_rank_reliability[rank]
```

### Layer 3 — Score shrinkage for overconfident quintiles

When score quintile Q1 underperforms Q3 at 20d, dampen top-score names toward median composite score before final sort.

## Backtest summary (historical runs, no prod ranker change)

Verdict `mixed`: Calibration passes some checks (e.g. Sharpe/monotonicity) but top-5 alpha or 20d alpha lift is weak — not ready for production promotion.

| Portfolio | 20d Alpha | Rank↔return ρ |
|-----------|-----------|---------------|
| production_top20 | 0.97% | 0.029 |
| calibrated_top20 | 0.97% | 0.022 |

| Criterion | Met |
|-----------|-----|
| Improved monotonicity (ρ) | ✓ |
| Better top-5 alpha (5d) | ✗ |
| Better top-10 alpha (10d) | ✓ |
| Better Sharpe (20d) | ✓ |

**Expected impact:** Modest monotonicity gain in portfolio ρ; alpha unchanged at 20d in this window. Material alpha lift would require out-of-sample isotonic tables and factor spread re-estimation per regime.

## Implementation phases (research script only)

| Phase | Deliverable | Prod merge? |
|-------|-------------|-------------|
| 1 | `generate_rank_reliability_reports.py` + reliability/regime docs | No |
| 2 | Walk-forward isotonic tables (`ranking_research/calibration.py`) | No |
| 3 | OOS backtest vs production top-N | No |
| 4 | Optional ranking v2 RFC after OOS pass | Separate PR |

## Linked reports

- [Rank reliability](docs/rank-reliability-report.md)
- [Regime rank reliability](docs/regime-rank-reliability-report.md)
- [Backtest detail](docs/calibrated-ranking-backtest.md)

## Recommendation: ranking v2?

**NO** for production promotion — backtest `mixed`, in-sample fit, weak 20d alpha lift.
Continue production ranker; iterate research calibration with walk-forward validation.
