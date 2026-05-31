# Pi-PM

Personal Intelligence Portfolio Manager — deterministic ranking, validation, traceability, and regime policy research for Indian NSE equities.

## Documentation (start here)

| Doc | Audience |
|-----|----------|
| **[docs/README.md](docs/README.md)** | Full documentation index |
| **[docs/HANDOFF.md](docs/HANDOFF.md)** | **Developers & AI takeover — read first** |
| [docs/AI_CONTEXT.md](docs/AI_CONTEXT.md) | AI assistant onboarding |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | All endpoints |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | Tables & migrations |

**Current branch:** `feature/sprint8` | **Migration head:** `20260531_0008` | **Tests:** 150

## Stack

- Python 3.12+, FastAPI, PostgreSQL 16, SQLAlchemy 2.0, Alembic, Pydantic v2, Docker

## Quick start

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up --build
```

- API: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

docker compose -f docker/docker-compose.yml up db -d
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

## Key operations

```bash
# Traceability backfill (if needed)
python scripts/backfill_sprint7_traceability.py --all

# Regime policy presets (Sprint 8.1)
python scripts/init_regime_policy_presets.py
```

## Project layout

```
app/
├── api/v1/           # REST routes (rankings, validation, observability, regime-policy)
├── services/         # Orchestration
├── ranking/          # Deterministic ranking engine
├── validation/       # IC, deciles, regimes
├── regime_policy/    # Sprint 8.1 policy replay (research only)
├── db/repositories/  # Data access
└── models/           # SQLAlchemy ORM

docs/                 # Full documentation package
scripts/              # Backfill, presets, pipelines
migrations/versions/  # Alembic (0001 → 0008)
```

## Principles

1. LLMs never rank securities or determine position sizes
2. All money-related logic is deterministic and auditable
3. Policy/regime layers sit **after** ranking — they do not change factors or weights

See [docs/domain-boundaries.md](docs/domain-boundaries.md).
