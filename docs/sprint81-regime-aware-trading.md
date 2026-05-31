# Sprint 8.1 — Regime-Aware Trading

**Status:** Implemented (research only)  
**Migration:** `20260531_0008`  
**Branch:** `feature/sprint8`  
**Takeover:** `docs/HANDOFF.md`

Research-only policy layer for evaluating regime gating on `breakout_v1` using historical replay. **No live ranking, validation, or paper trading changes.**

---

## Scope

| In scope | Out of scope |
|----------|--------------|
| Policy configs, decisions, backtest runs | Ranking/factor/weight changes |
| E1–E4 experiment comparison | Live policy activation in production |
| Bootstrap CI + `research_findings` | Paper trading integration |
| Holdout split (`2025-01-01`) | Sprint 8.2 factor analytics |

---

## Architecture

```
POST /regime-policy/backtest/run
  → RegimePolicyService.run_backtest_comparison()
  → ExperimentService.start() [committed RUNNING]
  → Load validation reports (once)
  → batch_load_scored_returns_by_run() [1 SQL query]
  → validation_horizon_metrics spreads [E1/E2 fast path]
  → For each policy (E1–E4):
       create_running() → flush()
       RegimePolicyReplayService.replay()
       compare_spread_significance()
       complete() → research_findings
  → ExperimentService.complete()
```

### Key packages

| Path | Role |
|------|------|
| `app/regime_policy/engine.py` | `RegimePolicyEngine` — deterministic ALLOW/BLOCK/REDUCE |
| `app/regime_policy/replay.py` | Historical overlay on stored results |
| `app/regime_policy/metrics.py` | Pooled metrics, bootstrap CI, research findings |
| `app/regime_policy/scored_returns_loader.py` | Batch SQL load |
| `app/services/regime_policy_service.py` | Orchestration |
| `app/api/v1/regime_policy.py` | REST API |

### Data sources (read-only)

- `ranking_validation_reports.regime_label` — regime at signal date (no lookahead)
- `ranking_results` + `ranking_performance_snapshots` — scores + forward returns
- `validation_horizon_metrics` — precomputed spread/IC (E1/E2 daily spreads)

**No reranking. No factor recompute. No score reconstruction in backtest path.**

---

## Setup

```bash
alembic upgrade head   # through 20260531_0008

# Load E1-E4 draft presets (NOT in migration)
python scripts/init_regime_policy_presets.py

# Verify
python -c "
from app.core.config import get_settings
from app.db.session import get_session_factory
from sqlalchemy import text
get_settings()
db = get_session_factory()()
print(db.execute(text('SELECT policy_name, policy_type FROM regime_policy_configs')).all())
db.close()
"
```

Or via API:

```bash
curl -X POST http://localhost:8000/api/v1/regime-policy/configs/presets/load \
  -H "Content-Type: application/json" -d '{"dry_run": false}'
```

---

## Policy Experiments

| ID | Type | Behavior |
|----|------|----------|
| E1 | `BASELINE_E1` | No gating |
| E2 | `HARD_GATE_E2` | `BULL_LOW_VOL` only — block all other regimes |
| E3 | `SOFT_GATE_E3` | 100% BULL_LOW_VOL, 50% elsewhere — **scale returns**, do not exclude days |
| E4 | `THRESHOLD_GATE_E4` | BULL_LOW_VOL + top decile only (**experimental**, low n) |

---

## API Endpoints

Prefix: `/api/v1/regime-policy`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/configs` | List policy configs |
| POST | `/configs` | Create draft config |
| POST | `/configs/presets/load` | Load E1–E4 presets |
| POST | `/configs/{id}/activate` | Activate (research registry only) |
| GET | `/decisions` | Audit trail |
| POST | `/evaluate` | Dry-run / persist decision |
| POST | `/backtest/run` | Run E1–E4 comparison |
| GET | `/backtest/runs` | List backtest results |

Full examples: `docs/API_REFERENCE.md`

---

## Backtest Runbook

### 1. Get policy config IDs

```bash
curl "http://localhost:8000/api/v1/regime-policy/configs?strategy_name=breakout_v1"
```

Note UUIDs for E1 (baseline), E2, E3, E4.

### 2. Run comparison

```bash
curl -X POST http://localhost:8000/api/v1/regime-policy/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "breakout_v1",
    "strategy_version": "1.0.0",
    "universe_code": "NIFTY_500",
    "horizon": 20,
    "start_date": "2024-01-01",
    "end_date": "2025-12-31",
    "holdout_start_date": "2025-01-01",
    "policy_config_ids": ["<e1>", "<e2>", "<e3>", "<e4>"],
    "baseline_policy_config_id": "<e1>",
    "experiment_name": "sprint81_regime_gate_comparison"
  }'
```

### 3. Verify completion

```sql
SELECT id, status FROM experiment_runs ORDER BY started_at DESC LIMIT 3;
SELECT id, status, policy_config_id,
       research_findings->>'recommendation' AS rec
FROM regime_backtest_runs ORDER BY started_at DESC LIMIT 5;
```

Expect: experiment `completed`, 4 backtest runs `completed`.

### 4. Document results

Fill `docs/sprint81-results-template.md`.

---

## Troubleshooting

### ALLOW decisions but sample_count=0 (fixed 8.1.2)

**Symptom:** `regime_policy_decisions` shows ALLOW for E2 BULL_LOW_VOL, but backtest reports `sample_count=0`, `ranked_days=0`.

**Cause:** Replay excluded ALLOW days when `batch_load_scored_returns_by_run()` returned no rows (NULL `return_20d` on snapshots while `validation_horizon_metrics` still populated from Sprint 7 backfill). Engine decisions were persisted before the exclusion check.

**Fix (8.1.2):**
- `_try_include_precomputed_day()` — E1/E2 include days from `validation_horizon_metrics` when snapshot returns missing
- `sample_sizes_by_report_for_horizon()` on `ValidationMetricsRepository`
- `research_findings` falls back to train metrics when holdout `ranked_days==0`

**Log events:**
- `regime_replay_day_evaluated`
- `regime_replay_day_excluded_no_scored_returns`
- `regime_replay_day_included_precomputed`
- `regime_replay_pooled_samples_before_metrics`

**Remediation if still failing:** Force validation recompute to populate snapshot returns:

```bash
curl -X POST "http://localhost:8000/api/v1/validation/runs/{run_id}/compute?force_recompute=true"
```

### Experiment stuck RUNNING, no backtest rows

**Cause (fixed 8.1.1):** Baseline replay pooled ~200k stock-days into `compute_full_horizon_metrics()` → O(n²) directional hit rate in `compute_hit_rates()`.

**Fix:** Ensure code includes:
- `compute_pooled_period_metrics()` in `app/regime_policy/metrics.py`
- `batch_load_scored_returns_by_run()` in replay path
- Do **not** call `compute_full_horizon_metrics` on pooled train/holdout sets

**Log events to watch:**
- `regime_backtest_data_loaded`
- `regime_backtest_baseline_replay_completed`
- `regime_backtest_run_created`
- `regime_backtest_completed`

### Preset loader ImportError SessionLocal

Use `get_session_factory()()` — see `scripts/init_regime_policy_presets.py`.

### Empty traceability during backtest

Backtest reads `ranking_validation_reports` + performance snapshots. Run Sprint 7.1 backfill first:

```bash
python scripts/backfill_sprint7_traceability.py --all
```

---

## Performance Notes

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Batch scored returns load | O(rows) 1 query | ~410 days × ~500 stocks |
| Per-day policy loop | O(days) | ~410 iterations |
| Pooled period metrics | O(n log n) | n = pooled stock-days |
| ~~Pooled compute_full_horizon_metrics~~ | ~~O(n²)~~ | **Removed — caused hang** |
| Bootstrap CI | O(1000 × days) | Fine |

---

## Walk-Forward Ready Design

`window_spec` JSON on `regime_backtest_runs`:

| Field | Purpose |
|-------|---------|
| `mode` | `single_holdout` (implemented), `rolling`, `walk_forward` (reserved) |
| `holdout_start_date` | Current: `2025-01-01` |
| `rolling_window_days` | Future Sprint 8.2+ |
| `walk_forward_step_days` | Future Sprint 8.2+ |
| `holdout_periods` | Future multi-holdout |

---

## research_findings Schema

Stored on `regime_backtest_runs.research_findings`:

```json
{
  "policy": "HARD_GATE_E2",
  "baseline_spread": 0.002,
  "policy_spread": 0.016,
  "improvement": 0.014,
  "sample_count": 237,
  "ranked_days": 50,
  "confidence": "high",
  "recommendation": "promote_to_next_research_stage",
  "is_statistically_significant": true,
  "spread_p_value": 0.01,
  "spread_ci_lower": 0.008,
  "spread_ci_upper": 0.024
}
```

Consumed by future Research Copilot (Sprint 8.3).

---

## Verification SQL

```sql
SELECT policy_type, status, COUNT(*) FROM regime_policy_configs GROUP BY 1, 2;
SELECT COUNT(*) FROM regime_policy_decisions;
SELECT policy_config_id, status,
       holdout_metrics->>'spread' AS holdout_spread,
       research_findings->>'recommendation'
FROM regime_backtest_runs ORDER BY started_at DESC LIMIT 10;
```

---

## Tests

```bash
.venv/bin/pytest tests/unit/regime_policy tests/integration/api/test_regime_policy_api.py -q
```

---

## Rollback

```bash
alembic downgrade 20260530_0007
```

No impact on ranking, validation, or traceability tables.

---

## Related Documentation

- `docs/HANDOFF.md` — Takeover guide
- `docs/sprint81-results-template.md` — Results template
- `docs/ARCHITECTURE.md` — Regime policy layer diagram
- `docs/DECISION_LOG.md` — ADR-016 through ADR-019
