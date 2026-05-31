# Pi-PM — AI Context

**Purpose:** Onboard any AI assistant (ChatGPT, Claude, Gemini, Cursor) to Pi-PM without reading source code.

**Last updated:** 2026-05-31

---

## What Is Pi-PM?

Pi-PM is a **Personal Intelligence Portfolio Manager** — a Python/FastAPI backend for ranking Indian NSE equities using deterministic factor models, validating signal predictive power, and (eventually) managing a personal portfolio with LLM-assisted research.

**Critical rule:** LLMs never rank securities, determine position sizes, approve trades, or override risk controls. All money decisions are deterministic.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| API | FastAPI 0.115+ |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Market data | Yahoo Finance (`yfinance`) |
| Tests | pytest (121 tests) |
| Deployment | Docker Compose |

**Repo root:** `/Users/kalyancb/pi-pm`  
**API prefix:** `/api/v1`  
**Default DB:** `postgresql+psycopg://pipm:pipm@localhost:5432/pipm`

---

## Core Pipeline (Memorize This)

```
Market Data Ingest
  → Universe Filter (eligibility: history, ADTV, price, active status)
  → Ranking Engine (factor scores → percentile normalize → composite score → rank)
  → Persist ranking_runs + ranking_results + performance_snapshots
  → Validation (forward returns 5/10/20/60d → IC, deciles, hit rates)
  → Full-Universe Campaign (pool all days → aggregate metrics)
```

---

## Domain Boundaries (Do Not Violate)

| Domain | Package | Owns | Must NOT |
|--------|---------|------|----------|
| Universe | `app/universe/` | Eligibility filtering, exclusion codes | Score or rank stocks |
| Ranking | `app/ranking/` | Factors, normalization, scoring, hashing | Filter universe or persist |
| Market data cache | `app/market_data/` | Session-scoped bar loading | Business logic |
| Validation | `app/validation/` | Forward returns, IC, deciles, regimes | Ranking logic |
| Services | `app/services/` | Orchestration, transactions, defaults | Factor formulas |
| API | `app/api/` | HTTP contracts | Business logic |

---

## Key Configuration Defaults

These come from `app/core/config.py` and `.env`:

| Setting | Default | ⚠️ Gotcha |
|---------|---------|-----------|
| `ranking_default_universe_code` | `PI_PM_CORE` | Only ~15 stocks! Use `NIFTY_500` for full universe |
| `ranking_default_strategy` | `momentum_v1` | Sprint 6.1 validates `breakout_v1` |
| `ranking_default_benchmark` | `^NSEI` | Required for relative strength factors |
| `ranking_min_history_days` | 63 | Universe filter minimum |
| `validation_high_vol_threshold` | 0.20 | Regime classification |

---

## Ranking Strategies

### `momentum_v1` (1.0.0) — Default

- **History:** 201 days (MA200 + 1)
- **Factors:** vol_adj_momentum (40%), volume_expansion (25%), trend_quality (20%), relative_strength (15%)
- **File:** `app/ranking/strategies/momentum_v1.py`

### `breakout_v1` (1.0.0) — Sprint 5

- **History:** 252 days
- **Factors:** vol_adj_momentum (20%), relative_strength (15%), trend_quality (10%), volume_surge (15%), high_proximity (15%), atr_expansion (10%), rs_acceleration (5%), consolidation_breakout (10%)
- **File:** `app/ranking/strategies/breakout_v1.py`
- **Benchmark-dependent:** `relative_strength`, `relative_strength_acceleration` — excluded with weight redistribution if benchmark missing

Registry: `app/ranking/registry.py`

---

## Universes

| Code | Description | ~Members |
|------|-------------|----------|
| `NIFTY_500` | NSE NIFTY 500 | 504 |
| `NIFTY_100` | NSE NIFTY 100 | Seeded |
| `NIFTY_50` | NSE NIFTY 50 | Seeded |
| `PI_PM_CORE` | Small core watchlist | ~15 |

Bootstrap: `UniverseBootstrapService` + `data/nifty500_constituents.csv`

---

## Validation Framework

### Per-Run Validation (Sprint 4.2)

- Computes forward returns at 5/10/20/60 **trading days**
- Classifies regime: BULL/BEAR (SMA200) × HIGH_VOL/LOW_VOL (20d vol)
- Metrics: Spearman IC, decile spread, hit rates
- Tables: `ranking_validation_reports`, `ranking_performance_snapshots`

### Full-Universe Campaign (Sprint 6.1)

- Orchestrates: backfill rankings → validate each day → pool all stock-day observations
- Metrics: Pearson IC, Spearman Rank IC, top/bottom decile, spread, top 20/50, decile win rates, monotonicity
- Tables: `full_universe_validation_campaigns`, `_runs`, `_metrics`, `_deciles`
- Service: `FullUniverseValidationService`
- Default: `NIFTY_500` + `breakout_v1`

---

## Database Tables (16 Total)

**Core:** `stocks`, `market_data`, `stock_universes`, `universe_memberships`  
**Ingestion:** `market_data_ingestion_runs`  
**Ranking:** `ranking_runs`, `ranking_results`, `ranking_performance_snapshots`  
**Validation:** `ranking_validation_reports`  
**Campaign:** `full_universe_validation_campaigns`, `_runs`, `_metrics`, `_deciles`  
**Future:** `portfolio_positions`, `paper_trades`, `research_reports`

See `docs/DATABASE_SCHEMA.md` for full details.

---

## API Endpoints (21)

| Group | Key Endpoints |
|-------|---------------|
| Health | `GET /health` |
| Stocks | `GET /stocks`, `GET /stocks/{symbol}/market-data` |
| Market data | `POST /market-data/ingest` |
| Rankings | `POST /rankings/run`, `GET /rankings/latest`, `GET /rankings/{id}/top` |
| Backtest | `POST /backtest/generate-rankings`, `GET /backtest/summary` |
| Validation | `POST /validation/backfill`, `POST /validation/runs/{id}/compute`, `GET /validation/summary` |
| Full-universe | `POST /validation/full-universe/run`, `GET .../summary`, `GET .../deciles` |

See `docs/API_REFERENCE.md` for request/response examples.

---

## Idempotency

Ranking runs use `inputs_hash` (SHA-256 of strategy + universe + date + filter config + benchmark). Identical inputs → reuse completed run. Failed runs have `inputs_hash = NULL` and can be retried.

---

## Common Tasks

### Run a ranking (full universe)

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

### Run full-universe validation campaign

```bash
curl -X POST http://localhost:8000/api/v1/validation/full-universe/run \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-01", "end_date": "2025-05-31"}'
```

### Apply migrations

```bash
alembic upgrade head
```

### Run tests

```bash
pytest
```

---

## Sprint Status

| Sprint | Feature | Status |
|--------|---------|--------|
| 1 | Foundation | ✅ |
| 2 | Market intelligence | ✅ |
| 3 | Ranking engine | ✅ |
| 3.1 | Ranking hardening | ✅ |
| 4.1 | Historical backtest | ✅ |
| 4.2 | Signal validation | ✅ |
| 5.1 | NIFTY 500 + breakout_v1 | ✅ |
| 6.1 | Full-universe validation | ✅ Code; ⏳ Results TBD |
| 7+ | Portfolio, LLM agents | ⏳ Planned |

---

## Current Branch and Git State

- **Branch:** `feature/sprint6`
- **Base:** `main` @ Sprint 5 merge
- **Note:** Sprint 6.1 code may be uncommitted — check `git status` before assuming CI/deployment parity

---

## What NOT to Do

1. **Do not add new signals** until Sprint 6.1 validation answers go/no-go questions
2. **Do not use LLMs for ranking/sizing/trades**
3. **Do not omit `universe_code`** — defaults to tiny `PI_PM_CORE`
4. **Do not assume Docker has latest code** — rebuild after changes
5. **Do not put business logic in API routes** — use services

---

## Key Files Quick Map

```
app/
├── api/v1/           # HTTP routes
├── api/deps.py       # Dependency injection
├── core/config.py    # Settings
├── core/constants.py # Enums, strategy names
├── db/repositories/  # Data access
├── models/           # SQLAlchemy ORM
├── schemas/          # Pydantic DTOs
├── services/         # Orchestration
├── ranking/          # Engine + strategies + factors
├── universe/         # Filter engine + NIFTY loader
├── validation/       # IC, deciles, campaigns
├── backtest/         # Historical replayer
└── providers/yahoo/  # Yahoo client

migrations/versions/  # Alembic migrations
tests/                # pytest suite
docs/                 # Documentation (this file)
scripts/              # Pipeline utilities
data/                 # NIFTY 500 CSV
```

---

## Related Documentation

- `docs/PROJECT_MASTER.md` — Executive overview
- `docs/ARCHITECTURE.md` — Diagrams and data flows
- `docs/DATABASE_SCHEMA.md` — All tables and relationships
- `docs/API_REFERENCE.md` — Endpoint catalog with examples
- `docs/SPRINT_HISTORY.md` — Completed sprint details
- `docs/ROADMAP.md` — Future plans
- `docs/DECISION_LOG.md` — Architectural decisions
