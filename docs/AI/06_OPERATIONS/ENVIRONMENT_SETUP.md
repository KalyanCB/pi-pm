# Environment Setup

---

## Prerequisites

- Python 3.12+
- Docker (for Postgres)
- Git

---

## Local development

```bash
cd /Users/kalyancb/pi-pm
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d db
alembic upgrade head   # → 20260609_0018
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pytest tests/ -q
```

---

## URLs

| Resource | URL |
|----------|-----|
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/api/v1/health |

---

## Key environment variables

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `postgresql+psycopg://pipm:pipm@localhost:5432/pipm` | |
| `RANKING_DEFAULT_UNIVERSE_CODE` | `PI_PM_CORE` | **Set `NIFTY_500` for ops** |
| `RANKING_DEFAULT_BENCHMARK` | `^NSEI` | Must be ingested |
| `RANKING_DEFAULT_STRATEGY` | `momentum_v1` | Batch runs both |
| `VALIDATION_HIGH_VOL_THRESHOLD` | `0.20` | Regime split |
| `ARGS_LLM_PROVIDER` | `mock` | `openai` for live committees |
| `ARGS_QRC_USE_SQE` | **`false`** | Experimental QRC path |

Full table: [PLATFORM-HANDOFF-2026.md §4.2](../../PLATFORM-HANDOFF-2026.md).

---

## Docker full stack

```bash
docker compose -f docker/docker-compose.yml up --build
```

Files: `docker/Dockerfile`, `docker/docker-compose.yml`, `docker/docker-compose.dev.yml`.

---

## Database

- User/db: `pipm` / `pipm`
- Port: `5432`
- Migrations: `alembic upgrade head`

---

## Branch

```bash
git checkout feature/see-v2
```

Legacy docs may reference older branches; trust [AI_AGENT_HANDOVER.md](../12_HANDOVER/AI_AGENT_HANDOVER.md) for current.
