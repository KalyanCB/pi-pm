# Sprint 8.2 — Factor Predictive Power Analytics

**Status:** Implementation complete (awaiting review)  
**Branch:** `feature/sprint82-factor-ic-analytics`  
**Migration:** `20260601_0009`

---

## Mission

Read-only analytics layer answering:

> Which factors generate positive edge in BULL_LOW_VOL, and do they remain predictive on holdout?

**Out of scope:** ranking, validation, regime classification, factor weights, trading.

---

## Architecture

```
ranking_factor_contributions ──┐
ranking_performance_snapshots ─┼──► FactorObservationLoader
ranking_validation_reports ────┘         │
                                           ▼
                              FactorMetricsEngine (IC, bootstrap, stability, coverage)
                                           │
                     ┌─────────────────────┼─────────────────────┐
                     ▼                     ▼                     ▼
          factor_daily_metrics   factor_performance_metrics   factor_performance_runs
                     │                     │
                     └──────────► FactorPredictivePowerService ◄── reports builders
                                           │
                                           ▼
                              /api/v1/analytics/factors/*
```

### Package layout

| Path | Role |
|------|------|
| `app/factor_analytics/constants.py` | Horizons, splits, thresholds, bootstrap params |
| `app/factor_analytics/window.py` | Train/holdout split helpers |
| `app/factor_analytics/observation_loader.py` | Join traceability + snapshots + regime; percentile ranks |
| `app/factor_analytics/metrics_engine.py` | IC, hit rate, spread, stability, coverage, bootstrap |
| `app/factor_analytics/weight_resolver.py` | `resolve_factor_weights()` metadata → registry |
| `app/factor_analytics/reports.py` | Leaderboard, regime matrix, horizon stability, drift |
| `app/services/factor_predictive_power_service.py` | Backfill + query orchestration |
| `app/api/v1/factor_analytics.py` | REST endpoints |

---

## Enhancements (A–H)

| ID | Feature | Notes |
|----|---------|-------|
| A | Train/holdout splits | `ALL`, `TRAIN`, `HOLDOUT`; default boundary `2025-01-01` |
| B | Regime coverage | `regime_coverage_pct`, labels sparse/low/adequate |
| C | Stability score | Positive daily IC days / total daily IC days |
| D | Daily metrics table | `factor_daily_metrics`; not exposed via API in 8.2 |
| E | Weight resolution | `ranking_runs.metadata.effective_weights` first |
| F | Bootstrap audit | `bootstrap_sample_count`, `bootstrap_method` persisted |
| G | Factor percentile | Computed in loader; internal model field only |
| H | ALL regime rollup | `regime_label = ALL` aggregate rows |

---

## Backfill

```bash
# Apply migration
alembic upgrade head

# Full NIFTY_500 history (adjust dates to validated ranking window)
python scripts/backfill_sprint82_factor_analytics.py \
  --universe-code NIFTY_500 \
  --start-date 2023-01-01 \
  --end-date 2025-05-30 \
  --holdout-start-date 2025-01-01

# Or via API
curl -X POST http://localhost:8000/api/v1/analytics/factors/backfill \
  -H 'Content-Type: application/json' \
  -d '{
    "universe_code": "NIFTY_500",
    "start_date": "2023-01-01",
    "end_date": "2025-05-30",
    "holdout_start_date": "2025-01-01"
  }'
```

**Prerequisites:** Completed ranking runs with factor contributions, performance snapshots, and validation reports in the date window.

---

## Verification SQL

```sql
-- Aggregate metrics by split
SELECT dataset_split, regime_label, COUNT(*)
FROM factor_performance_metrics
WHERE universe_code = 'NIFTY_500'
GROUP BY 1, 2
ORDER BY 1, 2;

-- Daily metrics populated
SELECT COUNT(*) FROM factor_daily_metrics WHERE universe_code = 'NIFTY_500';

-- BULL_LOW_VOL holdout leaderboard source
SELECT factor_name, ic_spearman, stability_score, regime_coverage_pct
FROM factor_performance_metrics
WHERE regime_label = 'BULL_LOW_VOL'
  AND dataset_split = 'HOLDOUT'
  AND horizon = 20
ORDER BY ic_spearman DESC NULLS LAST;
```

---

## Related

- `docs/sprint82-implementation-summary.md` — PR review package
- `docs/sprint82-factor-ic-results-template.md` — post-backfill findings template
- ADR-021 in `docs/DECISION_LOG.md` — Sprint 8.2.1 interaction analysis (design only)
