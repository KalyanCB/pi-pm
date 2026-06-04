# Pi-PM — Developer & AI Handoff Guide

**Last updated:** 2026-06-04  
**Purpose:** Enable any developer, AI assistant, or LLM to take over Pi-PM without prior chat context.

---

## Start here

**Primary handoff (June 2026):** [`PLATFORM-HANDOFF-2026.md`](./PLATFORM-HANDOFF-2026.md)

That document is the single entry point: system map, production vs experimental, env vars, scripts index, SEE v2 / QRC / SQE / committee Phase 2, ranking research, daily runs pattern, PO decisions, and AI quickstart.

This file retains Sprint 8.x operational detail and gotchas not duplicated there.

| Item | Value |
|------|-------|
| Repo | `/Users/kalyancb/pi-pm` |
| **Active branch** | `feature/see-v2` |
| **Migration head** | `20260609_0018` |
| **Tests** | **312 passed** (`pytest`) |

---

## Read order (30-minute onboarding)

| Order | Document | Why |
|------:|----------|-----|
| 1 | [`PLATFORM-HANDOFF-2026.md`](./PLATFORM-HANDOFF-2026.md) | Current platform state |
| 2 | [`HANDOFF.md`](./HANDOFF.md) | This file — Sprint 8 gotchas |
| 3 | [`AI_CONTEXT.md`](./AI_CONTEXT.md) | Pipeline, defaults, anti-patterns |
| 4 | [`architecture.md`](./architecture.md) | Layers, diagrams |
| 5 | [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md) | Tables |
| 6 | [`API_REFERENCE.md`](./API_REFERENCE.md) | Endpoints |
| 7 | [`daily-nifty500-batch-runbook.md`](./daily-nifty500-batch-runbook.md) | Daily ops |
| 8 | [`args-implementation-plan.md`](./args-implementation-plan.md) | ARGS Phase 1 |

Full doc index: [`README.md`](./README.md)

---

## Core pipeline

```
Market Data Ingest (Yahoo)
  → Universe Filter → Ranking (breakout_v1 + momentum_v1)
  → Validation → Traceability (Sprint 7)
  → Regime Policy Replay (8.1, research) → Factor IC / Exit / Research Intel (8.2–8.5)
  → Daily batch orchestration (8.6)
  → ARGS governance (packets, committees, CRO) + SEE v2 + SQE observability
```

---

## Sprint status (summary)

| Area | Status |
|------|--------|
| 6.1–8.6 (validation, traceability, regime, factor, exit, daily batch) | **Complete** |
| ARGS Phase 1 + committee Phase 2 | **Complete** on `feature/see-v2` |
| SEE v2, SQE Phase 2, outcome attribution, ranking research | **Complete** (analytics / observability) |
| Ranking v2 calibration, QRC SQE default, committee Phase 3 | **PO decisions pending** |

Details: [`PLATFORM-HANDOFF-2026.md`](./PLATFORM-HANDOFF-2026.md) §2, §14, §17.

---

## Key research finding (Sprint 8+)

`breakout_v1` at **20-day horizon** appears alpha-positive mainly in **BULL_LOW_VOL**:

| Regime | avg IC | avg spread | n |
|--------|--------|------------|---|
| BULL_LOW_VOL | +0.0359 | +1.62% | 237 |
| BEAR_LOW_VOL | -0.0891 | -3.11% | 80 |
| BULL_HIGH_VOL | -0.1704 | -3.06% | 28 |
| BEAR_HIGH_VOL | -0.3738 | -11.30% | 4 |

Ranking **order** within top-20 is non-monotonic — see [`ranking-calibration-root-cause.md`](./ranking-calibration-root-cause.md).

---

## Environment setup

```bash
cd /Users/kalyancb/pi-pm
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
docker compose -f docker/docker-compose.yml up -d db
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Common operations

See [`PLATFORM-HANDOFF-2026.md`](./PLATFORM-HANDOFF-2026.md) §6 (scripts) and §15 (quickstart).

Quick refs:

```bash
python scripts/run_daily_nifty500_batch.py --assume-session-done
ARGS_QRC_USE_SQE=false python scripts/run_args_top20.py --as-of-date 2026-06-04
python scripts/generate_ranking_root_cause_reports.py
pytest tests/ -q
```

---

## Critical gotchas

| Gotcha | Fix |
|--------|-----|
| Default universe is `PI_PM_CORE` (~15 stocks) | Always pass `universe_code: NIFTY_500` |
| Docker serves stale code | Rebuild + restart API container |
| `SessionLocal` does not exist | Use `get_session_factory()()` in scripts |
| Ranking/validation logic is frozen unless scoped | Policy/ARGS layers post-ranking |
| Latest validation `insufficient_data` | Need forward bars (≥5 trading days); tail from ~2026-05-27 |
| `^NSEI` not ingested through target day | Rankings won't run for that date |
| Daily batch `already_current` skip | Use `force_from_date` + `force_regenerate_rankings` |
| Do not pool 100k+ rows through `compute_full_horizon_metrics` | O(n²) — use `compute_pooled_period_metrics` |

Sprint 8.1 backtest hang / zero metrics fixes remain in §9–§10 below (still valid).

---

## Sprint 8.1 backtest — known bug & fix

### Symptom

- Backtest hangs or experiment stuck `RUNNING`
- No `regime_backtest_runs` rows

### Root cause

`compute_full_horizon_metrics()` O(n²) on ~200k pooled rows + N+1 SQL.

### Fix (implemented)

| Change | File |
|--------|------|
| `compute_pooled_period_metrics()` | `app/regime_policy/metrics.py` |
| `batch_load_scored_returns_by_run()` | `app/regime_policy/scored_returns_loader.py` |
| Horizon-metrics fallback for E1/E2 | `app/regime_policy/replay.py` |

---

## Sprint 8.1 replay — ALLOW but zero metrics (8.1.2)

Replay now falls back to precomputed `validation_horizon_metrics` when snapshot returns are NULL. Log events: `regime_replay_day_included_precomputed`. Verify via SQL in original §10 or [`sprint81-regime-aware-trading.md`](./sprint81-regime-aware-trading.md).

---

## Domain boundaries

| Layer | May change ranking? | May change validation? |
|-------|--------------------|-----------------------|
| Regime policy (8.1) | **No** | **No** |
| Traceability (7) | **No** | **No** |
| Factor / exit analytics | **No** | **No** (read precomputed) |
| ARGS / committees | **No** | **No** |

---

## Takeover checklist

- [ ] Read [`PLATFORM-HANDOFF-2026.md`](./PLATFORM-HANDOFF-2026.md)
- [ ] `git checkout feature/see-v2` · `alembic upgrade head` → `20260609_0018`
- [ ] `pytest` → 312 passed
- [ ] Review [`dailyruns/04-jun-2026/`](./dailyruns/04-jun-2026/)
- [ ] Read [`DECISION_LOG.md`](./DECISION_LOG.md) before policy/ARGS changes
