# Pi-PM Migration Guide

Guide for managing Alembic database migrations in Pi-PM.

## Overview

Pi-PM uses [Alembic](https://alembic.sqlalchemy.org/) with migrations in `migrations/versions/`. Configuration is in `alembic.ini` and `migrations/env.py`.

## Common Commands

```bash
# Show current revision
alembic current

# Show migration history
alembic history -v

# Apply all pending migrations
alembic upgrade head

# Downgrade one revision
alembic downgrade -1

# Generate SQL without applying (offline)
alembic upgrade head --sql
```

## Creating a New Migration

```bash
alembic revision -m "describe_change"
# Edit the generated file in migrations/versions/
alembic upgrade head  # Apply locally
pytest                # Verify tests pass
```

### Naming Convention

Files follow: `YYYYMMDD_NNNN_description.py` (e.g., `20260609_0018_see_v2_metrics.py`).

## Validation

Run before committing migration changes:

```bash
python scripts/validate_migrations.py
```

This verifies:

1. Exactly one migration head exists (no branch conflicts)
2. Migration history is readable

CI additionally runs `alembic upgrade head` against PostgreSQL 16.

## Merge Migrations

If multiple heads exist after parallel development:

```bash
alembic heads                    # List heads
alembic merge -m "merge_heads" <rev1> <rev2>
python scripts/validate_migrations.py
```

## Model Registration

New SQLAlchemy models must be imported in `migrations/env.py` so autogenerate detects them:

```python
from app.models import (
    # ... existing imports ...
    NewModel,
)
```

## Best Practices

1. **One concern per migration** — avoid mixing unrelated schema changes
2. **Backward compatible when possible** — add columns as nullable first
3. **No data loss without explicit review** — document destructive changes
4. **Test locally** — apply upgrade and downgrade before PR
5. **Never edit applied migrations** — create a new migration instead

## Production Migration Procedure

1. Take database backup
2. Run during low-traffic window
3. Apply: `alembic upgrade head`
4. Verify: `alembic current`
5. Check `/api/v1/health/ready`
6. Monitor logs for 15 minutes

See [Release Checklist](./release-checklist.md) and [Rollback Guide](./rollback-guide.md).

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Multiple heads | Create merge migration |
| Revision not found | Ensure all migration files deployed |
| Upgrade fails mid-way | Check transaction state; may need manual fix + downgrade |
| Model/table mismatch | Verify model imports in `migrations/env.py` |
