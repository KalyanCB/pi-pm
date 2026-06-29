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

_BATCH = int(os.getenv("BULK_BATCH", "10000"))
_DIFF = os.getenv("BULK_DIFF_TEST", "0") == "1"


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


def main() -> int:
    if rf.START_DATE is None:
        print("ERROR: set REPLAY_START_DATE"); return 1
    db = get_session_factory()()
    days = _trading_days(db)
    if not days:
        print("ERROR: no trading days"); return 1
    print(f"Bulk-rank {len(days)} days x {len(rf._ALL_STRATEGIES)} strat = "
          f"{len(days)*len(rf._ALL_STRATEGIES):,} runs | suite={rf._SUITE}", flush=True)

    # Preload bars once (shared, in-memory).
    print("Preloading bars...", flush=True)
    from app.db.repositories.universe_repository import UniverseRepository
    stocks = UniverseRepository(db).list_stocks_in_universe(rf.UNIVERSE)
    bench = StockRepository(db).get_by_symbol(rf.BENCHMARK)
    ids = [s.id for s in stocks] + ([bench.id] if bench else [])
    store = GlobalBarStore.load(MarketDataRepository(db), ids, end_date=days[-1], source="kite")
    print(f"Preloaded {len(store._all_bars)} stocks.", flush=True)
    rsvc = _ranking_service(db, store)

    if _DIFF:
        return _diff_test(db, rsvc, days)

    run_buf, res_buf, t0, total_res = [], [], time.perf_counter(), 0
    for i, day in enumerate(days, 1):
        rr, res = _compute_day(rsvc, day)
        run_buf.extend(rr); res_buf.extend(res)
        if len(res_buf) >= _BATCH:
            db.bulk_insert_mappings(RankingRun, run_buf)
            db.bulk_insert_mappings(RankingResult, res_buf)
            db.commit()
            total_res += len(res_buf)
            run_buf, res_buf = [], []
        if i % 100 == 0 or i == len(days):
            el = time.perf_counter() - t0
            print(f"  [{i}/{len(days)}] {day} | {total_res:,} results | {el/60:.1f}m | "
                  f"eta ~{(el/i)*(len(days)-i)/60:.0f}m", flush=True)
    if run_buf:
        db.bulk_insert_mappings(RankingRun, run_buf)
        db.bulk_insert_mappings(RankingResult, res_buf)
        db.commit()
        total_res += len(res_buf)
    print(f"Done. {total_res:,} ranking_results in {(time.perf_counter()-t0)/60:.1f}m", flush=True)
    db.close()
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
