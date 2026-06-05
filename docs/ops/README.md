# Pi-PM Operations Documentation

Operational guides for deploying, releasing, and maintaining Pi-PM in production.

## Guides

| Guide | Description |
|-------|-------------|
| [Deployment Guide](./deployment-guide.md) | Environment setup, Docker deployment, health probes |
| [Release Checklist](./release-checklist.md) | Pre/post-release verification steps |
| [Rollback Guide](./rollback-guide.md) | Application and database rollback procedures |
| [Migration Guide](./migration-guide.md) | Alembic migration management |

## Track A Deliverables

| Document | Description |
|----------|-------------|
| [Architecture Review](./architecture-review.md) | Platform architecture assessment |
| [Test Report](./test-report.md) | Test suite status and coverage |
| [Production Readiness Scorecard](./production-readiness-scorecard.md) | Readiness scoring and gaps |

## Quick Reference

```bash
# Health checks
curl /api/v1/health/live
curl /api/v1/health/ready

# Validate migrations
python scripts/validate_migrations.py
alembic upgrade head

# Run tests with coverage
pytest --cov=app --cov-report=html -q
```
