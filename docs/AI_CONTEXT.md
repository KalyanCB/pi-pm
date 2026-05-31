# Pi-PM — AI Context

**Purpose:** Onboard any AI assistant (ChatGPT, Claude, Gemini, Cursor) to Pi-PM without reading source code.

**Last updated:** 2026-06-01  
**Takeover entry point:** `docs/HANDOFF.md`

---

## What Is Pi-PM?

Pi-PM is a **Personal Intelligence Portfolio Manager** — a Python/FastAPI backend for ranking Indian NSE equities using deterministic factor models, validating signal predictive power, evaluating regime-aware policies (research), and (eventually) managing a personal portfolio with LLM-assisted research.

**Critical rule:** LLMs never rank securities, determine position sizes, approve trades, or override risk controls. All money decisions are deterministic.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| API | FastAPI 0.115+ |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic (head: `20260531_0008`) |
| Validation | Pydantic v2 |
| Market data | Yahoo Finance (`yfinance`) |
| Tests | pytest (**150 tests**) |
| Deployment | Docker Compose |

**Repo:** `/Users/kalyancb/pi-pm`  
**API prefix:** `/api/v1`  
**Active branch:** `feature/sprint8`

---

## Core Pipeline

```
Market Data Ingest
  → Universe Filter
  → Ranking Engine
  → Validation (IC, deciles, regime)
  → Traceability (Sprint 7)
  → Regime Policy Replay (Sprint 8.1, research only)
```

---

## Domain Boundaries (Do Not Violate)

| Domain | Package | Must NOT |
|--------|---------|----------|
| Universe | `app/universe/` | Score or rank |
| Ranking | `app/ranking/` | Filter universe or persist |
| Validation | `app/validation/` | Change ranking logic |
| Regime policy | `app/regime_policy/` | Rerank, change factors, live trading |
| Services | `app/services/` | Factor formulas in API layer |

---

## Key Configuration Defaults

| Setting | Default | Gotcha |
|---------|---------|--------|
| `ranking_default_universe_code` | `PI_PM_CORE` | **Use `NIFTY_500` for full universe** |
| `ranking_default_strategy` | `momentum_v1` | Research uses `breakout_v1` |
| `validation_high_vol_threshold` | 0.20 | Regime classification |

---

## Ranking Strategies

### `momentum_v1` (1.0.0)

- 201-day history, 4 factors
- `app/ranking/strategies/momentum_v1.py`

### `breakout_v1` (1.0.0)

- 252-day history, 8 factors
- `app/ranking/strategies/breakout_v1.py`
- Regime research shows alpha mainly in `BULL_LOW_VOL` at 20d

---

## Validation & Traceability

### Per-run validation (Sprint 4.2)

- Horizons: 5/10/20/60 trading days
- Regime: `{BULL|BEAR}_{LOW_VOL|HIGH_VOL}` via MA200 + vol
- Tables: `ranking_validation_reports`, `ranking_performance_snapshots`

### Traceability (Sprint 7 / 7.1)

- `ranking_factor_contributions`, `validation_horizon_metrics`, `regime_history`, `run_lineage_records`
- Backfill: `scripts/backfill_sprint7_traceability.py --all`
- Reuse paths call `ensure_*` — see `docs/sprint71-traceability-operationalization.md`

### Full-universe campaigns (Sprint 6.1)

- `FullUniverseValidationService` — backfill rankings + validate + pool metrics
- **Warning:** O(n²) hit rate in campaign aggregation at scale

---

## Regime Policy (Sprint 8.1)

Research-only layer. **Not wired to live ranking.**

| Component | Path |
|-----------|------|
| Engine | `app/regime_policy/engine.py` |
| Replay | `app/regime_policy/replay.py` |
| Service | `app/services/regime_policy_service.py` |
| API | `/api/v1/regime-policy/*` |
| Presets | `scripts/init_regime_policy_presets.py` |

**Policies:** E1 baseline, E2 hard gate, E3 soft gate, E4 threshold (experimental)

**Backtest hang fix (8.1.1):** Use `compute_pooled_period_metrics`, not `compute_full_horizon_metrics` on pooled 200k+ rows. See `docs/HANDOFF.md` §9.

**Replay zero-metrics fix (8.1.2):** ALLOW days excluded when snapshot returns NULL — E1/E2 fall back to `validation_horizon_metrics`. See `docs/HANDOFF.md` §10.

---

## Database Session Pattern (Scripts)

```python
from app.core.config import get_settings
from app.db.session import get_session_factory

get_settings()
db = get_session_factory()()
try:
    ...
    db.commit()
finally:
    db.close()
```

**There is no `SessionLocal` export.**

---

## API Groups

| Group | Prefix | Sprint |
|-------|--------|--------|
| Health, stocks, market-data, rankings, backtest, validation | various | 1–6 |
| Observability | `/observability` | 7 |
| Regime policy | `/regime-policy` | 8.1 |

Full catalog: `docs/API_REFERENCE.md`

---

## Sprint Status

| Sprint | Status |
|--------|--------|
| 1–6.1 | Complete |
| 7 / 7.1 | Complete |
| 8.1 | Complete (regime policy research) |
| 8.2+ | Planned (factor IC, AI agent) |

---

## What NOT to Do

1. Do not modify ranking/validation unless explicitly scoped
2. Do not wire regime policy into production ranking or paper trades
3. Do not use `SessionLocal` in scripts
4. Do not pool 100k+ rows through `compute_full_horizon_metrics`
5. Do not omit `universe_code: NIFTY_500`
6. Do not assume Docker has latest code without rebuild

---

## Key Files

```
app/regime_policy/          # Sprint 8.1 (policy only)
app/services/traceability_service.py
app/services/regime_policy_service.py
app/api/v1/observability.py
app/api/v1/regime_policy.py
scripts/backfill_sprint7_traceability.py
scripts/init_regime_policy_presets.py
migrations/versions/20260531_0008_sprint81_regime_policy.py
```

---

## Documentation Index

| Doc | Use |
|-----|-----|
| `HANDOFF.md` | **Start here** for takeover |
| `PROJECT_MASTER.md` | Executive summary |
| `ARCHITECTURE.md` | Diagrams + layers |
| `DATABASE_SCHEMA.md` | Tables |
| `API_REFERENCE.md` | Endpoints |
| `SPRINT_HISTORY.md` | Completed sprints |
| `DECISION_LOG.md` | ADRs |
| `sprint81-regime-aware-trading.md` | Regime backtest runbook |
