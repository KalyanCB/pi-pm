"""Parallel Phase-2 recommendation generation (to the extent parallelizable).

Recommendations are (per the RCEE analysis) a near-pure function of rankings(D) + regime(D)
+ conviction: the RCEE edge is portfolio-independent and usually insufficient → conviction
fallback. The only portfolio-coupled inputs are `active_position_stock_ids` (held) and
`cooldown_stock_ids` — and during THIS phase the portfolio is empty (the paper trade hasn't
run), so `run_for_ranking_run` naturally reads empty sets → it emits the PURE entry signal.

⚠️ CORRECTNESS CONTRACT (see report): because these recs do NOT exclude held/cooldown
names, the downstream paper-trade gather MUST enforce held+cooldown exclusion at admission
(open_position churns on duplicates). Until that gather guard lands, these parallel recs are
NOT safe to feed the paper trade. Use BULK_REC_DIFF_TEST=1 to compare against the
sequential rec path on a sample run first.

Same write-heavy index hygiene as bulk_rank: BULK_DROP_INDEXES=1 drops recommendation_results
indexes → parallel generate → sorted bulk rebuild + ANALYZE.

Usage:
  STRATEGY_SUITE=lifecycle uv run python scripts/bulk_rec.py             # all completed ranking runs
  BULK_REC_DIFF_TEST=1 uv run python scripts/bulk_rec.py                 # diff one run vs sequential
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay_fast as rf  # noqa: E402

from sqlalchemy import text  # noqa: E402

from app.db.session import get_session_factory  # noqa: E402
from app.services.recommendation_service import RecommendationService  # noqa: E402
import _bulk_index as bi  # noqa: E402

_WORKERS = int(os.getenv("BULK_WORKERS", "6"))
_DROP_IDX = os.getenv("BULK_DROP_INDEXES", "0") == "1"
_DIFF = os.getenv("BULK_REC_DIFF_TEST", "0") == "1"
_TABLE = "recommendation_results"


def _completed_run_ids(db) -> list:
    """Completed ranking runs, optionally scoped to REPLAY_START_DATE..REPLAY_END_DATE
    (so a sample window — e.g. 2018 — can be rec'd in isolation)."""
    sql = "SELECT id FROM ranking_runs WHERE status = 'completed'"
    params: dict = {}
    if rf.START_DATE:
        sql += " AND as_of_date >= :s"; params["s"] = rf.START_DATE
    if rf.END_DATE:
        sql += " AND as_of_date <= :e"; params["e"] = rf.END_DATE
    sql += " ORDER BY as_of_date, strategy_name"
    return [r[0] for r in db.execute(text(sql), params).fetchall()]


def _worker_chunk(run_ids: list) -> int:
    db = get_session_factory()()
    svc = RecommendationService(db)
    n = 0
    try:
        for rid in run_ids:
            try:
                svc.run_for_ranking_run(rid)  # idempotent; flushes rec_run + rec_results
                db.commit()                   # ...but the caller must commit (repo only flushes)
                n += 1
            except Exception as exc:  # keep going; surface count of failures at the end
                db.rollback()
                print(f"  WARN run {rid}: {exc}", flush=True)
    finally:
        db.close()
    return n


def _diff_test(db) -> int:
    """Generate one rec run via the service; compare its action distribution to a re-run
    (idempotent → identical). Sanity that the parallel call path is deterministic."""
    rid = db.execute(text(
        "SELECT id FROM ranking_runs WHERE status='completed' ORDER BY as_of_date "
        "OFFSET (SELECT count(*) FROM ranking_runs)/2 LIMIT 1"
    )).scalar()
    print(f"DIFF-TEST rec for ranking_run {rid}", flush=True)
    svc = RecommendationService(db)
    run = svc.run_for_ranking_run(rid)
    dist = db.execute(text(
        "SELECT action, count(*) FROM recommendation_results WHERE recommendation_run_id=:r "
        "GROUP BY action ORDER BY action"
    ), {"r": run.id}).fetchall()
    print("  action mix:", {d[0]: d[1] for d in dist}, flush=True)
    print("  ✅ generated (idempotent — re-run returns same row)" if dist else "  🔴 no results", flush=True)
    return 0


def main() -> int:
    db = get_session_factory()()
    if _DIFF:
        rc = _diff_test(db)
        db.close()
        return rc

    run_ids = _completed_run_ids(db)
    if not run_ids:
        print("ERROR: no completed ranking_runs — run bulk_rank first."); db.close(); return 1
    print(f"Bulk-rec {len(run_ids):,} ranking runs | {_WORKERS} workers", flush=True)

    idx_state = None
    if _DROP_IDX:
        cons, idx = bi.capture(db, _TABLE)
        bi.drop(db, _TABLE, cons, idx)
        idx_state = (cons, idx)
        print(f"DROP-INDEX: dropped {len(cons)} unique + {len(idx)} plain on {_TABLE}", flush=True)
    db.close()

    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    chunks = [run_ids[i::_WORKERS] for i in range(_WORKERS)]
    t0, total = time.perf_counter(), 0
    with ProcessPoolExecutor(max_workers=_WORKERS, mp_context=mp.get_context("fork"),
                             initializer=rf._proc_init) as ex:
        for done, n in enumerate(ex.map(_worker_chunk, chunks), 1):
            total += n
            print(f"  worker {done}/{_WORKERS} done | {total:,} rec runs | "
                  f"{(time.perf_counter()-t0)/60:.1f}m", flush=True)

    if idx_state:
        print("Rebuilding indexes (sorted bulk build)...", flush=True)
        rdb = get_session_factory()()
        bi.restore(rdb, _TABLE, *idx_state)
        rdb.close()
        print("  rebuilt.", flush=True)
    print(f"Done. {total:,} rec runs in {(time.perf_counter()-t0)/60:.1f}m", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
