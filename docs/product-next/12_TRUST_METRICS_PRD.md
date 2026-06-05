# Trust Metrics — PRD (P3)

**Version:** Phase 2 / P3  
**Date:** 2026-06-05  
**Status:** Implemented  
**ADR:** [ADR-022](../architecture/ADR-022-Recommendation-Performance-Framework.md)

---

## 1. Purpose

Give the owner a transparent, evidence-based answer to: **"Should I trust the next recommendation?"**

Three dimensions. All observation-only — no feedback into conviction or engine.

---

## 2. Conviction Calibration

**Question:** Do HIGH conviction picks actually outperform MEDIUM?

**Method:** Group closed outcomes by `conviction_band` at entry. Compute win rate per band. Check rank order: EXCEPTIONAL > HIGH > MEDIUM > LOW.

**Calibration score:** Spearman rank correlation of expected band order vs actual win-rate order. `ρ ≥ 0.6` → calibrated.

**Action if not calibrated:** PO reviews conviction weights. No auto-adjustment.

---

## 3. Recommendation Stability

**Question:** How much do recommendations churn day-to-day?

**Metrics:**

| Metric | Formula |
|--------|---------|
| Churn rate | `daily_action_changes / total_evaluations` |
| Stability score | `1 - churn_rate` |
| Reversal count | BUY → WATCH/REJECT → BUY within 3 sessions |

High churn = signals are noisy. Ideal stability score ≥ 0.80.

---

## 4. Recommendation Reliability

**Question:** How often are recommendations made on complete data?

**Metric:** `COUNT(completed_validation) / COUNT(all_recommendations)`

Low reliability = too many recommendations made on `insufficient_data` validation. Target ≥ 0.85.

---

## 5. Overall Trust Score

Simple composite (0–1) of the three normalised dimensions:

```
trust = mean([
  (rank_correlation + 1) / 2,   # -1..1 → 0..1
  stability_score,
  reliability_rate,
])
```

---

## 6. API

`GET /api/v1/analytics/recommendations/trust?strategy_name=&from_date=&to_date=`

---

## 7. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC-RP-04 | System compares conviction band win rates |
| AC-RP-08 | Trust score is deterministic from DB state |
| AC-RP-09 | No LLM in trust computation |
