# Pi-PM — Developer & AI Handoff Guide

**Last updated:** 2026-06-01  
**Purpose:** Enable any developer, AI assistant, or LLM to take over Pi-PM without prior chat context.

**Start here.** Then read linked docs for depth.

---

## 1. What Is This Project?

Pi-PM (Personal Intelligence Portfolio Manager) ranks Indian NSE equities using **deterministic** factor models, validates whether rankings predict forward returns, and (in progress) evaluates regime-aware trading policies before any live deployment.

**Non-negotiable:** LLMs never rank, size positions, approve trades, or override risk. Money logic is deterministic.

| Item | Value |
|------|-------|
| Repo | `/Users/kalyancb/pi-pm` |
| Remote | `https://github.com/KalyanCB/pi-pm.git` |
| Active branch | `feature/sprint-8.3-exit-research` (Sprint 8.3 exit research + 8.5 research intelligence) |
| Base branch | `main` |
| API | FastAPI @ `/api/v1` |
| DB | PostgreSQL 16, user/db `pipm` |
| Migration head | `20260606_0014` |
| Tests | **189 passing** (`pytest`) |

---

## 2. Read Order (30-Minute Onboarding)

| Order | Document | Why |
|------:|----------|-----|
| 1 | `docs/HANDOFF.md` | This file — current state |
| 2 | `docs/AI_CONTEXT.md` | Pipeline, defaults, gotchas |
| 3 | `docs/ARCHITECTURE.md` | Layers, diagrams, data flows |
| 4 | `docs/DATABASE_SCHEMA.md` | All tables |
| 5 | `docs/API_REFERENCE.md` | Every endpoint |
| 6 | `docs/SPRINT_HISTORY.md` | What shipped when |
| 7 | Sprint runbooks (below) | Operational procedures |

**Sprint runbooks:**

- `docs/sprint61-full-universe-validation-report.md` — full-universe campaigns
- `docs/sprint7-platform-traceability.md` — traceability design
- `docs/sprint71-traceability-operationalization.md` — backfill + verification SQL
- `docs/sprint81-regime-aware-trading.md` — regime policy + backtest
- `docs/sprint81-results-template.md` — fill after backtest
- `docs/sprint82-factor-ic-analytics.md` — factor IC analytics + backfill
- `docs/sprint82-implementation-summary.md` — PR review package

---

## 3. Core Pipeline

```
Market Data Ingest (Yahoo)
  → Universe Filter (eligibility)
  → Ranking Engine (factors → normalize → score → rank)
  → Persist ranking_runs + ranking_results + performance_snapshots
  → Validation (forward returns, IC, deciles, regime)
  → Traceability (factor contributions, horizon metrics, lineage)  [Sprint 7]
  → Regime Policy Replay / Backtest (research only)               [Sprint 8.1]
```

---

## 4. Current Sprint Status

### Complete

| Sprint | Feature |
|--------|---------|
| 6.1 | Full-universe validation campaigns |
| 7 | Platform traceability tables + observability API |
| 7.1 | Traceability backfill + `ensure_*` on reuse paths |
| 8.1 | Regime-aware trading policy layer (research only) |

### In Progress / Next

| Sprint | Feature | Status |
|--------|---------|--------|
| 8.2 | Factor predictive power analytics | Planned — not implemented |
| 8.3 | AI research agent | Planned |
| Portfolio / paper trading | Tables exist, services stubbed | Not started |

---

## 5. Key Research Finding (Drives Sprint 8+)

`breakout_v1` at **20-day horizon** appears alpha-positive only in **BULL_LOW_VOL**:

| Regime | avg IC | avg spread | n |
|--------|--------|------------|---|
| BULL_LOW_VOL | +0.0359 | +1.62% | 237 |
| BEAR_LOW_VOL | -0.0891 | -3.11% | 80 |
| BULL_HIGH_VOL | -0.1704 | -3.06% | 28 |
| BEAR_HIGH_VOL | -0.3738 | -11.30% | 4 |

Sprint 8.1 tests whether **regime gating** (E1–E4 policies) improves holdout performance vs baseline.

---

## 6. Environment Setup

```bash
cd /Users/kalyancb/pi-pm

# Python venv
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt  # or project install method

# Database
docker compose -f docker/docker-compose.yml up -d db
alembic upgrade head

# API (local)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or Docker (rebuild after code changes!)
docker compose -f docker/docker-compose.yml build api
docker compose -f docker/docker-compose.yml up -d
```

**.env:** Copy from `.env.example` if present; key var is `DATABASE_URL`.

---

## 7. Common Operations

### Run ranking (full universe)

```bash
curl -X POST http://localhost:8000/api/v1/rankings/run \
  -H "Content-Type: application/json" \
  -d '{
    "universe_code": "NIFTY_500",
    "strategy_name": "breakout_v1",
    "strategy_version": "1.0.0",
    "benchmark_symbol": "^NSEI"
  }'
```

### Backfill traceability (if tables empty)

```bash
python scripts/backfill_sprint7_traceability.py --all
```

### Load regime policy presets (Sprint 8.1)

```bash
# Uses get_session_factory() — NOT SessionLocal
python scripts/init_regime_policy_presets.py
```

### Run regime backtest comparison

```bash
# 1. Load presets, get config UUIDs from GET /regime-policy/configs
# 2. POST /regime-policy/backtest/run (see sprint81 doc)
```

### Tests

```bash
.venv/bin/pytest tests/ -q
```

---

## 8. Critical Gotchas

| Gotcha | Fix |
|--------|-----|
| Default universe is `PI_PM_CORE` (~15 stocks) | Always pass `universe_code: NIFTY_500` |
| Docker serves stale code | Rebuild + restart API container |
| Traceability tables empty on reuse paths | Sprint 7.1 fixed forward path; run backfill for history |
| `SessionLocal` does not exist | Use `get_session_factory()()` in scripts |
| Backtest hangs / experiment stuck RUNNING | Fixed in 8.1.1 — see §9 |
| E2 shows ALLOW decisions but `sample_count=0` | Fixed in 8.1.2 — see §10; check snapshot returns or horizon-metrics fallback |
| Do not call `compute_full_horizon_metrics` on 200k+ pooled rows | O(n²) directional hit rate — use `compute_pooled_period_metrics` |
| Ranking/validation logic is frozen unless scoped | Policy layer only post-ranking |

---

## 9. Sprint 8.1 Backtest — Known Bug & Fix

### Symptom

- `POST /regime-policy/backtest/run` returns 200 eventually OR hangs
- `experiment_runs` stuck `RUNNING`
- No `regime_backtest_runs` rows

### Root cause

Before first `regime_backtest_runs` insert, `baseline_replay()` pooled ~410 days × ~500 stocks (~200k rows) into `compute_full_horizon_metrics()` → `compute_hit_rates()` **O(n²)** directional loop → CPU pegged, no traceback.

Secondary: **N+1 SQL** — one query per validation day per policy.

### Fix (implemented)

| Change | File |
|--------|------|
| `compute_pooled_period_metrics()` — no O(n²) | `app/regime_policy/metrics.py` |
| `batch_load_scored_returns_by_run()` — 1 query | `app/regime_policy/scored_returns_loader.py` |
| Use `validation_horizon_metrics` for E1/E2 spreads | `app/regime_policy/replay.py` |
| Timing logs + early `flush()` on backtest run | `app/services/regime_policy_service.py` |

### Verify backtest success

```sql
SELECT status, COUNT(*) FROM experiment_runs GROUP BY 1;
SELECT status, COUNT(*) FROM regime_backtest_runs GROUP BY 1;
```

Expect: experiment `completed`, 4 backtest runs `completed`.

---

## 10. Sprint 8.1 Replay — ALLOW but Zero Metrics (8.1.2)

### Symptom

- `regime_policy_decisions` shows **ALLOW** for BULL_LOW_VOL (E2)
- `RegimePolicyEngine` is correct
- Backtest / `research_findings` shows `sample_count=0`, `ranked_days=0`
- `days_included=0` on `regime_backtest_runs`

### Root cause

Replay persisted engine decisions, then excluded days when `batch_load_scored_returns_by_run()` returned no rows (typically `return_20d IS NULL` on all performance snapshots while `validation_horizon_metrics` still has spread/sample_size from Sprint 7 backfill).

Secondary: `research_findings` used holdout metrics only; if all BULL days fall before `holdout_start_date` (2025-01-01), holdout shows zero even when train has data.

### Fix (8.1.2)

| Change | File |
|--------|------|
| E1/E2 fallback via `_try_include_precomputed_day()` when horizon metrics exist | `app/regime_policy/replay.py` |
| `sample_sizes_by_report_for_horizon()` | `app/db/repositories/validation_metrics_repository.py` |
| Pass sample sizes to replay; use train metrics in findings when holdout empty | `app/services/regime_policy_service.py` |
| Diagnostic logging (`regime_replay_day_*`) | `app/regime_policy/replay.py` |

### Log events

- `regime_replay_day_evaluated` — report_id, ranking_run_id, regime_label, policy_action, scored_returns_loaded
- `regime_replay_day_excluded_no_scored_returns` — ALLOW but no snapshot returns
- `regime_replay_day_included_precomputed` — fallback path used
- `regime_replay_pooled_samples_before_metrics` — pooled counts before metrics

### Verify

```sql
SELECT days_included,
       train_metrics->>'ranked_days' AS train_days,
       holdout_metrics->>'ranked_days' AS holdout_days,
       research_findings->>'sample_count' AS findings_sample
FROM regime_backtest_runs
WHERE policy_config_id IN (
  SELECT id FROM regime_policy_configs WHERE policy_type = 'HARD_GATE_E2'
)
ORDER BY started_at DESC LIMIT 1;
```

If days still excluded with no precomputed fallback, recompute validation to populate snapshot returns:

```bash
curl -X POST "http://localhost:8000/api/v1/validation/runs/{run_id}/compute?force_recompute=true"
```

---

## 11. Package Map

```
app/
├── api/v1/                    # HTTP routes
│   ├── observability.py       # Sprint 7
│   └── regime_policy.py       # Sprint 8.1
├── api/deps.py                # DI — all service factories
├── core/config.py             # Settings
├── core/constants.py          # Enums, policy types
├── db/repositories/           # Data access
├── models/                    # SQLAlchemy ORM
├── schemas/                   # Pydantic DTOs
├── services/                  # Orchestration
│   ├── traceability_service.py
│   ├── regime_policy_service.py
│   └── ...
├── regime_policy/             # Sprint 8.1 domain (NOT ranking)
│   ├── engine.py              # RegimePolicyEngine
│   ├── replay.py              # Historical overlay
│   ├── metrics.py             # Pooled metrics + bootstrap CI
│   └── scored_returns_loader.py
├── ranking/                   # DO NOT MODIFY unless scoped
├── validation/                # DO NOT MODIFY unless scoped
└── backtest/                  # Historical ranking replayer

scripts/
├── backfill_sprint7_traceability.py
└── init_regime_policy_presets.py

migrations/versions/
├── 20260530_0007_sprint7_platform_traceability.py
└── 20260531_0008_sprint81_regime_policy.py
```

---

## 12. Domain Boundaries — Do Not Violate

| Layer | May change ranking? | May change validation formulas? |
|-------|--------------------|---------------------------------|
| Sprint 8.1 regime policy | **No** | **No** |
| Sprint 7 traceability | **No** (instrumentation only) | **No** |
| Sprint 8.2 factor analytics (planned) | **No** | **No** (read precomputed) |

Policy sits **after** ranking. Replay reads:

- `ranking_results` + `ranking_performance_snapshots`
- `ranking_validation_reports.regime_label`
- `validation_horizon_metrics` (precomputed spreads for E1/E2)

---

## 13. Traceability State (Post Sprint 7.1)

After backfill, expect approximately:

| Table | ~Rows |
|-------|------:|
| `ranking_factor_contributions` | 1.18M |
| `validation_horizon_metrics` | 1,636 |
| `regime_history` | 348 |
| `run_lineage_records` | 409 |

Verification SQL: `docs/sprint71-traceability-operationalization.md`

---

## 14. What NOT To Do

1. Add new ranking factors before Sprint 8.2 factor IC analytics
2. Wire regime policy into live ranking or paper trading (8.1 is research only)
3. Embed business config in Alembic migrations (use preset loader / API)
4. Use `SessionLocal` in scripts
5. Pool 100k+ stock-days through `compute_full_horizon_metrics`
6. Commit without running `pytest`

---

## 15. Related Documentation Index

| Doc | Content |
|-----|---------|
| `README.md` | **Documentation index** (this folder) |
| `PROJECT_MASTER.md` | Executive summary |
| `AI_CONTEXT.md` | AI onboarding |
| `ARCHITECTURE.md` | System design |
| `DATABASE_SCHEMA.md` | Tables + migrations |
| `API_REFERENCE.md` | Endpoints |
| `DECISION_LOG.md` | ADRs |
| `ROADMAP.md` | Future sprints |
| `SPRINT_HISTORY.md` | Completed work |
| `domain-boundaries.md` | Domain rules |

---

## 16. Takeover Checklist

- [ ] `git checkout feature/sprint8 && git pull`
- [ ] `alembic upgrade head` → head is `20260531_0008`
- [ ] `pytest` → 150 passed
- [ ] `python scripts/init_regime_policy_presets.py` → 4 configs
- [ ] Confirm traceability row counts (§12)
- [ ] Run regime backtest; confirm experiment completes
- [ ] Fill `docs/sprint81-results-template.md` with results
- [ ] Read `DECISION_LOG.md` ADR-016 through ADR-019 before changing policy layer
