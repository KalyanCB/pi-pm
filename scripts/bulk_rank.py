"""In-memory BULK ranking (Phase 1, fast path).

Computes ALL (day, strategy) rankings in RAM via RankingService.compute_ranking_only
(the SAME RankingEngine as the per-run path → identical ranks), then BULK-inserts
ranking_runs + ranking_results in 10k batches. Avoids the ~10k per-run transactions that
saturate the (Dockerized) DB — the bottleneck profiling exposed.

Usage:
  REPLAY_START_DATE=2018-01-01 REPLAY_END_DATE=2026-06-18 STRATEGY_SUITE=lifecycle \\
  uv run python scripts/bulk_rank.py            # full bulk rank
  ... BULK_DIFF_TEST=1 uv run python scripts/bulk_rank.py   # diff one day vs per-run path
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import UTC, date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay_fast as rf  # reuse env (START_DATE/END_DATE/UNIVERSE/BENCHMARK/_ALL_STRATEGIES), store, helpers

from app.db.session import get_session_factory
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.stock_repository import StockRepository
from app.market_data.cache import GlobalBarStore
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.schemas.ranking import RankingRunRequest

import _bulk_index as bi  # noqa: E402  (scripts/ is on sys.path)

_BATCH = int(os.getenv("BULK_BATCH", "10000"))
_DIFF = os.getenv("BULK_DIFF_TEST", "0") == "1"
_WORKERS = int(os.getenv("BULK_WORKERS", "6"))
_DROP_IDX = os.getenv("BULK_DROP_INDEXES", "0") == "1"
_DUP_INDEX = "ix_ranking_results_run_rank"  # redundant dup of uq_ranking_result_run_rank — don't recreate
_STORE = None  # fork-inherited by workers (set in main before the pool)


def _trading_days(db):
    mdr = MarketDataRepository(db)
    bench = StockRepository(db).get_by_symbol(rf.BENCHMARK)
    return sorted(mdr.list_distinct_trading_dates(
        [bench.id], start_date=rf.START_DATE, end_date=rf.END_DATE, source="kite"))


def _ranking_service(db, store):
    svc = rf._build_batch_service(db, store)
    return svc.backtest_service.ranking_service


def _compute_day(rsvc, day):
    """Return (run_rows, result_rows) for all strategies on `day` — no DB writes."""
    run_rows, res_rows = [], []
    now = datetime.now(UTC)
    for strat in rf._ALL_STRATEGIES:
        out, regime, strategy, fc_hash = rsvc.compute_ranking_only(RankingRunRequest(
            universe_code=rf.UNIVERSE, as_of_date=day, strategy_name=strat,
            benchmark_symbol=rf.BENCHMARK, force_regenerate=True))
        rid = uuid.uuid4()
        ranked = out.ranked_stocks
        run_rows.append(dict(
            id=rid, strategy_name=strategy.name, strategy_version=strategy.version,
            as_of_date=day, inputs_hash=out.inputs_hash, universe_code=rf.UNIVERSE,
            benchmark_symbol=rf.BENCHMARK, filter_config_hash=fc_hash,
            normalization_method="percentile", status="completed",
            started_at=now, completed_at=now, regime_label=regime,
            ranked_stock_count=len(ranked)))
        for r in ranked:
            res_rows.append(dict(
                id=uuid.uuid4(), ranking_run_id=rid, stock_id=r.stock_id, rank=r.rank,
                score=float(r.composite_score),
                score_components={"composite_score": str(r.composite_score)},
                created_at=now))
    return run_rows, res_rows


def _worker_chunk(days_chunk: list) -> int:
    """Compute + bulk-write a chunk of days (parallel worker). Uses the fork-inherited
    store; bulk inserts contend far less than the old per-run transactions."""
    db = get_session_factory()()
    rsvc = _ranking_service(db, _STORE)
    run_buf, res_buf, total = [], [], 0
    try:
        for day in days_chunk:
            rr, res = _compute_day(rsvc, day)
            run_buf.extend(rr); res_buf.extend(res)
            if len(res_buf) >= _BATCH:
                db.bulk_insert_mappings(RankingRun, run_buf)
                db.bulk_insert_mappings(RankingResult, res_buf)
                db.commit()
                total += len(res_buf); run_buf, res_buf = [], []
        if res_buf:
            db.bulk_insert_mappings(RankingRun, run_buf)
            db.bulk_insert_mappings(RankingResult, res_buf)
            db.commit()
            total += len(res_buf)
    finally:
        db.close()
    return total


def main() -> int:
    if rf.START_DATE is None:
        print("ERROR: set REPLAY_START_DATE"); return 1
    db = get_session_factory()()
    days = _trading_days(db)
    if not days:
        print("ERROR: no trading days"); return 1
    print(f"Bulk-rank {len(days)} days x {len(rf._ALL_STRATEGIES)} strat = "
          f"{len(days)*len(rf._ALL_STRATEGIES):,} runs | suite={rf._SUITE}", flush=True)

    # Preload bars once → module global so forked workers inherit it (copy-on-write).
    print("Preloading bars...", flush=True)
    from app.db.repositories.universe_repository import UniverseRepository
    stocks = UniverseRepository(db).list_stocks_in_universe(rf.UNIVERSE)
    bench = StockRepository(db).get_by_symbol(rf.BENCHMARK)
    ids = [s.id for s in stocks] + ([bench.id] if bench else [])
    global _STORE
    _STORE = GlobalBarStore.load(MarketDataRepository(db), ids, end_date=days[-1], source="kite")
    print(f"Preloaded {len(_STORE._all_bars)} stocks.", flush=True)

    if _DIFF:
        return _diff_test(db, _ranking_service(db, _STORE), days)

    # WRITE-HEAVY: drop the random-UUID indexes so inserts are flat heap appends (not a
    # B-tree that thrashes the 128MB cache and slows day-by-day). Rebuilt after the load.
    idx_state = None
    if _DROP_IDX:
        cons, idx = bi.capture(db, "ranking_results")
        bi.drop(db, "ranking_results", cons, idx)
        idx_state = (cons, idx)
        print(f"DROP-INDEX: dropped {len(cons)} unique + {len(idx)} plain on ranking_results "
              f"→ load is flat heap appends", flush=True)
    db.close()

    # Parallel by DAY: interleaved chunks (each worker spans the full range for balance).
    # Workers compute in RAM + bulk-write their own chunk — bulk inserts contend far less
    # than the old per-run transactions, so the DB stops being the wall.
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    chunks = [days[i::_WORKERS] for i in range(_WORKERS)]
    t0, total = time.perf_counter(), 0
    print(f"PARALLEL bulk-rank | {_WORKERS} workers | flush every {_BATCH:,}", flush=True)
    with ProcessPoolExecutor(max_workers=_WORKERS, mp_context=mp.get_context("fork"),
                             initializer=rf._proc_init) as ex:
        for done, n in enumerate(ex.map(_worker_chunk, chunks), 1):
            total += n
            print(f"  worker {done}/{_WORKERS} done | {total:,} results | "
                  f"{(time.perf_counter()-t0)/60:.1f}m", flush=True)

    if idx_state:
        print("Rebuilding indexes (sorted bulk build, skip duplicate)...", flush=True)
        rdb = get_session_factory()()
        bi.restore(rdb, "ranking_results", *idx_state, skip={_DUP_INDEX})
        rdb.close()
        print(f"  rebuilt (dropped redundant {_DUP_INDEX}).", flush=True)
    print(f"Done. {total:,} ranking_results in {(time.perf_counter()-t0)/60:.1f}m", flush=True)
    return 0


def _diff_test(db, rsvc, days) -> int:
    """Compute one day in-memory; compare ranks to the per-run DB path."""
    from app.db.repositories.ranking_run_repository import RankingRunRepository
    day = days[len(days) // 2]
    strat = rf._ALL_STRATEGIES[0]
    print(f"DIFF-TEST {strat} on {day}", flush=True)
    out, *_ = rsvc.compute_ranking_only(RankingRunRequest(
        universe_code=rf.UNIVERSE, as_of_date=day, strategy_name=strat,
        benchmark_symbol=rf.BENCHMARK, force_regenerate=True))
    mem = {r.stock_id: r.rank for r in out.ranked_stocks}
    # per-run path (writes to DB), then read back the same run.
    outcome = rsvc.run_ranking_with_outcome(RankingRunRequest(
        universe_code=rf.UNIVERSE, as_of_date=day, strategy_name=strat,
        benchmark_symbol=rf.BENCHMARK, force_regenerate=True))
    from sqlalchemy import text
    rows = db.execute(text("SELECT stock_id, rank FROM ranking_results WHERE ranking_run_id=:r"),
                      {"r": outcome.run.id}).fetchall()
    dbm = {r[0]: r[1] for r in rows}
    mism = [s for s in mem if dbm.get(s) != mem[s]]
    print(f"  in-mem ranks: {len(mem)} | db ranks: {len(dbm)} | mismatches: {len(mism)}", flush=True)
    print("  ✅ IDENTICAL" if not mism and len(mem) == len(dbm) else f"  🔴 DIFF ({mism[:5]})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
