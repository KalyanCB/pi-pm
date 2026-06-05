# Recommendation Performance — PRD (P3)

**Version:** Phase 2 / P3  
**Date:** 2026-06-05  
**Status:** Implemented  
**ADR:** [ADR-022](../architecture/ADR-022-Recommendation-Performance-Framework.md)

---

## 1. Purpose

Measure recommendation effectiveness over closed outcomes. Answers: **"Are Pi-PM recommendations working?"**

No metric feeds back into conviction, the recommendation engine, or ARGS committees.

---

## 2. Data model

### `recommendation_outcomes` (extended in migration 0020)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `recommendation_result_id` | UUID | FK — lineage to machine recommendation |
| `symbol` | varchar(32) | Denormalised for analytics |
| `strategy_name` | varchar(64) | Denormalised |
| `conviction_band` | varchar(16) | Band at entry time |
| `regime_label` | varchar(32) | Regime at recommendation time |
| `outcome_status` | varchar(16) | OPEN / WIN / LOSS / BREAKEVEN |
| `entry_date` | date | First fill date |
| `exit_date` | date | Flat date; null while open |
| `entry_price` | numeric(18,8) | Fill price |
| `exit_price` | numeric(18,8) | Exit fill |
| `days_held` | int | Trading sessions held |
| `pnl_pct` | numeric(10,4) | Raw P&L % |
| `max_gain_pct` | numeric(10,4) | Peak favorable excursion |
| `max_drawdown_pct` | numeric(10,4) | Peak adverse excursion |
| `benchmark_return_pct` | numeric(10,4) | NIFTY 500 return over same window |
| `alpha_pct` | numeric(10,4) | `pnl_pct - benchmark_return_pct` |
| `target_hit` | bool | Whether price target was reached |
| `stop_hit` | bool | Whether stop loss was triggered |
| `exit_reason` | varchar(64) | Human-readable exit description |
| `exit_reason_codes` | JSONB | Machine codes array |
| `committee_advisory` | varchar(32) | ARGS advisory at entry (display only) |

**Lineage chain:** `ranking_run → recommendation_run → recommendation_result → recommendation_approval → portfolio_position → recommendation_outcome`

---

## 3. Quality metrics

Computed over closed outcomes for a rolling window (default 90 sessions).

| Metric | Formula |
|--------|---------|
| Win rate | `COUNT(WIN) / COUNT(closed)` |
| Average gain | `MEAN(alpha_pct) WHERE WIN` |
| Average loss | `MEAN(alpha_pct) WHERE LOSS` |
| Profit factor | `SUM(gains) / ABS(SUM(losses))` |
| Average alpha | `MEAN(alpha_pct)` all closed |
| Median alpha | `MEDIAN(alpha_pct)` |
| Target hit rate | `COUNT(target_hit) / COUNT(closed)` |
| Stop hit rate | `COUNT(stop_hit) / COUNT(closed)` |
| Avg days held | `MEAN(days_held)` |

---

## 4. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC-RP-01 | Every CLOSED recommendation_result can have a RecommendationOutcome row |
| AC-RP-02 | System can calculate win rate from closed outcomes |
| AC-RP-03 | System can calculate alpha (pnl_pct - benchmark_return_pct) |
| AC-RP-08 | Same DB state → same analytics output (deterministic) |
| AC-RP-09 | No LLM involvement in any analytics calculation |

---

## 5. API

`GET /api/v1/analytics/recommendations/summary?strategy_name=&from_date=&to_date=`

Returns: quality metrics, top BUY candidates, EXIT_APPROVED candidates.
