# Pi-PM

Personal Intelligence Portfolio Manager — deterministic ranking, validation, traceability, and regime policy research for Indian NSE equities.

## Documentation (start here)

| Doc | Audience |
|-----|----------|
| **[context/AGENTS.md](context/AGENTS.md)** | **AI & developers — read first** (Cursor, Claude Code, Devin) |
| [context/generated/PLATFORM_STATE.md](context/generated/PLATFORM_STATE.md) | Live branch, tests, migration head |
| [context/generated/IMPLEMENTATION_STATUS.md](context/generated/IMPLEMENTATION_STATUS.md) | Designed / planned / implemented / gaps |
| [context/canonical/INDEX.md](context/canonical/INDEX.md) | ADRs & PRDs (human decisions) |

Regenerate: `uv run python scripts/generate_context.py`

Legacy `docs/` is being retired — prefer `context/` for current truth.

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
