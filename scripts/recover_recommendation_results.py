#!/usr/bin/env python3
"""
Recovery script: regenerate recommendation_results from existing ranking_runs.

The TRUNCATE CASCADE on portfolio_positions wiped recommendation_results (4+ yrs of signals).
ranking_results (1.18M rows) and ranking_runs (4654 rows) are intact.

Steps:
  1. Delete recommendation_runs (resets idempotency check)
  2. For each completed ranking_run (ordered by date), call RecommendationService.run_for_ranking_run()
  3. Commits every 50 runs to avoid giant transactions

Run time estimate: ~4654 ranking_runs, ~0.1s each = ~8 min
"""
from __future__ import annotations

import os
import sys
import time
from datetime import date
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.recommendation_service import RecommendationService

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://pipm:pipm@localhost:5432/pipm",
)


def build_svc(db: Session) -> RecommendationService:
    return RecommendationService(db=db)  # all repos default-constructed internally


def main():
    engine = create_engine(DATABASE_URL)

    with Session(engine) as db:
        # ── Step 1: count existing state ──────────────────────────────────────
        rk_count = db.scalar(text("SELECT COUNT(*) FROM ranking_runs WHERE status='completed'"))
        rr_count = db.scalar(text("SELECT COUNT(*) FROM recommendation_runs"))
        rec_count = db.scalar(text("SELECT COUNT(*) FROM recommendation_results"))
        print(f"\n  ranking_runs (completed): {rk_count}")
        print(f"  recommendation_runs     : {rr_count}")
        print(f"  recommendation_results  : {rec_count}")

        # ── Step 2: load only ranking_runs that have NO recommendation_run yet ──
        # (idempotency — skip already-done runs, resume from gap)
        rows = db.execute(text("""
            SELECT rk.id FROM ranking_runs rk
            LEFT JOIN recommendation_runs rr ON rr.ranking_run_id = rk.id
            WHERE rk.status = 'completed' AND rr.id IS NULL
            ORDER BY rk.as_of_date ASC, rk.created_at ASC
        """)).fetchall()
        total = len(rows)
        already_done = rr_count  # previously completed
        print(f"\n  Already done : {already_done} runs ({rec_count:,} results)")
        print(f"  Remaining    : {total} ranking_runs to process...\n")

        svc = build_svc(db)
        ok = 0
        failed = 0
        t0 = time.time()

        for i, (run_id,) in enumerate(rows, 1):
            try:
                svc.run_for_ranking_run(UUID(str(run_id)))
                ok += 1
            except Exception as exc:
                failed += 1
                if failed <= 10:
                    print(f"  ⚠  Failed run {run_id}: {exc}")

            # Commit every 50 runs + progress every 250
            if i % 50 == 0:
                db.commit()
            if i % 250 == 0:
                elapsed = time.time() - t0
                rate = i / elapsed
                eta = (total - i) / rate if rate > 0 else 0
                rec_so_far = db.scalar(text("SELECT COUNT(*) FROM recommendation_results"))
                print(
                    f"  [{i:>4}/{total}] {ok} ok | {failed} fail | "
                    f"{rec_so_far:,} results | "
                    f"{elapsed:.0f}s elapsed | ETA {eta:.0f}s"
                )

        db.commit()

        # ── Final report ──────────────────────────────────────────────────────
        elapsed = time.time() - t0
        final_rec = db.scalar(text("SELECT COUNT(*) FROM recommendation_results"))
        final_rr  = db.scalar(text("SELECT COUNT(*) FROM recommendation_runs"))
        buy_count = db.scalar(text("SELECT COUNT(*) FROM recommendation_results WHERE action='BUY'"))
        print(f"\n  {'='*55}")
        print(f"  RECOVERY COMPLETE in {elapsed:.1f}s")
        print(f"  {'='*55}")
        print(f"  ranking_runs processed : {total}")
        print(f"  OK / Failed            : {ok} / {failed}")
        print(f"  recommendation_runs    : {final_rr}")
        print(f"  recommendation_results : {final_rec:,}")
        print(f"  BUY signals restored   : {buy_count:,}")
        print()


if __name__ == "__main__":
    main()
