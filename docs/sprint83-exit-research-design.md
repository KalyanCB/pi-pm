# Sprint 8.3 — Exit Research Workspace Design

**Status:** Design only (no implementation)  
**Branch:** `feature/sprint-8.3-exit-research`  
**Workspace package (planned):** `app/workspace_exit_research/`  
**Migration revision (planned):** `20260603_0011_sprint83_exit_research`  
**Authoring date:** 2026-05-31  
**Takeover:** `docs/HANDOFF.md`, `docs/sprint82-factor-ic-analytics.md`, `docs/sprint81-regime-aware-trading.md`

---

## Executive Summary

Sprint 8.3 introduces **`workspace_exit_research`**, a read-only analytics workspace that answers:

> **Given a signal entry (a top-ranked stock on a validated ranking day), which exit behaviors historically preserved or improved signal edge?**

The workspace **materializes signal-entry cohorts** from frozen ranking/validation artifacts, **simulates exit policies in research code** (no trading, no ranking changes), and **persists aggregate metrics** for five dashboard views. It follows the same isolation pattern as Sprint 8.1 (`app/regime_policy/`) and Sprint 8.2 (`app/factor_analytics/`): consume upstream outputs, write only workspace-owned tables, never mutate `breakout_v1`, validation formulas, or production paths.

**Explicit non-goals:** portfolio simulation, paper trading, position sizing, buy/sell recommendations, auto-selection of “winning” exit policies for production, parameter optimization of stops/thresholds, or changes to regime classification / factor IC pipelines.

---

## 1. Architecture Design

### 1.1 Research workspace isolation

```
┌─────────────────────────────────────────────────────────────────────────┐
│ FROZEN UPSTREAM (read-only)                                              │
│ ranking_runs, ranking_results, ranking_performance_snapshots           │
│ ranking_validation_reports, regime_history, market_data, stocks        │
│ ranking_factor_contributions (optional: signal-strength decile)        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ workspace_exit_research (Sprint 8.3 — NEW)                               │
│ SignalCohortBuilder → ExitPolicySimulator → ExitMetricsEngine            │
│        │                      │                    │                     │
│        ▼                      ▼                    ▼                     │
│ exit_research_runs    exit_research_signals   exit_research_*_metrics  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ API: /api/v1/analytics/exit/*  (dashboards + backfill)                 │
└─────────────────────────────────────────────────────────────────────────┘

Parallel, untouched:
  Signal Validation (app/validation/)     — IC, deciles, regime at signal date
  Regime Research (app/regime_policy/)    — gating policies E1–E4
  Factor IC Research (app/factor_analytics/) — factor predictive power
```

### 1.2 Layering (mirror Sprint 8.2)

| Layer | Planned path | Responsibility |
|-------|----------------|----------------|
| Constants | `workspace_exit_research/constants.py` | Horizons, thresholds, policy IDs, min sample=30 |
| Models (domain) | `workspace_exit_research/models.py` | `SignalEntry`, `ExitOutcome`, policy specs |
| Loaders | `workspace_exit_research/signal_cohort_loader.py` | SQL batch load entries + bars |
| Simulators | `workspace_exit_research/policy_simulators/*.py` | One module per policy family |
| Metrics | `workspace_exit_research/metrics_engine.py` | Mean/median/std/CI, stratified rollups |
| Reports | `workspace_exit_research/reports.py` | Dashboard DTO builders |
| Service | `app/services/exit_research_service.py` | Transactions, backfill orchestration |
| Repositories | `app/db/repositories/exit_research_*` | Upserts, idempotent runs |
| API | `app/api/v1/exit_analytics.py` | REST under `/analytics/exit` |
| Script | `scripts/backfill_sprint83_exit_research.py` | CLI backfill |

**Dependency rule:** `workspace_exit_research` may import `app.validation.forward_returns`, `app.validation.statistics` (bootstrap helpers), `app.ranking.math_utils` (DMA, ATR), and `app.factor_analytics.window` (train/holdout splits). It must **not** import ranking engine, validation report builders, regime policy engine, or factor metrics engine.

### 1.3 Signal entry definition (canonical)

A **signal entry** is one `(ranking_run_id, stock_id)` observation where:

1. `ranking_runs.status = completed` and strategy/universe match the research run config.
2. `ranking_validation_reports.status = completed` for that run.
3. Stock is in **top decile** by score within the run (same `assign_deciles()` semantics as `app/validation/statistics.py`: decile 1 = highest scores).
4. Entry price = **last available close on `ranking_runs.as_of_date`** (same bar walk as validation).
5. Entry metadata captured once: `regime_label` from validation report, `sector` from `stocks`, `signal_strength_decile` (score decile within top decile bucket or full cross-section — see §2), `market_cap_bucket` (derived at materialization — see §2).

**Not** a “trade”: no capital, no friction, no overlap rules unless explicitly studied in a later sprint.

### 1.4 Exit policy families (five research questions)

| ID | Policy family | Question |
|----|---------------|----------|
| Q1 | `FIXED_HOLD` | Does edge persist at fixed 5/10/20/40/60 **trading-day** holds? |
| Q2 | `ALPHA_DECAY` | How does forward return evolve day 1–60? |
| Q3 | `RANK_DETERIORATION` | Should we exit when cross-sectional strength falls below percentile thresholds? |
| Q4 | `REGIME_TRANSITION` | Should we exit on regime deterioration (immediate / delayed)? |
| Q5 | `TREND_FAILURE` | Do price-based stops (DMA, breakout level, ATR trail) protect edge? |

Each policy produces an **exit trading day index** (days after entry) and **holding-period return** (entry close → exit close, trading days).

### 1.5 Processing pipeline

```
POST /analytics/exit/backfill
  → ExitResearchService.start_run() → exit_research_runs (RUNNING)
  → SignalCohortBuilder.build() → exit_research_signals (bulk insert, idempotent)
  → For each policy_family × parameter_grid:
        ExitPolicySimulator.simulate(signals, bars, rank_paths, regimes)
        ExitMetricsEngine.aggregate(strata + ALL)
        persist exit_research_policy_metrics (+ decay curves for Q2)
  → complete run → COMPLETED
```

**Performance:** Batch-load `market_data` per `stock_id` for date windows `[entry_date, entry_date + 70 trading days]`. Batch-load rank paths via single SQL for all `(run_id, stock_id)` keys. Avoid per-signal N+1 queries (lesson from Sprint 8.1).

### 1.6 Integration without impacting validated outputs

| Concern | Mitigation |
|---------|------------|
| Ranking scores change | Never call `RankingEngine` |
| Validation IC changes | Never call `SignalValidationService.compute_run` |
| Regime labels change | Read `ranking_validation_reports.regime_label` + `regime_history` as stored; version via `parameter_set` hash |
| Factor IC backfill | No writes to `factor_*` tables; no reads required for core path |
| Regime backtest | No writes to `regime_backtest_runs` |

Register workspace runs in `experiment_runs` (optional FK) for lineage — same pattern as regime backtest — **without** implying production activation.

---

## 2. Domain Model

### 2.1 Core entities

```python
# Conceptual — implementation in workspace_exit_research/models.py

@dataclass(frozen=True)
class SignalEntry:
    signal_id: UUID
    ranking_run_id: UUID
    stock_id: UUID
    symbol: str
    entry_date: date              # ranking_runs.as_of_date
    entry_rank: int
    entry_score: Decimal
    entry_close: Decimal
  # Stratification dimensions (frozen at entry)
    regime_label: str             # e.g. BULL_LOW_VOL
    sector: str | None
    market_cap_bucket: str        # LARGE | MID | SMALL | UNKNOWN
    signal_strength_decile: int   # 1-10 within run cross-section by score
    dataset_split: str            # TRAIN | HOLDOUT | ALL
    structural_levels: StructuralLevels  # frozen at entry for Q5

@dataclass(frozen=True)
class StructuralLevels:
    dma_20: Decimal | None
    dma_50: Decimal | None
    breakout_level: Decimal       # 63-day high close as of entry (breakout_v1 proxy)
    atr_14: Decimal | None
    atr_trail_distance: Decimal | None  # 2.0 * atr_14 at entry (fixed multiplier)

@dataclass(frozen=True)
class ExitOutcome:
    signal_id: UUID
    policy_family: str
    policy_variant: str           # e.g. FIXED_HOLD_20, RANK_LT_80
    exit_trading_day: int         # 1..N days after entry; 0 = same-day impossible
    holding_days: int
    exit_close: Decimal
    period_return: Decimal
    exit_reason: str              # TIME | RANK | REGIME | DMA20 | ATR_TRAIL | DATA_END
    censored: bool                # True if exit forced by insufficient forward bars
```

### 2.2 Policy variant catalog

**Q1 — Fixed hold (`FIXED_HOLD`)**

| `policy_variant` | `holding_days` |
|------------------|----------------|
| `FIXED_HOLD_5` | 5 |
| `FIXED_HOLD_10` | 10 |
| `FIXED_HOLD_20` | 20 |
| `FIXED_HOLD_40` | 40 |
| `FIXED_HOLD_60` | 60 |

Use `compute_forward_return(bars, entry_date, n)` from `app/validation/forward_returns.py`. Horizons 5/10/20/60 may reuse `ranking_performance_snapshots` when non-NULL; **40-day must always be computed from bars** (not in snapshot schema).

**Q2 — Alpha decay (`ALPHA_DECAY`)**

- For each signal, compute `{k: return(entry → day k)}` for `k = 1..60` trading days.
- Store **curve points** in `exit_research_alpha_decay_points` (not one row per policy metric).
- Derived metrics: `alpha_decay_slope` (OLS on days 5–60), `half_life_day` (first day cumulative mean crosses 50% of day-1 mean), `edge_persistence_days` (last day mean return > 0 with n≥30).

**Q3 — Rank deterioration (`RANK_DETERIORATION`)**

- **Percentile rank** on each subsequent evaluation date: `100 * (rank - 1) / (N - 1)` within that day’s completed run (same universe/strategy).
- Exit when percentile **falls below** threshold (i.e. rank worsens): variants `RANK_PCT_LT_90`, `_80`, `_70`, `_60`, `_50`.
- **Rank path source:** For trading day `d`, use the latest `ranking_runs.as_of_date <= d` for same strategy/version/universe; read `ranking_results.rank`. If no run exists on `d`, carry forward last known rank (document lag bias in §Critical Analysis).
- Exit day = first day threshold breached; if never breached, censor at day 60 or data end.

**Q4 — Regime transition (`REGIME_TRANSITION`)**

- **Entry regime:** `ranking_validation_reports.regime_label` at signal date.
- **Deterioration definition (v1):** Any transition where `trend_regime` flips BULL→BEAR **or** `regime_label` leaves `BULL_LOW_VOL` (aligns with Sprint 8+ research focus). Configurable in `parameter_set` but **not optimized**.
- **Daily regime:** Prefer `regime_history` for benchmark `^NSEI`; fallback to validation report regime on ranking dates only.
- Variants:

| `policy_variant` | Behavior |
|------------------|----------|
| `REGIME_EXIT_IMMEDIATE` | Exit close on first deterioration day |
| `REGIME_EXIT_DELAY_3` | Exit close 3 trading days after deterioration signal |
| `REGIME_EXIT_DELAY_5` | Exit close 5 trading days after deterioration signal |
| `REGIME_EXIT_NEVER` | Hold 60 trading days (benchmark control) |

**Q5 — Trend failure (`TREND_FAILURE`)** — fixed parameters, no grid search

| `policy_variant` | Rule |
|------------------|------|
| `TREND_CLOSE_BELOW_DMA20` | Exit when close < SMA(20) computed from bars through that day |
| `TREND_CLOSE_BELOW_DMA50` | Exit when close < SMA(50) |
| `TREND_CLOSE_BELOW_BREAKOUT` | Exit when close < `breakout_level` (63-day high close frozen at entry) |
| `TREND_ATR_TRAIL_2X` | Trailing stop = max(entry_close, daily peak close since entry) − 2.0 × ATR(14) at entry; exit when close breaches stop |

### 2.3 Aggregated metric record

```python
@dataclass(frozen=True)
class StratifiedExitMetrics:
    policy_family: str
    policy_variant: str
    stratum_type: str       # ALL | REGIME | SECTOR | CAP_BUCKET | SIGNAL_DECILE
    stratum_value: str
    dataset_split: str
    sample_size: int
    mean_return: Decimal | None
    median_return: Decimal | None
    std_dev: Decimal | None
    hit_rate: Decimal | None
    confidence_interval_low: Decimal | None
    confidence_interval_high: Decimal | None
    max_drawdown: Decimal | None      # path-based where applicable
    status: str             # ok | INSUFFICIENT_SAMPLE_SIZE
```

**Hit rate:** fraction of `period_return > 0`.  
**Confidence interval:** bootstrap on per-signal returns (reuse `bootstrap_metric_ci` pattern from `app/regime_policy/metrics.py`, `n=1000`, `seed=42`).  
**If `sample_size < 30`:** `status = INSUFFICIENT_SAMPLE_SIZE`; API suppresses comparative rankings and shows warning banner text.

### 2.4 Market-cap bucket derivation (research-only)

No `market_cap` column exists today. At signal materialization:

1. Prefer Yahoo `marketCap` from provider metadata cache if available in ingest snapshot (future-friendly).
2. Else proxy: `median(close × volume, 20d) * float_shares` when shares outstanding ingested.
3. Else **ADTV proxy** using existing universe filter inputs:  
   - LARGE: 20d ADTV ≥ ₹50 Cr  
   - MID: ₹10–50 Cr  
   - SMALL: < ₹10 Cr  
   - UNKNOWN: insufficient bars  

Buckets are **stored on `exit_research_signals`** so stratification is stable across reruns. Changing bucket rules requires a new `parameter_set` version, not silent mutation.

### 2.5 Signal-strength decile

Within each `ranking_run_id`, assign deciles 1–10 on `ranking_results.score` (full cross-section, not only top decile). Stored as `signal_strength_decile`. Top-decile entries will cluster in deciles 1–2; stratification still allows “strongest vs weakest top-decile” analysis.

---

## 3. Data Model Changes

### 3.1 New domain package

```
app/workspace_exit_research/
  __init__.py
  constants.py
  models.py
  signal_cohort_loader.py
  rank_path_loader.py
  regime_path_loader.py
  metrics_engine.py
  reports.py
  policy_simulators/
    __init__.py
    fixed_hold.py
    alpha_decay.py
    rank_deterioration.py
    regime_transition.py
    trend_failure.py
```

### 3.2 Service & persistence (outside package — Pi-PM convention)

```
app/services/exit_research_service.py
app/db/repositories/exit_research_run_repository.py
app/db/repositories/exit_research_signal_repository.py
app/db/repositories/exit_research_metric_repository.py
app/models/exit_research.py
app/schemas/exit_analytics.py
app/api/v1/exit_analytics.py
```

### 3.3 Read dependencies (unchanged tables)

| Table | Use |
|-------|-----|
| `ranking_runs` | Date, strategy, universe filters |
| `ranking_results` | Rank, score, top-decile membership |
| `ranking_performance_snapshots` | Optional fast path for 5/10/20/60 returns |
| `ranking_validation_reports` | Regime at entry, validation gate |
| `regime_history` | Daily regime path for Q4 |
| `market_data` | Prices, DMA, ATR, forward paths |
| `stocks` | Sector |
| `experiment_runs` | Optional lineage |

---

## 4. Schema Changes

### 4.1 `exit_research_runs`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `status` | VARCHAR(16) | pending, running, completed, failed |
| `strategy_name`, `strategy_version` | VARCHAR | Default `breakout_v1` / `1.0.0` |
| `universe_code` | VARCHAR(64) | Default `NIFTY_500` |
| `as_of_date_start`, `as_of_date_end` | DATE | |
| `holdout_start_date` | DATE | Default `2025-01-01` |
| `entry_filter` | JSONB | e.g. `{"top_decile_only": true}` |
| `parameter_set` | JSONB | Policy thresholds, bucket rules version |
| `signals_materialized` | INT | |
| `metrics_written` | INT | |
| `started_at`, `completed_at` | TIMESTAMPTZ | |
| `error_message` | TEXT | |
| `experiment_run_id` | UUID FK nullable | → `experiment_runs` |

**Index:** `(status, started_at)`

### 4.2 `exit_research_signals`

One row per signal entry (idempotent per run config).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `exit_research_run_id` | UUID FK | |
| `ranking_run_id`, `stock_id` | UUID FK | |
| `entry_date` | DATE | |
| `entry_rank`, `entry_score`, `entry_close` | | |
| `regime_label` | VARCHAR(32) | |
| `sector` | VARCHAR(64) nullable | |
| `market_cap_bucket` | VARCHAR(16) | |
| `signal_strength_decile` | SMALLINT | 1–10 |
| `dataset_split` | VARCHAR(16) | TRAIN/HOLDOUT |
| `breakout_level`, `dma_20`, `dma_50`, `atr_14` | NUMERIC nullable | Frozen structural |
| `created_at` | TIMESTAMPTZ | |

**Unique:** `(exit_research_run_id, ranking_run_id, stock_id)`

**Indexes:** `(exit_research_run_id)`, `(entry_date)`, `(regime_label)`, `(sector)`

### 4.3 `exit_research_policy_metrics`

Aggregate results per policy × stratum × split.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `exit_research_run_id` | UUID FK | |
| `policy_family` | VARCHAR(32) | |
| `policy_variant` | VARCHAR(64) | |
| `stratum_type` | VARCHAR(32) | ALL, REGIME, SECTOR, CAP_BUCKET, SIGNAL_DECILE |
| `stratum_value` | VARCHAR(64) | e.g. `BULL_LOW_VOL`, `Energy` |
| `dataset_split` | VARCHAR(16) | ALL, TRAIN, HOLDOUT |
| `sample_size` | INT | |
| `mean_return`, `median_return`, `std_dev` | NUMERIC(18,8) | |
| `hit_rate` | NUMERIC(18,8) | |
| `confidence_interval_low`, `confidence_interval_high` | NUMERIC(18,8) | |
| `avg_holding_days`, `median_holding_days` | NUMERIC nullable | Q3–Q5 |
| `max_drawdown` | NUMERIC(18,8) nullable | |
| `status` | VARCHAR(32) | ok, INSUFFICIENT_SAMPLE_SIZE |
| `extra` | JSONB | Policy-specific (exit reason mix, censorship rate) |

**Unique:** `(exit_research_run_id, policy_family, policy_variant, stratum_type, stratum_value, dataset_split)`

### 4.4 `exit_research_alpha_decay_points` (Q2 only)

| Column | Type | Notes |
|--------|------|-------|
| `exit_research_run_id` | UUID FK | |
| `forward_day` | SMALLINT | 1–60 |
| `stratum_type`, `stratum_value` | | Same stratification |
| `dataset_split` | VARCHAR(16) | |
| `sample_size` | INT | |
| `mean_return`, `median_return` | NUMERIC | |
| `cumulative_mean_return` | NUMERIC | |
| `status` | VARCHAR(32) | |

**Unique:** `(exit_research_run_id, forward_day, stratum_type, stratum_value, dataset_split)`

### 4.5 Optional: `exit_research_signal_outcomes` (debug / drill-down)

Store per-signal outcomes for API drill-down (cap volume; enable via `parameter_set.persist_outcomes: true`). Not required for dashboard v1.

---

## 5. API Design

**Prefix:** `/api/v1/analytics/exit` (parallel to `/api/v1/analytics/factors`)

### 5.1 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/backfill` | Start materialization + simulation for date window |
| GET | `/runs` | List `exit_research_runs` |
| GET | `/runs/{run_id}` | Run status + counts |
| GET | `/policy-comparison` | Dashboard 1 — all variants, ALL stratum |
| GET | `/alpha-decay` | Dashboard 2 — curve + summary metrics |
| GET | `/rank-deterioration` | Dashboard 3 — threshold sweep |
| GET | `/regime-transition` | Dashboard 4 — delay variants |
| GET | `/trend-failure` | Dashboard 5 — price stop variants |
| GET | `/signals/sample` | Optional: paginated sample for audit |

### 5.2 Common query parameters

| Param | Required | Description |
|-------|----------|-------------|
| `run_id` | Yes* | Latest completed if omitted (explicit default rules in service) |
| `universe_code` | No | Filter |
| `strategy_name` | No | Default `breakout_v1` |
| `dataset_split` | No | `HOLDOUT` default for research conclusions |
| `regime_label` | No | Filter stratum |
| `sector` | No | |
| `market_cap_bucket` | No | |
| `signal_strength_decile` | No | |

### 5.3 Response contract (metrics row)

```json
{
  "policy_family": "FIXED_HOLD",
  "policy_variant": "FIXED_HOLD_20",
  "stratum_type": "REGIME",
  "stratum_value": "BULL_LOW_VOL",
  "dataset_split": "HOLDOUT",
  "sample_size": 412,
  "mean_return": "0.0241",
  "median_return": "0.0188",
  "std_dev": "0.0912",
  "hit_rate": "0.56",
  "confidence_interval_low": "0.0110",
  "confidence_interval_high": "0.0372",
  "avg_holding_days": "20.0",
  "status": "ok"
}
```

When `sample_size < 30`:

```json
{
  "sample_size": 12,
  "status": "INSUFFICIENT_SAMPLE_SIZE",
  "mean_return": null,
  "confidence_interval_low": null,
  "confidence_interval_high": null,
  "message": "Suppress comparative conclusions; n < 30."
}
```

### 5.4 POST `/backfill` body

```json
{
  "universe_code": "NIFTY_500",
  "strategy_name": "breakout_v1",
  "strategy_version": "1.0.0",
  "start_date": "2023-01-01",
  "end_date": "2025-05-30",
  "holdout_start_date": "2025-01-01",
  "persist_signal_outcomes": false,
  "experiment_name": "sprint83_exit_research_v1"
}
```

### 5.5 Dependency injection

Add `get_exit_research_service()` to `app/api/deps.py` following `get_factor_predictive_power_service()` pattern.

---

## 6. Analytics Job Design

### 6.1 Backfill script

`scripts/backfill_sprint83_exit_research.py`

```bash
python scripts/backfill_sprint83_exit_research.py \
  --universe-code NIFTY_500 \
  --start-date 2023-01-01 \
  --end-date 2025-05-30 \
  --holdout-start-date 2025-01-01
```

Uses `get_session_factory()()` (not `SessionLocal`).

### 6.2 Job phases

1. **Validate prerequisites** — completed validations + snapshots in window; warn if `return_20d` sparse (Sprint 8.1 lesson).
2. **Materialize signals** — bulk insert `exit_research_signals`.
3. **Prefetch** — market bars + rank paths + regime series keyed by `(stock_id, entry_date)`.
4. **Simulate policies** — vectorized where possible; pure functions for unit tests.
5. **Aggregate** — stratify: ALL + each regime + sector + cap bucket + signal decile; splits ALL/TRAIN/HOLDOUT.
6. **Persist** — upsert metrics; decay points for Q2.
7. **Complete run** — status, counts, structured logs (`exit_research_*` events).

### 6.3 Idempotency

- `exit_research_runs`: unique on `(strategy, version, universe, start, end, holdout, parameter_set_hash)`.
- Re-run deletes or upserts metrics for same run id only.
- Signals: `ON CONFLICT DO NOTHING` on unique key.

### 6.4 Runtime estimates

| Phase | Risk | Mitigation |
|-------|------|------------|
| Rank path join | O(signals × days) | Pre-index runs by date; SQL window functions |
| Bar load | Large IO | Batch by stock_id chunks of 50 |
| Bootstrap | CPU | Stratified aggregates only; bootstrap final means not per-signal |

Target: full NIFTY_500 × 2y history < 15 minutes on dev hardware (measure in implementation).

---

## 7. Dashboard Design

Front-end is out of scope; APIs return dashboard-ready aggregates.

### 7.1 Exit Policy Comparison

- **Rows:** All `policy_variant` across Q1–Q5 (normalized labels).
- **Columns:** `mean_return`, `median_return`, `hit_rate`, CI, `sample_size`, `status`.
- **Views:** Toggle `dataset_split`; facet by `regime_label` (default `BULL_LOW_VOL`).
- **Chart:** Horizontal bar — mean return with CI whiskers; grey-out `INSUFFICIENT_SAMPLE_SIZE`.
- **Table sort:** Disabled when status insufficient.

### 7.2 Alpha Decay Analysis

- **Line chart:** X = forward day 1–60; Y = `mean_return` and `cumulative_mean_return`; bands = bootstrap CI per day (only days with n≥30).
- **KPI cards:** Day-1 mean, day-20 mean, decay slope, edge persistence days.
- **Facet:** Regime tabs; optional sector dropdown.

### 7.3 Rank Deterioration Analysis

- **X-axis:** Threshold (90, 80, 70, 60, 50).
- **Series:** `mean_return`, `median_return`, `hit_rate`, `avg_holding_days`.
- **Distribution mini-chart:** Histogram of holding days (from `extra.holding_days_histogram`).

### 7.4 Regime Transition Analysis

- **Grouped bar:** Variants immediate / delay-3 / delay-5 / never.
- **Overlay:** Censorship rate + % exits due to regime vs time stop.
- **Facet:** Entry regime = `BULL_LOW_VOL` vs ALL.

### 7.5 Trend Failure Analysis

- **Compare:** DMA20, DMA50, breakout, ATR trail vs `FIXED_HOLD_20` baseline (reference line).
- **Show:** Time-to-exit distribution; hit rate vs fixed hold.

---

## 8. Validation Strategy

### 8.1 Research validity checks (automated in job)

| Check | Rule |
|-------|------|
| Entry lookahead | Entry close must be last bar on `as_of_date`, not future |
| Regime lookahead | Regime for day `d` uses bars ≤ `d` only (reuse validation regime rules) |
| Rank lookahead | Rank on day `d` uses ranking run with `as_of_date <= d` |
| Holdout integrity | Default reporting uses `HOLDOUT` split; train for exploration only |
| Censorship disclosure | Report `% censored` per policy in `extra` |
| Minimum n | Enforce n≥30 for `status=ok` |

### 8.2 Manual validation checklist (post-backfill)

1. Compare `FIXED_HOLD_20` mean to validation top-decile `return_20d` campaign aggregates — should be directionally consistent, not identical (different cohort: top decile stocks vs decile bucket mean).
2. Spot-check 10 signals: verify exit day against manual Excel.
3. Confirm `BEAR_HIGH_VOL` strata → `INSUFFICIENT_SAMPLE_SIZE`.
4. Re-run backfill → identical metrics (idempotency).

### 8.3 Regression guardrails

- Full `pytest` suite must pass without changes to ranking/validation snapshots (golden tests untouched).
- Add integration test: backfill small fixture window → expect known policy metrics.

---

## 9. Test Strategy

### 9.1 Unit tests (`tests/unit/workspace_exit_research/`)

| Module | Cases |
|--------|-------|
| `fixed_hold` | Known bar series → exact return |
| `alpha_decay` | 60-day path monotonicity |
| `rank_deterioration` | Threshold breach day |
| `regime_transition` | Immediate vs delay counting |
| `trend_failure` | DMA cross, ATR trail ratchet |
| `metrics_engine` | n<30 → INSUFFICIENT; bootstrap CI bounds |
| `signal_cohort_loader` | Top decile filter |

### 9.2 Integration tests

- `tests/integration/api/test_exit_analytics_api.py` — filter params, 404 run, insufficient sample JSON shape.
- Repository upsert idempotency (in-session).

### 9.3 Fixtures

Extend `tests/conftest.py` with miniature ranking run + 30 bars/market_data pattern (reuse factor_analytics conftest style).

### 9.4 Non-goals for tests

- No UI tests.
- No live Yahoo calls.

---

## 10. Risk Assessment

### 10.1 Bias and methodological risks

| Risk | Severity | Mitigation in design |
|------|----------|----------------------|
| **Survivorship bias** | High | Universe membership uses historical `universe_memberships`; include delisted if present in DB; document if only active stocks |
| **Look-ahead bias** | High | Frozen entry levels; ranks/regimes dated ≤ evaluation day; code review checklist |
| **Holdout contamination** | Medium | Default API `dataset_split=HOLDOUT`; never tune thresholds on holdout |
| **Sparse strata** | High | n<30 → INSUFFICIENT_SAMPLE_SIZE; do not merge strata without explicit rule |
| **Rank path staleness** | Medium | Rank updates only on ranking dates (~daily backtest); document as structural limitation |
| **Overlapping signals** | Medium | Multiple entries same stock across dates treated independent (research choice); document; optional de-duplication in v2 |
| **Friction ignored** | Low | Research-only; disclose |
| **Multiple testing** | Medium | Many policy variants → emphasize pre-registration of primary comparisons (fixed 20d vs best exit) in research template |

### 10.2 Architectural risks

| Risk | Mitigation |
|------|------------|
| Scope creep into trading | Hard boundary in domain-boundaries.md update |
| Package coupling | No imports from regime_policy / factor_analytics engines |
| DB growth (`signal_outcomes`) | Off by default |
| Runtime | Batched SQL + chunked bar loads |

### 10.3 Missing research questions (future, not 8.3)

- Volume / liquidity exits (ADTV collapse).
- Time-stop vs profit-target combinations.
- Cross-signal portfolio overlap and capital constraints.
- Vol-scaled position sizing (explicitly out of scope).
- Comparison to **random entry** control within same universe.

---

## 11. Migration Plan

### 11.1 Alembic

1. Create `20260603_0011_sprint83_exit_research.py` after head `20260602_0010`.
2. Tables: `exit_research_runs`, `exit_research_signals`, `exit_research_policy_metrics`, `exit_research_alpha_decay_points`.
3. Register models in `migrations/env.py` and `app/models/__init__.py`.

### 11.2 Documentation updates (implementation PR)

| Doc | Change |
|-----|--------|
| `docs/DATABASE_SCHEMA.md` | Sprint 8.3 tables |
| `docs/API_REFERENCE.md` | `/analytics/exit/*` |
| `docs/domain-boundaries.md` | `workspace_exit_research` section |
| `docs/HANDOFF.md` | Sprint 8.3 runbook link |
| `docs/SPRINT_HISTORY.md` | Entry after ship |
| `docs/DECISION_LOG.md` | ADR-022 Exit research isolation |

### 11.3 Rollout

1. Merge design (this doc).
2. Implement on feature branch; `alembic upgrade head`.
3. Backfill NIFTY_500 window aligned with factor IC backfill.
4. Human review dashboards on holdout before any trading sprint.

### 11.4 Rollback

Drop tables via downgrade revision; no upstream data affected.

---

## 12. Implementation Plan

### Phase 0 — Design approval (current)

- [x] Design document
- [ ] ADR-022 stakeholder sign-off

### Phase 1 — Schema & skeleton (3–4 days)

- Migration + ORM models + repositories
- `workspace_exit_research/constants.py`, `models.py`
- Empty service + router returning 501

### Phase 2 — Signal materialization (3 days)

- `SignalCohortBuilder` + loader tests
- Cap bucket + decile computation
- `exit_research_signals` backfill phase only

### Phase 3 — Policy simulators (5–6 days)

- Q1 fixed hold, Q2 alpha decay
- Q3 rank path loader + deterioration
- Q4 regime path + delays
- Q5 trend failure (reuse `math_utils`)

### Phase 4 — Metrics & API (4 days)

- `ExitMetricsEngine` + stratification
- Reports + 5 dashboard endpoints
- Integration tests

### Phase 5 — Backfill & validation (2–3 days)

- CLI script
- Manual validation checklist
- `docs/sprint83-exit-research-results-template.md` (optional)

### Phase 6 — Docs & handoff (1 day)

- Update HANDOFF, API_REFERENCE, domain-boundaries
- No changes to `app/ranking/**`, `app/validation/**`, `app/regime_policy/**`, `app/factor_analytics/**` except shared util imports

**Estimated effort:** 18–22 dev days (single engineer), excluding UI.

---

## Critical Analysis (Design Challenge)

### Survivorship bias

NIFTY 500 membership changes over time. If exits are computed only for stocks still active in the master table, delisted losers may be missing. **Design mitigation:** join `universe_memberships` as-of `entry_date`; flag `survivorship_warning` in run metadata when `removed_at` stocks excluded; long-term: ingest delisting dates.

### Look-ahead bias

Rank deterioration is the highest risk: using a ranking run with `as_of_date` after the simulated calendar day would inflate exits. **Mitigation:** strict `as_of_date <= evaluation_date` rule; unit tests with adversarial dates. Regime delays must use closes available at exit day, not announcement times.

### Holdout contamination

With ~15 policy variants × 5 strata types × multiple splits, exhaustive search on holdout will overfit. **Mitigation:** document **primary endpoint** in results template: `FIXED_HOLD_20` vs best alternative on **train**, confirm on **holdout** once. API defaults to HOLDOUT but UI should require train/holdout toggle discipline.

### Sample-size issues

`BULL_LOW_VOL` may be adequate while `BEAR_HIGH_VOL` remains unusable (historical n≈4 at campaign level). Stratified dashboards will be mostly `INSUFFICIENT_SAMPLE_SIZE` outside ALL and BULL_LOW_VOL — **this is correct behavior**, not a bug.

### Architectural concerns

- **Rank frequency:** Rankings exist per backtest day, not intraday; rank-deterioration exits are stepwise. Alternative (rerank simulation) is out of scope because it would invoke ranking engine.
- **40-day hold:** Requires bar computation; inconsistent snapshot coverage must be logged.
- **Breakout level proxy:** 63-day high is an research proxy, not necessarily identical to `consolidation_breakout` factor internal state — document in dashboard footnotes.

### Weaknesses in proposed approach

1. **Independent entries** ignore portfolio overlap.
2. **No transaction costs** overstate stop-loss benefits.
3. **ATR trail frozen at entry ATR** is simplistic (industry often recalculates ATR daily) — intentional to avoid parameter optimization.
4. **Regime deterioration** definition privileging `BULL_LOW_VOL` may not generalize if strategy edge shifts.

### Extension points (safe)

| Extension | Isolation |
|-----------|-----------|
| New policy variant | Add simulator module + enum; no upstream change |
| New stratification | Add column on signals + metrics stratum_type |
| LLM narrative (Sprint 8.4+) | Read metrics tables only |
| Paper trading | Separate sprint; consumes **selected** policy externally |

---

## Research Standards Compliance Matrix

| Requirement | Design element |
|-------------|----------------|
| Stratify by regime, sector, cap bucket, signal-strength decile | `stratum_type` on metrics; dimensions on `exit_research_signals` |
| sample_size, mean, median, std_dev, CI | `exit_research_policy_metrics` columns |
| n < 30 → INSUFFICIENT_SAMPLE_SIZE | `MIN_EXIT_RESEARCH_SAMPLE_SIZE = 30` in constants |
| No ranking/validation/regime/factor changes | Isolation rules §1.6 |
| Five dashboards | §7 + API §5.1 |

---

## Related Documentation

- `docs/sprint82-factor-ic-analytics.md` — prior isolated workspace pattern
- `docs/sprint81-regime-aware-trading.md` — replay + bootstrap patterns
- `docs/sprint7-platform-traceability.md` — data lineage
- `docs/ROADMAP.md` — Sprint 8.3 entry
