#!/usr/bin/env python
"""Delete duplicate rec run results using 10 parallel threads, one rec_run_id per commit."""
import sys
import threading
from sqlalchemy import create_engine, text

# Fetch all stale rec_run_ids first
eng = create_engine('postgresql+psycopg://pipm:pipm@localhost:5432/pipm')
with eng.connect() as conn:
    rec_run_ids = [r[0] for r in conn.execute(text("""
        SELECT id FROM recommendation_runs WHERE ranking_run_id IN (
            SELECT id FROM ranking_runs WHERE as_of_date >= '2022-01-01'
            AND id NOT IN (
                SELECT DISTINCT ON (as_of_date, strategy_name) id FROM ranking_runs
                WHERE as_of_date >= '2022-01-01'
                ORDER BY as_of_date, strategy_name, created_at DESC
            )
        )
    """)).fetchall()]
    conn.commit()

total_ids = len(rec_run_ids)
print(f"Rec run IDs to delete: {total_ids}", flush=True)

lock = threading.Lock()
counter = [0]
total_rows = [0]

def delete_rec_run(rid):
    with eng.connect() as conn:
        n = conn.execute(text(
            "DELETE FROM recommendation_results WHERE recommendation_run_id = :id"
        ), {"id": rid}).rowcount
        conn.commit()
    with lock:
        counter[0] += 1
        total_rows[0] += n
        print(f"  [{counter[0]}/{total_ids}] {rid}: -{n} rows (total={total_rows[0]})", flush=True)

# Split into 10 threads
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=10) as ex:
    ex.map(delete_rec_run, rec_run_ids)

print(f"All rec_results deleted. Total rows: {total_rows[0]}", flush=True)

# Now delete the recommendation_runs and ranking_runs
with eng.connect() as conn:
    n = conn.execute(text("DELETE FROM recommendation_runs WHERE id = ANY(:ids)"), {"ids": rec_run_ids}).rowcount
    conn.commit()
    print(f"recommendation_runs deleted: {n}", flush=True)

    stale = conn.execute(text("""
        SELECT array_agg(id) FROM ranking_runs WHERE as_of_date >= '2022-01-01'
        AND id NOT IN (
            SELECT DISTINCT ON (as_of_date, strategy_name) id FROM ranking_runs
            WHERE as_of_date >= '2022-01-01'
            ORDER BY as_of_date, strategy_name, created_at DESC
        )
    """)).scalar() or []
    conn.commit()
    n = conn.execute(text("DELETE FROM ranking_runs WHERE id = ANY(:ids)"), {"ids": stale}).rowcount
    conn.commit()
    print(f"ranking_runs deleted: {n}", flush=True)

    n = conn.execute(text(
        "DELETE FROM daily_batch_runs WHERE status!='completed' AND target_trading_day>='2022-01-01'"
    )).rowcount
    conn.commit()
    print(f"daily_batch_runs (failed) wiped: {n}", flush=True)

print("Done.", flush=True)
sys.exit(0)
