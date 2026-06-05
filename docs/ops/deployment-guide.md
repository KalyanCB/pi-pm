# Pi-PM Deployment Guide

Operational guide for deploying Pi-PM to staging and production environments.

## Prerequisites

| Component | Version |
|-----------|---------|
| Python | 3.12+ |
| PostgreSQL | 16+ |
| Docker / Docker Compose | Latest stable |

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_ENV` | Yes | `development`, `staging`, or `production` |
| `DEBUG` | Yes | Must be `false` in production |
| `LOG_LEVEL` | No | Default `INFO` |
| `DATABASE_URL` | Yes | PostgreSQL connection string |

See [`.env.example`](../../.env.example) for full list including ranking and ARGS LLM settings.

## Docker Deployment (Recommended)

```bash
cp .env.example .env
# Set APP_ENV=production, DEBUG=false, DATABASE_URL as needed

docker compose -f docker/docker-compose.yml up --build -d
docker compose -f docker/docker-compose.yml exec api alembic upgrade head
```

Verify deployment:

```bash
curl -s http://localhost:8000/api/v1/health/ready | jq .
curl -s http://localhost:8000/api/v1/health/live
```

## Manual Deployment

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
export APP_ENV=production DEBUG=false
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Health Probes

| Endpoint | Purpose | Expected |
|----------|---------|----------|
| `GET /api/v1/health/live` | Liveness | Always `200` when process is up |
| `GET /api/v1/health/ready` | Readiness | `200` when DB connected; `503` otherwise |
| `GET /api/v1/health` | Detailed status | `200` with dependency checks |

Configure Kubernetes/load balancer probes:

- **Liveness:** `/api/v1/health/live` — interval 10s
- **Readiness:** `/api/v1/health/ready` — interval 5s

## Startup Validation

On application start, Pi-PM validates:

1. Database connectivity (`SELECT 1`)
2. Production config (`DEBUG=false` when `APP_ENV=production`)

In production, startup fails fast if validation fails. In development, warnings are logged.

## Observability

- **Structured logging:** JSON logs in `production`, `staging`, and `test` environments
- **Correlation IDs:** Pass `X-Correlation-ID` header; echoed in response
- **Request tracing:** Each request receives `X-Request-ID` in response headers

## CI/CD

GitHub Actions workflows:

- **PR Validation** (`.github/workflows/pr-validation.yml`) — runs on pull requests
- **Main Branch CI** (`.github/workflows/main.yml`) — runs on push to `main`

Both execute: ruff lint, pytest with coverage, and migration validation against PostgreSQL 16.

## Post-Deploy Checklist

1. Health probes return `200`
2. `alembic current` matches expected revision
3. Smoke test: `GET /api/v1/stocks` returns data
4. Review application logs for startup validation success

See also: [Release Checklist](./release-checklist.md) | [Rollback Guide](./rollback-guide.md)
