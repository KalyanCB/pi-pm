# Pi-PM Rollback Guide

Procedures for rolling back a failed Pi-PM deployment.

## Decision Matrix

| Scenario | Rollback Type | Action |
|----------|---------------|--------|
| App bug, DB unchanged | Application only | Redeploy previous image/tag |
| Migration caused issues | App + DB | Downgrade migration + redeploy |
| Config error | Config only | Revert env vars, restart |
| Data corruption | Full restore | Restore DB backup + redeploy |

## Application Rollback

### Docker

```bash
# Tag previous known-good image
docker compose -f docker/docker-compose.yml down
# Update docker-compose or image tag to previous version
docker compose -f docker/docker-compose.yml up -d
```

### Manual

```bash
git checkout <previous-tag>
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Verify:

```bash
curl -s http://localhost:8000/api/v1/health/ready
```

## Database Migration Rollback

**Warning:** Only downgrade if the migration has not introduced irreversible schema changes (e.g., dropped columns with data loss).

```bash
# Identify current revision
alembic current

# Downgrade one step
alembic downgrade -1

# Or downgrade to specific revision
alembic downgrade <revision_id>
```

After downgrade, redeploy the matching application version.

## Full Database Restore

When migration rollback is unsafe or data was corrupted:

```bash
# Stop application
docker compose -f docker/docker-compose.yml stop api

# Restore from backup (example)
pg_restore -h localhost -U pipm -d pipm --clean --if-exists backup.dump

# Redeploy previous application version
docker compose -f docker/docker-compose.yml up -d api
```

## Verification After Rollback

1. `/api/v1/health/ready` → `200`
2. `alembic current` matches expected revision for rolled-back version
3. Smoke test rankings and recommendations endpoints
4. Review logs for startup validation success

## Communication

Document in incident channel:

- Rollback reason
- Time of rollback
- Versions involved (app + migration)
- Data impact assessment
- Follow-up action items

## Prevention

- Always take DB backup before production migrations
- Use [Release Checklist](./release-checklist.md) for every deploy
- Test migrations in staging with production-like data first
