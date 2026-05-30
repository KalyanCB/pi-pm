# Pi-PM

Personal Intelligence Portfolio Manager — foundation layer.

## Stack

- Python 3.12+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Alembic
- Pydantic Settings
- Docker

## Quick start

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up --build
```

API: http://localhost:8000/api/v1/health

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

docker compose -f docker/docker-compose.yml up db -d
./scripts/init_db.sh
uvicorn app.main:app --reload
```

## Project layout

```
app/
├── api/          # FastAPI routes
├── core/         # Settings, logging, constants
├── db/           # SQLAlchemy base and session management
├── models/       # ORM models (system of record)
├── schemas/      # Pydantic DTOs (future)
├── services/     # Application layer (future)
├── workflows/    # LangGraph orchestration (future)
├── agents/       # LLM research agents (future)
├── ranking/      # Deterministic ranking (future)
├── portfolio/    # Deterministic sizing (future)
├── risk/         # Risk gates (future)
├── execution/    # Trade execution (future)
├── research/     # Research domain (future)
└── monitoring/   # Observability (future)
```

## Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Tests

```bash
pytest
```
