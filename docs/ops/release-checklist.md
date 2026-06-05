# Pi-PM Release Checklist

Use this checklist before every production release.

## Pre-Release

- [ ] All CI checks green on the release branch (lint, test, migrations)
- [ ] Test suite: 524+ tests passing locally
- [ ] Migration head is single (run `python scripts/validate_migrations.py`)
- [ ] Review [DECISION_LOG.md](../DECISION_LOG.md) for breaking changes
- [ ] Confirm no changes to protected business logic:
  - Ranking Engine
  - Validation Engine
  - Recommendation Engine logic
  - Portfolio Engine business rules
  - Investment Committee logic

## Database

- [ ] New migrations reviewed for backward compatibility
- [ ] Migration tested against production-like data volume (if applicable)
- [ ] Rollback plan documented (see [Rollback Guide](./rollback-guide.md))
- [ ] Backup taken before migration (`pg_dump` or managed backup snapshot)

## Configuration

- [ ] `APP_ENV=production`
- [ ] `DEBUG=false`
- [ ] `DATABASE_URL` points to production database
- [ ] Secrets rotated if this release touches credentials
- [ ] ARGS LLM provider keys configured (if committee features enabled)

## Deployment

- [ ] Deploy application image/binary
- [ ] Run `alembic upgrade head`
- [ ] Verify `/api/v1/health/ready` returns `200`
- [ ] Verify `/api/v1/health/live` returns `200`

## Post-Release Validation

- [ ] Smoke test critical endpoints:
  - `GET /api/v1/health`
  - `GET /api/v1/rankings/latest`
  - `GET /api/v1/recommendations/daily`
- [ ] Check structured logs for errors in first 15 minutes
- [ ] Confirm correlation IDs present in log entries
- [ ] Monitor daily batch run (if scheduled post-release)

## Rollback Triggers

Initiate rollback if any of the following occur within 30 minutes:

- Readiness probe failing consistently
- Error rate spike > 5% on core endpoints
- Database migration caused data integrity issues
- Critical business workflow blocked

See [Rollback Guide](./rollback-guide.md).

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Platform Engineer | | | |
| Release Owner | | | |
