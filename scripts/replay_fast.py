#!/usr/bin/env python3
"""Fast daily replay — foreground/background split (identical trades, faster path).

FOREGROUND (sync, trade-critical → BYTE-IDENTICAL paper-trade records):
  per day D:  regime → pick the regime-gated ACTIVE strategy → rank + validate +
  recommend ONLY that strategy → portfolio (exits / entries / NAV).
  Trades use only the active strategy (paper_pilot_ops: strategy_name==_active_strategy),
  and rankings/validation are per-strategy independent — so ranking *just* the active
  one produces the same recs and the same trades as the all-4 replay.

BACKGROUND (async, research, OFF the critical path):
  the OTHER 3 strategies' ranking + validation + factor-IC, on a PROCESS pool (true
  multi-core — sidesteps the GIL that caps a single process at one core; the box has
  idle cores). Never blocks the trade loop, never writes trade state (no recs, no
  portfolio). The bar store is shared with workers via fork copy-on-write (no re-load).
  Trades are ready when the FOREGROUND finishes; the research drains afterward.

Env:
  BG_WORKERS=2          background research worker PROCESSES (4-core box: 2 ideal)
  FACTOR_IC_CADENCE=21  factor-IC cadence (research only)
Requires: MARKET_DATA_PROVIDER=kite, REGIME_DYNAMIC_STOPS_ENABLED=true, TIME_STOP_ENABLED=false
"""
from __future__ import annotations

import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import date

sys.path.insert(0, ".")

from app.core.config import get_settings
from app.core.constants import (
    DEFAULT_BENCHMARK_SYMBOL,
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V2,
    RANKING_STRATEGY_BREAKOUT_V3_BROAD,
    RANKING_STRATEGY_BREAKOUT_V3_DEF,
    RANKING_STRATEGY_LOW_VOL_V1,
    RANKING_STRATEGY_MOMENTUM_V1,
    RANKING_STRATEGY_MOMENTUM_V2,
    RANKING_STRATEGY_MOMENTUM_V3,
    RANKING_STRATEGY_REVERSAL_V1,
    RANKING_STRATEGY_REVERSION_V2,
    RANKING_STRATEGY_REVERSION_V3,
)
from app.db.repositories.daily_batch_artifact_repository import DailyBatchArtifactRepository
from app.db.repositories.daily_batch_run_repository import DailyBatchRunRepository
from app.db.repositories.factor_performance_run_repository import FactorPerformanceRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.db.repositories.research_intelligence_repository import (
    ResearchIntelligenceReportRepository,
    ResearchIntelligenceRunRepository,
)
from app.db.repositories.stock_repository import StockRepository
from app.db.session import dispose_engine, get_session_factory
from app.market_data.cache import GlobalBarStore
from app.schemas.daily_batch import (
    DailyBatchPhaseFlags,
    DailyBatchPortfolioPhaseFlags,
    DailyBatchRunCreateRequest,
    DailyBatchStrategySpec,
)
from app.services.daily_batch_service import DailyBatchService
from app.services.factor_predictive_power_service import FactorPredictivePowerService
from app.services.regime_analytics_service import RegimeAnalyticsService
from app.services.research_intelligence_service import ResearchIntelligenceService
from scripts.pipm_service_factory import build_pipm_services

# ── Config ────────────────────────────────────────────────────────────────────
def _envdate(name: str, default: date) -> date:
    v = os.getenv(name)
    return date.fromisoformat(v) if v else default


START_DATE = _envdate("REPLAY_START_DATE", date(2018, 1, 1))
PAPER_TRADE_FROM = _envdate("REPLAY_PAPER_FROM", date(2021, 1, 1))
END_DATE = _envdate("REPLAY_END_DATE", date.today())
# factor-IC is the heaviest BACKGROUND grower: it re-reads ranking_factor_contributions,
# which balloons (~2.75M rows in 1y → ~22M full-run), so its per-day cost climbs and the
# background contends more with the foreground over time. It is PURE research (never feeds
# a trade), so default it OFF (deferred) for the fast trade replay — backfill it separately
# afterward if the factor-IC research is wanted. Set FACTOR_IC_CADENCE=21 to re-enable.
FACTOR_IC_CADENCE = int(os.getenv("FACTOR_IC_CADENCE", "0"))  # 0 = deferred (research only)
BG_WORKERS = int(os.getenv("BG_WORKERS", "2"))
REPLAY_PHASED = os.getenv("REPLAY_PHASED", "0") == "1"  # rank-all-parallel then trade-sequential
# Trade-only: skip Phase 1 ranking entirely and REUSE existing ranking_runs (built by
# bulk_rank/bulk_rec). Phase 2 reads them via list_completed_in_range. Implies phased.
SKIP_RANK = os.getenv("REPLAY_SKIP_RANK", "0") == "1"
# Paper-only: recommendations ALSO pre-filled (by bulk_rec) → skip the rec + regime_performance
# phases entirely; the portfolio/paper loop reads the existing recommendation_results directly.
SKIP_REC = os.getenv("REPLAY_SKIP_REC", "0") == "1"
BENCHMARK = "^NSEI"
UNIVERSE = "NIFTY_1000"
_VER = "1.0.0"

# Regime → active strategy (mirrors paper_pilot_ops._REGIME_STRATEGY). Trades use only
# this strategy, so the foreground ranks only it. Keep in sync with the pilot.
_REGIME_STRATEGY_V1: dict[str, str] = {
    "BULL_LOW_VOL": RANKING_STRATEGY_BREAKOUT_V1,
    "BULL_HIGH_VOL": RANKING_STRATEGY_MOMENTUM_V1,
    "BEAR_LOW_VOL": RANKING_STRATEGY_REVERSAL_V1,
    "BEAR_HIGH_VOL": RANKING_STRATEGY_LOW_VOL_V1,
    "NEUTRAL_LOW_VOL": RANKING_STRATEGY_MOMENTUM_V1,
    "NEUTRAL_HIGH_VOL": RANKING_STRATEGY_MOMENTUM_V1,
}
# v2 suite (STRATEGY_SUITE=v2): forward-IC validation killed momentum_v2 (IC -0.027)
# and reversion_v2 (bear IC -0.005). The ONLY validated edge is breakout_v2 — "quiet
# stocks near their highs" — bull composite IC +0.048, out-of-sample confirmed +0.051.
# So the honest suite is breakout_v2 across all regimes; in bear few names are near
# their highs, so it naturally finds few candidates and holds mostly cash.
_REGIME_STRATEGY_V2: dict[str, str] = {
    "BULL_LOW_VOL": RANKING_STRATEGY_BREAKOUT_V2,
    "BULL_HIGH_VOL": RANKING_STRATEGY_BREAKOUT_V2,
    "BEAR_LOW_VOL": RANKING_STRATEGY_BREAKOUT_V2,
    "BEAR_HIGH_VOL": RANKING_STRATEGY_BREAKOUT_V2,
    "NEUTRAL_LOW_VOL": RANKING_STRATEGY_BREAKOUT_V2,
    "NEUTRAL_HIGH_VOL": RANKING_STRATEGY_BREAKOUT_V2,
}
# lifecycle suite (STRATEGY_SUITE=lifecycle): regime-aware sleeves — breakout_v2 in
# bull/neutral (the 3-way entry gate sits out actual SIDEWAYS), reversion_v3 in bear.
# Ranks ALL FIVE lifecycle strategies each day so the cross-rank handoff exit has the
# active ranks (breakout_v1 / reversal_v1) available. Pair with LIFECYCLE_ENTRY_ENABLED
# + LIFECYCLE_HANDOFF_EXITS_ENABLED.
_REGIME_STRATEGY_LIFECYCLE: dict[str, str] = {
    "BULL_LOW_VOL": RANKING_STRATEGY_BREAKOUT_V2,
    "BULL_HIGH_VOL": RANKING_STRATEGY_BREAKOUT_V2,
    "BEAR_LOW_VOL": RANKING_STRATEGY_REVERSION_V3,
    "BEAR_HIGH_VOL": RANKING_STRATEGY_REVERSION_V3,
    "NEUTRAL_LOW_VOL": RANKING_STRATEGY_BREAKOUT_V2,
    "NEUTRAL_HIGH_VOL": RANKING_STRATEGY_BREAKOUT_V2,
}
_LIFECYCLE_ALL = [
    RANKING_STRATEGY_BREAKOUT_V2, RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_MOMENTUM_V3, RANKING_STRATEGY_REVERSION_V3,
    RANKING_STRATEGY_REVERSAL_V1,
]
_SUITE = os.getenv("STRATEGY_SUITE", "v1").lower()
# Strategies the TRADE path reads SAME-DAY and must therefore be ranked in the SYNC
# foreground, not the lagging background. The lifecycle handoff exit reads breakout_v1
# (B1), momentum_v3 (trend leg) and reversal_v1 (RV1) for open positions — deferring
# them to background research made the exit fire on stale (bg_pending-day-old) ranks.
_FOREGROUND_SYNC: set[str] = set()
if _SUITE == "lifecycle":
    _REGIME_STRATEGY = _REGIME_STRATEGY_LIFECYCLE
    _ALL_STRATEGIES = _LIFECYCLE_ALL
    # Belt-and-suspenders: ALL lifecycle strategies synchronous — both entry sleeves
    # (breakout_v2/reversion_v3) AND the handoff ranks (breakout_v1/momentum_v3/reversal_v1).
    # Guarantees no trade ever reads a background-lagged rank, even if future code reads
    # the non-active sleeve. Background becomes a no-op (factor-IC off). Foreground does
    # all 5/day (slower) but fully correct.
    _FOREGROUND_SYNC = {
        RANKING_STRATEGY_BREAKOUT_V2,
        RANKING_STRATEGY_BREAKOUT_V1,
        RANKING_STRATEGY_MOMENTUM_V3,
        RANKING_STRATEGY_REVERSION_V3,
        RANKING_STRATEGY_REVERSAL_V1,
    }
# v3 suite (STRATEGY_SUITE=v3): deterministic 2-STATE regime tilt. The active sleeve is
# NOT chosen by the 4-way vol/bull label but by MARKET BREADTH (market_breadth.broad_flag,
# precomputed point-in-time by scripts/compute_breadth.py): BROAD -> breakout_v3_broad
# (proximity+momentum+efficiency), NARROW -> breakout_v3_def (proximity+low_vol). Only the
# breadth-selected sleeve trades each day, so the foreground ranks just that one.
elif _SUITE == "v3":
    _REGIME_STRATEGY = {}  # breadth-keyed, not label-keyed (see _active_strategy)
    _ALL_STRATEGIES = [RANKING_STRATEGY_BREAKOUT_V3_BROAD, RANKING_STRATEGY_BREAKOUT_V3_DEF]
else:
    _REGIME_STRATEGY = _REGIME_STRATEGY_V2 if _SUITE == "v2" else _REGIME_STRATEGY_V1
    _ALL_STRATEGIES = sorted(set(_REGIME_STRATEGY.values()))


def _active_strategy(db, day: date, label: str) -> str:
    """Pick the active strategy for ``day``. v3 suite routes by market breadth (BROAD ->
    breakout_v3_broad, NARROW -> breakout_v3_def); all other suites route by the 4-way
    regime label. Breadth defaults to BROAD when the table has no row for the day."""
    if _SUITE == "v3":
        from sqlalchemy import text as _text
        flag = db.execute(
            _text("SELECT broad_flag FROM market_breadth WHERE date <= :d "
                  "ORDER BY date DESC LIMIT 1"),
            {"d": day},
        ).scalar()
        broad = True if flag is None else bool(flag)
        return RANKING_STRATEGY_BREAKOUT_V3_BROAD if broad else RANKING_STRATEGY_BREAKOUT_V3_DEF
    return _REGIME_STRATEGY.get(label, RANKING_STRATEGY_MOMENTUM_V1)

# Background runs in separate PROCESSES (true multi-core — sidesteps the GIL that caps
# a single process at one core). The preloaded bar store is shared with the workers via
# fork copy-on-write (no re-load, no pickling): the parent sets _GLOBAL_STORE before the
# pool forks, the workers read it. Each worker disposes the inherited DB engine on start
# (_proc_init) so it opens its OWN connections — fork-safe SQLAlchemy.
_GLOBAL_STORE: GlobalBarStore | None = None


def _proc_init() -> None:
    """Background worker startup: drop the DB engine inherited across fork so this
    process creates fresh connections (sharing a forked engine corrupts the pool)."""
    dispose_engine()


def _spec(name: str) -> DailyBatchStrategySpec:
    return DailyBatchStrategySpec(strategy_name=name, strategy_version=_VER)


def _build_batch_service(db, global_store: GlobalBarStore | None = None) -> DailyBatchService:
    services = build_pipm_services(db)
    settings = get_settings()
    regime_svc = RegimeAnalyticsService(
        db, settings, RegimeAnalyticsRepository(db), StockRepository(db), MarketDataRepository(db),
    )
    factor_svc = FactorPredictivePowerService(
        db, services["factor_service"].metric_repo, FactorPerformanceRunRepository(db),
        RankingValidationRepository(db), RankingRunRepository(db),
    )
    research_svc = ResearchIntelligenceService(
        db, ResearchIntelligenceRunRepository(db), ResearchIntelligenceReportRepository(db),
        services["validation_service"], factor_svc.metric_repo,
    )
    if global_store is not None:
        services["backtest_service"].ranking_service.global_bar_store = global_store
        services["validation_service"].global_bar_store = global_store
    return DailyBatchService(
        db,
        market_data_service=services["market_data_service"],
        backtest_service=services["backtest_service"],
        validation_service=services["validation_service"],
        factor_service=factor_svc,
        exit_service=services["exit_service"],
        regime_service=regime_svc,
        research_intelligence_service=research_svc,
        ranking_run_repo=RankingRunRepository(db),
        run_repo=DailyBatchRunRepository(db),
        artifact_repo=DailyBatchArtifactRepository(db),
        db_factory=get_session_factory(),
    )


def _base_request(day: date, strategies: list[DailyBatchStrategySpec], phases, **kw):
    return DailyBatchRunCreateRequest(
        universe_code=UNIVERSE, benchmark_symbol=BENCHMARK,
        target_date=day, from_date=day, force_from_date=True,
        force_recompute=False, force_regenerate_rankings=False, force_ingest=False,
        assume_session_done=True, allow_partial_ingest=True, holdout_start_date=START_DATE,
        strategies=strategies, phases=phases, **kw,
    )


def run_foreground(day: date, paper_trade: bool, global_store) -> tuple[str, str]:
    """Trade-critical, sync. Returns (active_strategy, status)."""
    db = get_session_factory()()
    try:
        settings = get_settings()
        # 1. Regime FIRST — needed to pick the active strategy before ranking.
        regime_svc = RegimeAnalyticsService(
            db, settings, RegimeAnalyticsRepository(db), StockRepository(db), MarketDataRepository(db),
        )
        regime_svc.compute_and_store_regime(as_of_date=day, benchmark_symbol=BENCHMARK)
        db.commit()
        row = RegimeAnalyticsRepository(db).get_current(
            benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL, as_of_date=day
        )
        label = (row.regime_label if row else None) or "NEUTRAL_LOW_VOL"
        active = _active_strategy(db, day, label)

        # 2. Batch the active strategy PLUS any trade-critical handoff strategies the exit
        #    reads same-day (lifecycle: breakout_v1/momentum_v3/reversal_v1). Ranking them
        #    here (not background) means the handoff sees CURRENT ranks, matching live.
        _fg_specs = [_spec(active)] + [_spec(n) for n in _FOREGROUND_SYNC if n != active]
        batch_svc = _build_batch_service(db, global_store)
        request = _base_request(
            day, _fg_specs,
            DailyBatchPhaseFlags(
                ingest=False, rankings=True, validation=True, recommendations=True,
                regime_history=False, regime_performance=False, factor_ic=False,
                research_intelligence=False, exit_research=False, portfolio=paper_trade,
            ),
            portfolio_phases=DailyBatchPortfolioPhaseFlags(
                recompute=paper_trade, exit_monitor=paper_trade, paper_trading=paper_trade,
                nav_snapshot=paper_trade, reconcile=paper_trade,
            ),
            pilot_auto_approve=paper_trade,
        )
        resp = batch_svc.create_and_execute(request)
        return active, resp.status
    finally:
        db.close()


def run_background(day: date, active: str, factor_ic_day: bool) -> None:
    """Research only, runs in a background PROCESS. The OTHER 3 strategies' ranking +
    validation + factor-IC. No recommendations, no portfolio — never touches trade
    state. Reads the fork-inherited _GLOBAL_STORE (not passed, to avoid pickling it)."""
    db = get_session_factory()()
    try:
        # Exclude the active AND the foreground-sync handoff strategies — those are now
        # ranked synchronously on the trade path, so the background only does the leftover
        # pure research (non-handoff sleeves + factor-IC).
        others = [_spec(n) for n in _ALL_STRATEGIES
                  if n != active and n not in _FOREGROUND_SYNC]
        # Belt-and-suspenders: with every strategy ranked synchronously in the foreground,
        # there is no leftover research to do (factor-IC is off by default) — skip.
        if not others and not factor_ic_day:
            return
        batch_svc = _build_batch_service(db, _GLOBAL_STORE)
        request = _base_request(
            day, others,
            DailyBatchPhaseFlags(
                ingest=False, rankings=True, validation=True, recommendations=False,
                regime_history=False, regime_performance=True, factor_ic=factor_ic_day,
                research_intelligence=False, exit_research=False, portfolio=False,
            ),
        )
        batch_svc.create_and_execute(request)
    except Exception as exc:  # research must never break the trade loop
        print(f"  [bg {day}] ERROR: {exc}", flush=True)
    finally:
        db.close()


# ── Phased mode (REPLAY_PHASED=1): rank ALL days in parallel first, then validate+
# recommend+paper sequentially. Ranking is independent per day -> saturates cores; the
# trade path stays sequential so the edge gate (regime_performance) matures with no
# look-ahead. Reuses _GLOBAL_STORE (fork-inherited) + the same batch service. ────────
def _phase_rank(day: date) -> tuple[str, str]:
    """PHASE 1 (parallel): regime + rank all lifecycle strategies. No rec/paper."""
    db = get_session_factory()()
    try:
        settings = get_settings()
        RegimeAnalyticsService(
            db, settings, RegimeAnalyticsRepository(db), StockRepository(db),
            MarketDataRepository(db),
        ).compute_and_store_regime(as_of_date=day, benchmark_symbol=BENCHMARK)
        db.commit()
        batch_svc = _build_batch_service(db, _GLOBAL_STORE)
        request = _base_request(
            day, [_spec(n) for n in _ALL_STRATEGIES],
            DailyBatchPhaseFlags(
                ingest=False, rankings=True, validation=False, recommendations=False,
                regime_history=False, regime_performance=False, factor_ic=False,
                research_intelligence=False, exit_research=False, portfolio=False,
            ),
        )
        return (str(day), batch_svc.create_and_execute(request).status)
    except Exception as exc:
        return (str(day), f"ERR:{str(exc)[:100]}")
    finally:
        db.close()


def _phase_trade(day: date, paper_trade: bool) -> tuple[str, str]:
    """PHASE 2 (sequential): validation + regime_performance + recommendations + paper.
    Rankings already exist (Phase 1); the rec phase finds them via list_completed_in_range.
    Sequential so the RCEE edge gate matures day-by-day (no look-ahead)."""
    db = get_session_factory()()
    try:
        row = RegimeAnalyticsRepository(db).get_current(
            benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL, as_of_date=day)
        active = _active_strategy(
            db, day, (row.regime_label if row else None) or "NEUTRAL_LOW_VOL")
        batch_svc = _build_batch_service(db, _GLOBAL_STORE)
        request = _base_request(
            day, [_spec(n) for n in _ALL_STRATEGIES],
            DailyBatchPhaseFlags(
                # validation (forward-IC) is RESEARCH, not trade-critical — the RCEE gate
                # reads regime_performance, not the IC. Skip it on the trade path for speed.
                # SKIP_RANK reuses pre-built RANKINGS only (the 7h bottleneck). Recs +
                # regime_performance still run here — the batch's portfolio phase depends
                # on the recommendation phase, and rec regen is cheap vs ranking.
                # recommendations stays ON: the paper-trade execution is GATED on it
                # (daily_batch_service L430), but it's IDEMPOTENT — with recs pre-filled by
                # bulk_rec, run_for_ranking_run returns the existing rows (no regeneration).
                # SKIP_REC drops only regime_performance (edge accumulation) — not needed
                # for fixed, pre-decided recs.
                ingest=False, rankings=False, validation=False, recommendations=True,
                regime_history=False, regime_performance=not SKIP_REC, factor_ic=False,
                research_intelligence=False, exit_research=False, portfolio=paper_trade,
            ),
            portfolio_phases=DailyBatchPortfolioPhaseFlags(
                recompute=paper_trade, exit_monitor=paper_trade, paper_trading=paper_trade,
                nav_snapshot=paper_trade, reconcile=paper_trade,
            ),
            pilot_auto_approve=paper_trade,
        )
        return (active, batch_svc.create_and_execute(request).status)
    finally:
        db.close()


def _run_phased(remaining: list[date], executor) -> list[str]:
    """Drive the 2-phase replay. Returns error strings."""
    errors: list[str] = []
    t0 = time.perf_counter()
    if SKIP_RANK:
        print(f"\nSKIP_RANK — Phase 1 skipped, reusing existing rankings; trade-only over "
              f"{len(remaining)} days\n", flush=True)
    else:
        print(f"\nPHASE 1 — ranking {len(remaining)} days (parallel)...", flush=True)
        for i, (d, status) in enumerate(executor.map(_phase_rank, remaining), 1):
            if status.startswith("ERR") or status != "completed":
                errors.append(f"rank {d}: {status}")
            if i % 100 == 0 or i == len(remaining):
                el = time.perf_counter() - t0
                print(f"  ranked {i}/{len(remaining)} | {el/60:.1f}m | eta ~{(el/i)*(len(remaining)-i)/60:.0f}m", flush=True)
        print(f"PHASE 1 done in {(time.perf_counter()-t0)/60:.1f}m\n", flush=True)

    t1 = time.perf_counter()
    print(f"PHASE 2 — validate+recommend+paper {len(remaining)} days (sequential)...", flush=True)
    for i, day in enumerate(remaining, 1):
        try:
            active, status = _phase_trade(day, day >= PAPER_TRADE_FROM)
        except Exception as exc:
            errors.append(f"trade {day}: {exc}")
            continue
        if status != "completed":
            errors.append(f"trade {day}: {status}")
        if i % 50 == 0 or i == len(remaining):
            el = time.perf_counter() - t1
            print(f"  [{i}/{len(remaining)}] {day} {status} | active={active} | "
                  f"paper={day>=PAPER_TRADE_FROM} | {el/60:.1f}m | eta ~{(el/i)*(len(remaining)-i)/60:.0f}m", flush=True)
    print(f"PHASE 2 done in {(time.perf_counter()-t1)/60:.1f}m", flush=True)
    return errors


def main() -> int:
    settings = get_settings()
    print(f"Settings: provider={settings.market_data_provider} "
          f"regime_dynamic_stops={settings.regime_dynamic_stops_enabled} "
          f"time_stop={settings.time_stop_enabled} | BG_WORKERS={BG_WORKERS}")

    db = get_session_factory()()
    try:
        sr, mdr = StockRepository(db), MarketDataRepository(db)
        bench = sr.get_by_symbol(BENCHMARK)
        if bench is None:
            print("ERROR: benchmark not found — ingest first.")
            return 1
        trading_days = sorted(mdr.list_distinct_trading_dates(
            [bench.id], start_date=START_DATE, end_date=END_DATE, source="kite"))
    finally:
        db.close()
    if not trading_days:
        print("ERROR: no trading days.")
        return 1

    print(f"Trading days: {trading_days[0]} → {trading_days[-1]} ({len(trading_days)})")
    print(f"Paper trade from: {PAPER_TRADE_FROM}\n")

    # REPLAY_NO_RESUME: ignore prior completed daily_batch_runs (e.g. a pre-existing prod
    # batch log) and process every trading day. Needed for a fresh paper-only replay when
    # the rankings/recs were built out-of-band (bulk_rank/bulk_rec) and the batch log still
    # has the old run history.
    done = set()
    if os.getenv("REPLAY_NO_RESUME", "0") != "1":
        resume_db = get_session_factory()()
        try:
            done = {r.target_trading_day for r in DailyBatchRunRepository(resume_db).list_runs(limit=10000)
                    if r.status == "completed" and r.target_trading_day is not None}
        finally:
            resume_db.close()
    remaining = [d for d in trading_days if d not in done]
    if len(remaining) < len(trading_days):
        print(f"Resuming: {len(trading_days) - len(remaining)} done, {len(remaining)} remaining")

    print("Preloading market data into memory...", flush=True)
    pdb = get_session_factory()()
    try:
        from app.db.repositories.universe_repository import UniverseRepository as _UR
        stocks = _UR(pdb).list_stocks_in_universe(UNIVERSE)
        bench = StockRepository(pdb).get_by_symbol(BENCHMARK)
        ids = [s.id for s in stocks] + ([bench.id] if bench else [])
        t = time.perf_counter()
        global_store = GlobalBarStore.load(
            MarketDataRepository(pdb), ids, end_date=trading_days[-1],
            source=settings.ranking_market_data_source)
        print(f"Preloaded {len(global_store._all_bars)} stocks in {time.perf_counter()-t:.1f}s\n", flush=True)
    finally:
        pdb.close()

    # Publish the bar store to the module global so forked background PROCESSES inherit
    # it via copy-on-write (shared, read-only — no per-worker re-load or pickling).
    global _GLOBAL_STORE
    _GLOBAL_STORE = global_store

    executor = ProcessPoolExecutor(
        max_workers=BG_WORKERS,
        mp_context=mp.get_context("fork"),  # fork → inherit _GLOBAL_STORE; 3.13 default
        initializer=_proc_init,             # fresh DB engine per worker (fork-safe)
    )
    bg_futures: list = []
    errors: list[str] = []
    t0 = time.perf_counter()

    if REPLAY_PHASED or SKIP_RANK:
        print(f"{'TRADE-ONLY (skip-rank)' if SKIP_RANK else 'PHASED'} mode | workers={BG_WORKERS}", flush=True)
        errors = _run_phased(remaining, executor)
        executor.shutdown(wait=True)
        print(f"\nDone (phased). {len(remaining)} days, {len(errors)} errors.")
        for e in errors[:20]:
            print(f"  {e}")
        return 0 if not errors else 1

    for i, day in enumerate(remaining, 1):
        paper_trade = day >= PAPER_TRADE_FROM
        factor_ic_day = FACTOR_IC_CADENCE > 0 and (i % FACTOR_IC_CADENCE == 0)
        try:
            active, status = run_foreground(day, paper_trade, global_store)  # SYNC trade path
        except Exception as exc:
            print(f"[{i}/{len(remaining)}] {day} FG ERROR: {exc}", flush=True)
            errors.append(f"{day}: {exc}")
            continue
        # Off-critical-path research (async). Submitted AFTER the active ranking is
        # committed, so factor-IC sees all 4 strategies.
        bg_futures.append(executor.submit(run_background, day, active, factor_ic_day))
        bg_futures = [f for f in bg_futures if not f.done()]  # prune

        elapsed = time.perf_counter() - t0
        eta = (elapsed / i) * (len(remaining) - i)
        if status != "completed":
            errors.append(f"{day}: {status}")
        print(f"[{i}/{len(remaining)}] {day} {status} | active={active} | paper={paper_trade} "
              f"| bg_pending={len(bg_futures)} | eta ~{eta/3600:.1f}h (foreground)", flush=True)

    print("\nForeground (TRADES) complete — draining background research...", flush=True)
    executor.shutdown(wait=True)
    print(f"Done. {len(remaining)} days, {len(errors)} errors.")
    for e in errors[:20]:
        print(f"  {e}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
