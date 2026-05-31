# Sprint 8.1 Results Template — Regime-Aware Trading

Use this template when documenting E1–E4 backtest results for `breakout_v1`.

---

## Hypothesis

Regime-aware gating improves risk-adjusted performance by avoiding negative-alpha regimes outside `BULL_LOW_VOL`.

---

## Data Used

| Field | Value |
|-------|-------|
| Strategy | `breakout_v1` v1.0.0 |
| Universe | |
| Date range | |
| Holdout start | `2025-01-01` |
| Horizon | 20 days |
| Validation reports used | |
| Source tables | `ranking_runs`, `ranking_validation_reports`, `ranking_performance_snapshots` |

---

## Methodology

- Replay overlay (no reranking, no factor recompute)
- Regime from validation report at signal date (no lookahead)
- Policies tested: E1 Baseline, E2 Hard Gate, E3 Soft Gate, E4 Threshold Gate
- Train period: before holdout start
- Holdout period: from holdout start to end date
- Significance: bootstrap 95% CI, paired spread comparison vs E1

---

## Training Results

| Policy | IC | Spread | Hit Rate | Drawdown | Sample Count | Days Included |
|--------|-----|--------|----------|----------|--------------|---------------|
| E1 | | | | | | |
| E2 | | | | | | |
| E3 | | | | | | |
| E4 | | | | | | |

---

## Holdout Results

| Policy | IC | Spread | Hit Rate | Drawdown | Sample Count | Days Included |
|--------|-----|--------|----------|----------|--------------|---------------|
| E1 | | | | | | |
| E2 | | | | | | |
| E3 | | | | | | |
| E4 | | | | | | |

---

## Statistical Significance

| Comparison | Spread Δ | 95% CI Lower | 95% CI Upper | p-value | Significant? |
|------------|----------|--------------|--------------|---------|--------------|
| E2 vs E1 | | | | | |
| E3 vs E1 | | | | | |
| E4 vs E1 | | | | | |

---

## Risks

- [ ] Sparse regime cells (e.g. BEAR_HIGH_VOL n < 30)
- [ ] Regime label instability at transitions
- [ ] E4 low sample count (top decile filter)
- [ ] Overfitting to 2024 train period
- [ ] Survivorship / universe membership effects

---

## Recommendation

**Best policy on holdout:**

**Research findings summary:**

```json
{
  "policy": "",
  "baseline_spread": null,
  "policy_spread": null,
  "improvement": null,
  "sample_count": null,
  "confidence": "",
  "recommendation": "",
  "is_statistically_significant": false
}
```

---

## Go / No-Go Decision

| Decision | Criteria met? | Notes |
|----------|---------------|-------|
| Promote to Sprint 8.2 factor analytics | | |
| Promote E2/E3 to next research stage | E2 or E3 beats E1 on holdout with significance | |
| Reject E4 for production consideration | | |
| No live integration in Sprint 8.1 | Always yes | Research only |

**Final decision:** GO / NO-GO / DEFER

**Signed off by:** _______________ **Date:** _______________
