# ADR-022: Recommendation Performance & Trust Framework (Phase 2 / P3)

**Status:** Accepted  
**Date:** 2026-06-05  
**Deciders:** Product Owner, Engineering Lead  
**Supersedes:** N/A — additive to ADR-021  
**Related:** [ADR-021](./ADR-021-Recommendation-Platform-Architecture.md), [PO_SIGNOFF_2026_06_04.md](../po/PO_SIGNOFF_2026_06_04.md), [16_RECOMMENDATION_PERFORMANCE_PRD.md](../product/16_RECOMMENDATION_PERFORMANCE_PRD.md), [17_TRUST_DASHBOARD_VISION.md](../product/17_TRUST_DASHBOARD_VISION.md)

---

## Context

The Recommendation Engine (P1–P2) produces deterministic BUY/WATCH/HOLD/EXIT_APPROVED/REJECT actions with conviction scores. However, without outcome tracking and retrospective analytics, there is no way to answer:

- **"Are recommendations actually working?"** (win rate, alpha vs NIFTY 500)
- **"Do HIGH conviction picks outperform MEDIUM?"** (conviction calibration)
- **"Is the regime gate adding value?"** (regime effectiveness)
- **"Is the ARGS committee advisory useful?"** (committee effectiveness)
- **"Should I trust the next BUY recommendation?"** (trust metrics)

These questions must be answerable before paper trading capital is deployed and before live investing is considered. A system that cannot measure its own recommendation quality cannot be trusted with real money.

---

## Decision

Implement a **Recommendation Performance & Trust Layer** as a pure analytics overlay:

1. **`RecommendationOutcome`** — extended entity tracking realized performance per closed recommendation (WIN/LOSS/BREAKEVEN/OPEN)
2. **`recommendation_analytics/` module** — deterministic, query-only calculators for all metrics
3. **Five analytics APIs** — summary, conviction, regime, committee, trust, symbol-level
4. **Trust metrics** — conviction calibration, stability, reliability — observation only, no feedback loop
5. **Mobile DTOs** — structured responses ready for mobile consumption

**Critical constraint (inherited from ADR-021):** Analytics are **observation only**. No metric, score, or trust signal feeds back into the conviction formula, recommendation engine, or ARGS committee logic. The measurement layer is read-only with respect to the generation layer.

---

## How Recommendation Performance Is Measured

### Data foundation

```
recommendation_results (action, conviction_band, conviction_score, reason_codes)
    ↓ 1:1
recommendation_outcomes (entry_price, exit_price, alpha_pct, outcome_status, target_hit, stop_hit)
    ↑ joins
recommendation_runs (strategy_name, as_of_date, regime_snapshot)
ranking_runs (regime_label)
research_runs / committee_reviews (advisory labels)
```

All metrics are computed from stored, immutable records. Same DB state → same analytics output (AC-RP-08).

### Core quality metrics (closed outcomes only)

| Metric | Formula |
|--------|---------|
| Win rate | `COUNT(WIN) / COUNT(closed)` |
| Average gain | `MEAN(alpha_pct) WHERE outcome_status = WIN` |
| Average loss | `MEAN(alpha_pct) WHERE outcome_status = LOSS` |
| Profit factor | `SUM(gains) / ABS(SUM(losses))` |
| Average alpha | `MEAN(alpha_pct)` over all closed |
| Median alpha | `MEDIAN(alpha_pct)` |
| Target hit rate | `COUNT(target_hit=true) / COUNT(closed)` |
| Stop hit rate | `COUNT(stop_hit=true) / COUNT(closed)` |

Window: configurable rolling session count (default 90 sessions).

---

## How Conviction Effectiveness Is Measured

Conviction bands at entry time (EXCEPTIONAL / HIGH / MEDIUM / LOW) are stored immutably on `recommendation_results`. Post-close, outcomes are grouped by band:

```
Band → [win_rate, avg_alpha, profit_factor, target_hit_rate]
```

**Calibration check:** If conviction is correctly calibrated, EXCEPTIONAL should outperform HIGH which should outperform MEDIUM. If this rank ordering does not hold in outcomes, the conviction formula needs PO-gated recalibration.

**Rule:** Conviction is never auto-adjusted from analytics. PO signs off on any weight change.

---

## How Regime Effectiveness Is Measured

Each `recommendation_run` stores a `regime_snapshot` (regime label + posture at execution time). Outcomes are grouped by regime at entry:

```
Regime label → [recommendation_count, win_rate, avg_alpha, avg_return]
```

This answers: "Do BULL_LOW_VOL entries outperform BEAR_HIGH_VOL entries?" and validates whether the regime gate (`defensive` → no BUY) is correctly conservative.

---

## How Committee Effectiveness Is Measured (Advisory — Post-Hoc Only)

ARGS committee labels (`supportive/neutral/cautious/HIGH_CONCERN`) are stored on `investment_review_packets` and `committee_reviews`. For outcomes where a committee review exists, we compare:

```
Committee advisory × Machine action → Outcome distribution
```

Example buckets:
- Machine BUY + Committee supportive → win rate
- Machine BUY + Committee cautious → win rate
- Machine BUY + Committee HIGH_CONCERN → win rate
- Committee cautious but human approved anyway → win rate

**Purpose:** Measure whether cautious/HIGH_CONCERN advisories are predictive of worse outcomes. This informs the PO whether committees add signal — but **does not** change how committees are run or how their output affects recommendations.

---

## How Trust Metrics Are Measured

Three dimensions:

### 1. Conviction Calibration
Expected: `EXCEPTIONAL win rate > HIGH win rate > MEDIUM win rate`  
Actual: computed from closed outcomes.  
Calibration score: rank-correlation of [EXCEPTIONAL, HIGH, MEDIUM, LOW] expected vs actual win rates.

### 2. Recommendation Stability
Measures churn: how often does the same symbol flip between BUY/WATCH/HOLD on consecutive days?  
High churn = low stability = lower trust in individual signals.  
Formula: `churn_rate = daily_action_changes / total_symbols_evaluated`

### 3. Recommendation Reliability
Measures data completeness at recommendation time:  
`reliability = COUNT(completed_validation) / COUNT(all_recommendations)`  
Low reliability = too many recommendations made on `insufficient_data` validation.

---

## Why Performance Tracking Is Required Before Paper Trading and Live Investing

| Gate | Requirement |
|------|------------|
| Paper trading (M2) | Must have `RecommendationOutcome` entity populated by fill events; no outcome model = no performance tracking |
| Exit policy calibration | Need outcome data to validate 15/20/30-day exit thresholds from exit research |
| Conviction weight adjustment | PO requires evidence from outcomes before any formula change |
| Live capital (M3+) | Win rate and alpha must demonstrate positive expectancy over ≥30 closed recommendations; no analytics = no green light |
| Mobile trust dashboard (M4) | Performance APIs must exist before mobile can render conviction calibration charts |

A system that cannot measure its recommendation quality cannot justify deploying real capital. The performance layer is the evidence foundation for all subsequent milestones.

---

## Consequences

### Positive
- Owner can objectively evaluate whether BUY recommendations are profitable
- PO has data-driven basis for conviction weight changes (gated)
- Committee advisory usefulness is measured, not assumed
- Regime effectiveness validates the defensive-posture gate

### Negative / Constraints
- Analytics are retrospective — require closed outcomes to be meaningful
- With no paper trading yet (M2 not started), outcomes must be manually recorded or seeded via scripts
- Committee effectiveness requires ARGS runs to have been performed and linked to outcomes

### Invariants preserved
- No analytics metric feeds back into conviction formula, recommendation engine, or committee logic
- All calculations are deterministic: same DB state → same output (AC-RP-08, AC-RP-09)
- No LLM involvement in any analytics computation (AC-RP-09)

---

## Implementation Scope (P3)

| Component | Location |
|-----------|----------|
| Extended outcome model + migration | `app/models/recommendation.py`, `migrations/versions/20260606_0020_*` |
| Analytics calculators | `app/recommendation_analytics/calculator.py` |
| Trust metrics | `app/recommendation_analytics/trust_metrics.py` |
| Mobile DTOs | `app/recommendation_analytics/dtos.py` |
| Outcome repository | `app/db/repositories/recommendation_outcome_repository.py` |
| Analytics service | `app/services/recommendation_analytics_service.py` |
| REST APIs | `app/api/v1/recommendation_analytics.py` |
| Tests | `tests/unit/recommendation_analytics/` |

---

## References

- [16_RECOMMENDATION_PERFORMANCE_PRD.md](../product/16_RECOMMENDATION_PERFORMANCE_PRD.md)
- [17_TRUST_DASHBOARD_VISION.md](../product/17_TRUST_DASHBOARD_VISION.md)
- [02_CONVICTION_SCORING_PRD.md](../product/02_CONVICTION_SCORING_PRD.md)
- [08_AI_INVESTMENT_COMMITTEE_PRD.md](../product/08_AI_INVESTMENT_COMMITTEE_PRD.md)
- [ADR-021-Recommendation-Platform-Architecture.md](./ADR-021-Recommendation-Platform-Architecture.md)
