# Step 00 — Prerequisites (2026-06-04)

**Checked at:** pipeline start (local ops run)

## Docker

```
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

| Service | Status |
|---------|--------|
| docker-api-1 | Up 25h, `0.0.0.0:8000->8000` |
| docker-db-1 | Up 25h **(healthy)**, `0.0.0.0:5432->5432` |

## API health

`GET http://127.0.0.1:8000/api/v1/health`

```json
{"status":"ok","service":"pi-pm","environment":"development","database":"connected"}
```

OpenAPI `/docs` returned HTTP 200.

## DB connectivity

Confirmed via health payload `"database":"connected"` (PostgreSQL 16 in Docker).

## Notes

- Operational run only; no code changes to ranking/ARGS production logic.
- Benchmark `^NSEI` ingest reminder applied per Jun-3 runbook if rankings gap on target day.
