# Sprint 8.3 / 8.5 — Implementation Summary

**Branch:** `feature/sprint-8.3-exit-research`  
**Date:** 2026-06-02  
**Status:** Ready for review

---

## 1. Architecture

### Sprint 8.3 — Exit Research (`app/workspace_exit_research/`)

Read-only research workspace that simulates exit policies on **top-decile signal entries** from validated ranking runs. No portfolio simulation, no execution changes, no modifications to ranking/validation/regime/factor logic.

**Flow:**

1. `SignalCohortLoader` loads completed ranking runs + performance snapshots in a date window.
2. Policy simulators evaluate fixed hold, rank deterioration, regime exit, trend failure, and alpha decay paths using cached bars/ranks/regimes (`BarForwardReturnIndex` for alpha decay).
3. `ExitMetricsEngine` aggregates hit rate, mean/median return, bootstrap CI; enforces `MIN_EXIT_SAMPLE_SIZE = 30`.
4. `build_policy_metric_buckets()` pre-indexes simulations before aggregation (replaces repeated full-cohort scans).
5. `ExitResearchService` runs phased backfill with batch commits; serves family reports and recommended policy.

**Run phases:** `collecting_entries` → `simulating` → `aggregating_metrics` → `persisting_policy_metrics` → `persisting_alpha_decay` → `finalizing` → `completed` / `failed`.

### Sprint 8.5 — Research Intelligence (`app/workspace_research_reporting/`)

Committee-grade reporting from existing validation, ranking, and factor analytics outputs.

**Reports:** coverage statistics, ranking statistics, IC/spread by strategy and regime, factor contribution analysis, top 20 candidates, executive committee summary with data-driven conclusions.

---

## 2. Schema

| Migration | Tables / columns |
|-----------|------------------|
| `20260603_0011_sprint83_exit_research` | `exit_research_runs`, `exit_research_policy_metrics`, `exit_research_alpha_decay_points` |
| `20260604_0012_sprint85_research_intelligence` | `research_intelligence_runs`, `research_intelligence_reports` |
| `20260605_0013_sprint83_exit_research_progress` | `total_entries`, `processed_entries`, `percent_complete`, `last_progress_at`, `elapsed_seconds` on runs |
| `20260606_0014_sprint83_exit_research_phases` | `current_phase`, `persistence_items_total`, `persistence_items_processed` on runs |

---

## 3. APIs

### Exit Research — `/api/v1/analytics/exit`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/backfill` | Run exit policy simulation backfill |
| GET | `/runs` | List backfill runs (includes `current_phase`, persistence counters) |
| GET | `/reports/exit-policy-comparison` | Exit policy comparison |
| GET | `/reports/alpha-decay` | Alpha decay report |
| GET | `/reports/rank-deterioration` | Rank deterioration report |
| GET | `/reports/regime-transition` | Regime exit report |
| GET | `/reports/trend-failure` | Trend failure report |
| GET | `/reports/recommended-exit-policy` | Recommended exit policy |

### Research Intelligence — `/api/v1/analytics/research-intelligence`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate` | Generate full report pack (optional persist) |
| GET | `/runs` | List generation runs |
| GET | `/reports/executive-summary` | Executive committee summary |
| GET | `/reports/coverage` | Coverage statistics |
| GET | `/reports/ic-by-strategy` | IC by strategy |
| GET | `/reports/top-20` | Current top 20 candidates |

---

## 4. Backfill Scripts

```bash
alembic upgrade head   # through 20260606_0014

# Exit research (per strategy/window)
python scripts/backfill_sprint83_exit_research.py \
  --universe-code NIFTY_500 \
  --start-date 2024-01-01 \
  --end-date 2025-05-30

# Executive research intelligence pack
python scripts/generate_sprint85_research_intelligence.py \
  --universe-code NIFTY_500 \
  --start-date 2024-01-01 \
  --end-date 2025-05-30
```

**Operational notes:** Simulation percent is capped at 90% until finalization. Persistence drives 90%→100%. Policy and alpha rows commit every `PERSIST_COMMIT_INTERVAL` (25) upserts. See `docs/sprint83-backfill-performance.md`.

---

## 5. Policy Families Evaluated

| Family | Variants |
|--------|----------|
| Fixed hold | 5, 10, 15, 20, 30, 40, 60 days |
| Rank deterioration | exit rank > 50, 60, 70, 80, 90 |
| Regime exit | immediate, delay 3, delay 5, never |
| Trend failure | DMA20, DMA50, breakout failure, ATR trailing stop |
| Alpha decay | forward returns days 1–60 (curve in `exit_research_alpha_decay_points`) |

All aggregate policy reports include strategy, regime, horizon, sample size, hit rate, mean/median return, and confidence interval where sample size ≥ 30.

---

## 6. Tests

| Area | Location |
|------|----------|
| Simulators, Decimal safety, forward-return index | `tests/unit/workspace_exit_research/` |
| Phase transitions, batch commits, aggregation index | `tests/unit/services/test_exit_research_phases.py` |
| API smoke | `tests/integration/api/test_exit_and_research_api.py` |

Full suite: **212 tests passing**.

---

## 7. Explicit Non-Modifications

- `app/ranking/**`
- `app/validation/**`
- `app/regime_policy/**`
- `app/factor_analytics/**` (read-only consumption only)

Portfolio construction research remains deferred until exit research identifies optimal holding-period and exit framework.

---

## Related Documentation

- `docs/sprint83-exit-research-design.md` — original design (reference; some schema paths differ from implementation)
- `docs/sprint83-backfill-performance.md` — performance, phases, monitoring
- `docs/API_REFERENCE.md` — endpoint catalog
