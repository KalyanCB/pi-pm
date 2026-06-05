# Recommendation Performance — Product Requirements

**Version:** Phase 2.1 (PO sign-off 2026-06-04)  
**Date:** 2026-06-05  
**Foundation entity:** `RecommendationOutcome` ([03](./03_RECOMMENDATION_DATA_MODEL.md))

**Note:** Numbered **16** to avoid renumbering [11_HUMAN_IN_LOOP_EXECUTION_PRD.md](./11_HUMAN_IN_LOOP_EXECUTION_PRD.md).

---

## 1. Purpose

Measure **recommendation effectiveness** after positions close or while open — without feeding metrics back into conviction or recommendation generation (observation only).

Supports trust metrics, PO review, and [17_TRUST_DASHBOARD_VISION.md](./17_TRUST_DASHBOARD_VISION.md).

---

## 2. Data foundation

All metrics derive from `recommendation_outcomes` joined to `recommendation_results`, `ranking_runs`, and regime snapshots. See lifecycle closure in [04_RECOMMENDATION_LIFECYCLE.md](./04_RECOMMENDATION_LIFECYCLE.md) §11.

---

## 3. Recommendation quality metrics

Computed over closed outcomes (`outcome_status` ∈ WIN, LOSS, BREAKEVEN) for a rolling window (PO default: 90 sessions).

| Metric | Definition |
|--------|------------|
| **Win rate** | Count(WIN) / Count(closed) |
| **Average gain** | Mean `alpha_pct` where WIN |
| **Average loss** | Mean `alpha_pct` where LOSS (negative) |
| **Profit factor** | Sum(gains) / abs(Sum(losses)) |
| **Alpha** | Mean `alpha_pct` vs `benchmark_return_pct` |
| **Hit rate** | Count(`target_hit=true`) / Count(closed entries with target) |
| **Target achievement rate** | Same as hit rate (explicit target policy) |
| **Stop loss rate** | Count(`stop_hit=true`) / Count(closed) |

**Filters:** `strategy_name`, `universe_code`, date range, `conviction_band` at entry, regime at entry.

---

## 4. Conviction effectiveness

Compare realized outcomes **by band at entry** (from `recommendation_results.conviction_band` at CANDIDATE→ACTIVE):

| Band | Questions |
|------|-----------|
| `EXCEPTIONAL` | Win rate and alpha vs HIGH — justify priority queue |
| `HIGH` | Baseline BUY performance |
| `MEDIUM` | WATCH vs BUY spillover when slots open |
| `LOW` | Confirm near-zero BUY promotion |

**Output tables (product):**

- Band × win rate, avg gain, avg loss, profit factor
- Band × target_hit rate
- Calibration chart: predicted band order vs realized alpha deciles

**Critical:** Band at scoring time uses **deterministic conviction only** ([02](./02_CONVICTION_SCORING_PRD.md)) — never committee-adjusted.

---

## 5. Committee effectiveness (measure only)

Measure ARGS **advisory** labels post-hoc — **no influence** on recommendation generation.

| Advisory bucket | Measurement |
|-------------------|-------------|
| `APPROVE` | Outcome distribution when machine `BUY` and committee APPROVE |
| `WATCH` | Outcome when machine `WATCH` or committee WATCH on BUY |
| `REJECT` | Outcome when committee REJECT but human took BUY anyway (HITL override flag) |
| `HIGH_CONCERN` | Outcome when flag set ([08](./08_AI_INVESTMENT_COMMITTEE_PRD.md)) |

**Metrics:**

- Agreement rate: committee advisory vs machine action
- Conditional win rate when committee disagrees with machine
- Time-to-human-decision when `HIGH_CONCERN` present

**Forbidden:** Using these metrics as weights in conviction or recommendation rules.

---

## 6. Regime effectiveness

Bucket outcomes by **regime at entry** (from `recommendation_runs.regime_snapshot`):

| Regime bucket | PO labels |
|---------------|-----------|
| Bull / risk-on | “Bull” |
| Neutral | “Neutral” |
| Defensive | “Defensive” |
| Crisis | “Crisis” |

**Metrics per bucket:** win rate, alpha, avg days_held, EXIT_APPROVED rate, stop_hit rate.

Informs [05](./05_PORTFOLIO_ENGINE_PRD.md) slot table review — does not auto-change regime policy without PO gate.

---

## 7. APIs (proposed — P3)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/recommendations/performance/summary` | Quality metrics rollup |
| GET | `/api/v1/recommendations/performance/conviction` | Band effectiveness table |
| GET | `/api/v1/recommendations/performance/regime` | Regime effectiveness table |
| GET | `/api/v1/recommendations/performance/committee` | Advisory effectiveness (read-only) |

---

## 8. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC-RP-01 | Closed paper/live fills produce or update `recommendation_outcomes` |
| AC-RP-02 | Performance APIs reproducible from DB snapshot (no LLM) |
| AC-RP-03 | Committee effectiveness endpoint cannot be called from batch recommendation phase |
| AC-RP-04 | Conviction band report excludes any committee-derived fields |

---

## 9. Implementation priority

Part of **P3 — Recommendation Outcomes** in [13_PO_BACKLOG.md](./13_PO_BACKLOG.md) (after P1 domain + P2 engine).

---

## 10. References

- [03_RECOMMENDATION_DATA_MODEL.md](./03_RECOMMENDATION_DATA_MODEL.md)
- [17_TRUST_DASHBOARD_VISION.md](./17_TRUST_DASHBOARD_VISION.md)
- [PO_SIGNOFF_2026_06_04.md](./PO_SIGNOFF_2026_06_04.md)
- [outcome-attribution-report.md](../outcome-attribution-report.md)
