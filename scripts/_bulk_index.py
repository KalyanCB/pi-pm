"""Drop-then-rebuild index helper for write-heavy bulk loads.

Random-UUID indexes (ranking_run_id, stock_id) on a table larger than shared_buffers
degrade inserts to O(log N) with cache misses — the load gets *slower day by day* as the
B-tree outgrows cache and random writes spill to disk. Dropping the indexes turns inserts
into flat sequential heap appends (O(1), size-independent); rebuilding after is a single
sorted bulk build (uses maintenance_work_mem + parallel workers, not the tiny cache).

Scope (deliberately conservative):
  - DROP/REBUILD: UNIQUE constraints + plain (non-constraint) indexes.
  - KEEP: the PRIMARY KEY (often referenced by an inbound FK → can't drop without surgery)
    and all FOREIGN KEYs.
  - `skip`: names to drop but NOT recreate (e.g. a redundant duplicate index).

Safe under parallel load when workers write disjoint key-spaces (bulk_rank: disjoint
run_ids per worker). The rebuild's CREATE UNIQUE re-validates, so any dupe fails loudly.
"""
from __future__ import annotations

from sqlalchemy import text


def capture(db, table: str):
    """Return (unique_constraints, plain_indexes) as [(name, definition), ...]."""
    cons = db.execute(text(
        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid = :t::regclass AND contype = 'u'"
    ), {"t": table}).fetchall()
    idx = db.execute(text(
        "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = :t "
        "AND indexname NOT IN (SELECT conname FROM pg_constraint WHERE conrelid = :t::regclass)"
    ), {"t": table}).fetchall()
    return [(c[0], c[1]) for c in cons], [(i[0], i[1]) for i in idx]


def drop(db, table: str, cons, idx) -> None:
    for name, _ in idx:
        db.execute(text(f"DROP INDEX IF EXISTS {name}"))
    for name, _ in cons:
        db.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}"))
    db.commit()


def restore(db, table: str, cons, idx, *, skip=(), mwm: str = "2GB", parallel: int = 4) -> None:
    """Rebuild dropped indexes/constraints (one sorted bulk build each), then ANALYZE.
    Names in `skip` are not recreated (e.g. a redundant duplicate index)."""
    skip = set(skip)
    db.execute(text(f"SET maintenance_work_mem = '{mwm}'"))
    db.execute(text(f"SET max_parallel_maintenance_workers = {parallel}"))
    for name, ddl in idx:
        if name not in skip:
            db.execute(text(ddl))
    for name, ddl in cons:
        if name not in skip:
            db.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT {name} {ddl}"))
    db.commit()
    db.execute(text(f"ANALYZE {table}"))
    db.commit()
