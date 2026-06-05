# Recommendation Analytics — PRD (P3)

**Version:** Phase 2 / P3  
**Date:** 2026-06-05  
**Status:** Implemented  
**ADR:** [ADR-022](../architecture/ADR-022-Recommendation-Performance-Framework.md)

---

## 1. Purpose

Answer five questions deterministically using stored outcome data:

1. Are recommendations working? → `/summary`
2. Do conviction bands predict outcomes? → `/conviction`
3. Do recommendations behave differently by regime? → `/regime`
4. Is the ARGS committee adding advisory value? → `/committee`
5. Should I trust the next recommendation? → `/trust`
6. How has stock X performed across recommendations? → `/symbol/{symbol}`

---

## 2. Module structure

```
app/recommendation_analytics/
  __init__.py
  calculator.py          # Pure metric functions (no DB, no LLM)
  trust_metrics.py       # Calibration, stability, reliability
  dtos.py                # Mobile-ready response objects

app/services/
  recommendation_analytics_service.py   # Orchestration + DB queries

app/db/repositories/
  recommendation_outcome_repository.py  # Filtered outcome queries

app/api/v1/
  recommendation_analytics.py          # 6 REST endpoints
```

---

## 3. API contracts

| Method | Path | Query params | Returns |
|--------|------|--------------|---------|
| GET | `/analytics/recommendations/summary` | `strategy_name`, `from_date`, `to_date` | `RecommendationSummaryDTO` |
| GET | `/analytics/recommendations/conviction` | same | `ConvictionPerformanceDTO` |
| GET | `/analytics/recommendations/regime` | same | `RegimePerformanceDTO` |
| GET | `/analytics/recommendations/committee` | same | `CommitteePerformanceDTO` |
| GET | `/analytics/recommendations/trust` | same | `TrustMetricsDTO` |
| GET | `/analytics/recommendations/symbol/{symbol}` | `strategy_name` | `SymbolAnalyticsDTO` |

All responses are JSON. All calculations are deterministic.

---

## 4. Business rules

- Analytics only query outcomes where `outcome_status IN (WIN, LOSS, BREAKEVEN)` for rate calculations (OPEN excluded)
- Window default: all available outcomes (caller can filter by `from_date`/`to_date`)
- Strategy filter is optional; omitting returns cross-strategy aggregate
- Committee analytics are labelled with disclaimer: **advisory only**
- Calibration requires ≥2 bands with closed outcomes to produce a result

---

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC-RP-01 | Every CLOSED recommendation can produce a RecommendationOutcome |
| AC-RP-02 | System calculates win rate |
| AC-RP-03 | System calculates alpha |
| AC-RP-04 | System compares conviction bands |
| AC-RP-05 | System compares regimes |
| AC-RP-06 | System compares committee advisories |
| AC-RP-07 | Why-not-recommended is answerable through APIs |
| AC-RP-08 | Analytics are fully reproducible from stored data |
| AC-RP-09 | No LLM involvement in any analytics calculation |

---

## 6. Mobile DTOs

All DTOs in `app/recommendation_analytics/dtos.py` are dataclasses serialisable to JSON. Mobile layer (M4) consumes these directly without transformation.

Key DTOs:

- `RecommendationSummaryDTO`
- `ConvictionPerformanceDTO`
- `RegimePerformanceDTO`
- `CommitteePerformanceDTO`
- `TrustMetricsDTO`
- `SymbolAnalyticsDTO`

---

## 7. Follow-up (M2 dependency)

Committee effectiveness (`/committee`) currently uses `committee_advisory` stored on `recommendation_outcomes`. Until paper trading (M2) populates outcomes from approved fills, the committee analytics will have limited data. The framework is complete — data population is a M2 concern.
