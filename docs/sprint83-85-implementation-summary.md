# Sprint 8.3 / 8.5 — Implementation Summary

**Branch:** `feature/sprint-8.3-exit-research`  
**Date:** 2026-05-31  
**Status:** Ready for review

---

## 1. Architecture

### Sprint 8.3 — Exit Research (`app/workspace_exit_research/`)

Read-only research workspace that simulates exit policies on **top-decile signal entries** from validated ranking runs. No portfolio simulation, no execution changes, no modifications to ranking/validation/regime/factor logic.

**Flow:**

1. `SignalCohortLoader` loads completed ranking runs + performance snapshots in a date window.
2. Policy simulators evaluate fixed hold, rank deterioration, regime exit, trend failure, and alpha decay paths using cached bars/ranks/regimes.
3. `ExitMetricsEngine` aggregates hit rate, mean/median return, bootstrap CI; enforces `MIN_EXIT_SAMPLE_SIZE = 30`.
4. `ExitResearchService` persists runs and metrics; serves family reports and recommended policy.

### Sprint 8.5 — Research Intelligence (`app/workspace_research_reporting/`)

Committee-grade reporting from existing validation, ranking, and factor analytics outputs.

**Reports:** coverage statistics, ranking statistics, IC/spread by strategy and regime, factor contribution analysis, top 20 candidates, executive committee summary with data-driven conclusions.

---

## 2. Schema

| Migration | Tables |
|-----------|--------|
| `20260603_0011_sprint83_exit_research` | `exit_research_runs`, `exit_research_policy_metrics`, `exit_research_alpha_decay_points` |
| `20260604_0012_sprint85_research_intelligence` | `research_intelligence_runs`, `research_intelligence_reports` |

---

## 3. APIs

### Exit Research — `/api/v1/analytics/exit`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/backfill` | Run exit policy simulation backfill |
| GET | `/runs` | List backfill runs |
| GET | `/runs/{run_id}` | Run detail |
| GET | `/reports/comparison` | Exit policy comparison |
| GET | `/reports/alpha-decay` | Alpha decay report |
| GET | `/reports/rank-deterioration` | Rank deterioration report |
| GET | `/reports/regime-exit` | Regime exit report |
| GET | `/reports/trend-failure` | Trend failure report |
| GET | `/reports/recommended` | Recommended exit policy |

### Research Intelligence — `/api/v1/analytics/research-intelligence`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate` | Generate full report pack (optional persist) |
| GET | `/runs` | List generation runs |
| GET | `/runs/{run_id}` | Run detail with report payloads |

---

## 4. Backfill Scripts

```bash
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

Run `alembic upgrade head` before backfill (through `20260604_0012`).

---

## 5. Policy Families Evaluated

| Family | Variants |
|--------|----------|
| Fixed hold | 5, 10, 15, 20, 30, 40, 60 days |
| Rank deterioration | exit rank > 50, 60, 70, 80, 90 |
| Regime exit | immediate, delay 3, delay 5, never |
| Trend failure | DMA20, DMA50, breakout failure, ATR trailing stop |
| Alpha decay | daily alpha, cumulative alpha, edge persistence, alpha half-life |

All aggregate reports include strategy, regime, horizon, sample size, hit rate, mean/median return, and confidence interval where sample size ≥ 30.

---

## 6. Tests

- Unit: `tests/unit/workspace_exit_research/` — constants, simulators, metrics aggregation
- Integration: `tests/integration/api/test_exit_and_research_api.py` — API smoke tests

Full suite: **189 tests passing**.

---

## 7. Explicit Non-Modifications

- `app/ranking/**`
- `app/validation/**`
- `app/regime_policy/**`
- `app/factor_analytics/**` (read-only consumption only)

Portfolio construction research remains deferred until exit research identifies optimal holding-period and exit framework.
