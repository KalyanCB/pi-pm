#!/usr/bin/env python3
"""
Daily rollover replay from 2021-01-01.

For each trading day (derived from ingested benchmark data):
  - rank (all 4 strategies) as of that day
  - RCEE validation as of that day
  - factor IC as of that day
  - recommendations as of that day

From PAPER_TRADE_FROM onwards additionally runs:
  - portfolio phase: exits → fills → NAV

Requires:
  MARKET_DATA_PROVIDER=kite
  REGIME_DYNAMIC_STOPS_ENABLED=true
  TIME_STOP_ENABLED=false
"""
from __future__ import annotations

import sys
import time
from datetime import date

sys.path.insert(0, ".")

from app.core.config import get_settings
from app.core.constants import MARKET_DATA_SOURCE_YAHOO
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
from app.db.session import get_session_factory
from app.market_data.cache import GlobalBarStore
from app.ops.daily_batch.trading_day_resolver import TradingDayResolver
from app.schemas.daily_batch import (
    DailyBatchPhaseFlags,
    DailyBatchPortfolioPhaseFlags,
    DailyBatchRunCreateRequest,
)
from app.services.daily_batch_service import DailyBatchService
from app.services.factor_predictive_power_service import FactorPredictivePowerService
from app.services.regime_analytics_service import RegimeAnalyticsService
from app.services.research_intelligence_service import ResearchIntelligenceService
from scripts.pipm_service_factory import build_pipm_services

# ── Config ────────────────────────────────────────────────────────────────────
# Warm-up analytics (rankings/validation/regime/factor-IC) run from START_DATE;
# paper trading only kicks in >= PAPER_TRADE_FROM. 2018 start gives RCEE / SMA200
# / regime lookbacks a 3-year warm-up before the 2021 paper-trade phase.
START_DATE = date(2018, 1, 1)
PAPER_TRADE_FROM = date(2021, 1, 1)
BENCHMARK = "^NSEI"
UNIVERSE = "NIFTY_1000"


def _build_batch_service(db, global_store: GlobalBarStore | None = None) -> DailyBatchService:
    services = build_pipm_services(db)
    settings = get_settings()
    regime_svc = RegimeAnalyticsService(
        db, settings, RegimeAnalyticsRepository(db),
        StockRepository(db), MarketDataRepository(db),
    )
    factor_svc = FactorPredictivePowerService(
        db,
        services["factor_service"].metric_repo,
        FactorPerformanceRunRepository(db),
        RankingValidationRepository(db),
        RankingRunRepository(db),
    )
    research_svc = ResearchIntelligenceService(
        db,
        ResearchIntelligenceRunRepository(db),
        ResearchIntelligenceReportRepository(db),
        services["validation_service"],
        factor_svc.metric_repo,
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
        db_factory=get_session_factory(),  # enables parallel ranking strategies
    )


def _get_trading_days(db) -> list[date]:
    """Return all trading days from START_DATE to latest benchmark date."""
    stock_repo = StockRepository(db)
    mdr = MarketDataRepository(db)
    benchmark = stock_repo.get_by_symbol(BENCHMARK)
    if benchmark is None:
        raise ValueError(f"Benchmark {BENCHMARK} not found in DB — run ingest first")
    rows = mdr.list_distinct_trading_dates(
        [benchmark.id],
        start_date=START_DATE,
        end_date=date.today(),
        source="kite",
    )
    return sorted(rows)


def main() -> int:
    settings = get_settings()
    print(f"Settings: provider={settings.market_data_provider} "
          f"regime_dynamic_stops={settings.regime_dynamic_stops_enabled} "
          f"time_stop={settings.time_stop_enabled}")

    Session = get_session_factory()
    db = Session()

    try:
        trading_days = _get_trading_days(db)
    finally:
        db.close()

    if not trading_days:
        print("ERROR: No trading days found — ingest benchmark data first.")
        return 1

    print(f"Trading days: {trading_days[0]} → {trading_days[-1]} ({len(trading_days)} days)")
    print(f"Paper trade from: {PAPER_TRADE_FROM}")
    print()

    # Find resume point — skip days already fully processed
    resume_db = get_session_factory()()
    try:
        run_repo = DailyBatchRunRepository(resume_db)
        done_days = {
            r.target_trading_day
            for r in run_repo.list_runs(limit=10000)
            if r.status == "completed" and r.target_trading_day is not None
        }
    finally:
        resume_db.close()

    remaining = [d for d in trading_days if d not in done_days]
    skipped = len(trading_days) - len(remaining)
    if skipped:
        print(f"Resuming: {skipped} days already completed, {len(remaining)} remaining")

    # Load ALL market data once — zero DB queries for bars during the replay loop
    print("Preloading market data into memory...", flush=True)
    _preload_db = get_session_factory()()
    try:
        _mdr = MarketDataRepository(_preload_db)
        _sr = StockRepository(_preload_db)
        from app.db.repositories.universe_repository import UniverseRepository as _UR
        _stocks = _UR(_preload_db).list_stocks_in_universe(UNIVERSE)
        _benchmark = _sr.get_by_symbol(BENCHMARK)
        _all_ids = [s.id for s in _stocks] + ([_benchmark.id] if _benchmark else [])
        t_pre = time.perf_counter()
        global_store = GlobalBarStore.load(
            _mdr, _all_ids,
            end_date=trading_days[-1],
            source=settings.ranking_market_data_source,
        )
        print(f"Preloaded {len(global_store._all_bars)} stocks, "
              f"{sum(len(v) for v in global_store._all_bars.values()):,} bars "
              f"in {time.perf_counter() - t_pre:.1f}s", flush=True)
        print()
    finally:
        _preload_db.close()

    errors: list[str] = []
    t0 = time.perf_counter()

    for i, day in enumerate(remaining, 1):
        paper_trade = day >= PAPER_TRADE_FROM
        db = get_session_factory()()
        try:
            batch_svc = _build_batch_service(db, global_store)
            request = DailyBatchRunCreateRequest(
                universe_code=UNIVERSE,
                benchmark_symbol=BENCHMARK,
                target_date=day,
                from_date=day,
                force_from_date=True,
                force_recompute=False,           # let idempotency skip already-computed
                force_regenerate_rankings=False,
                force_ingest=False,              # data already ingested
                assume_session_done=True,
                allow_partial_ingest=True,
                holdout_start_date=START_DATE,   # fixed — not rolling per day
                phases=DailyBatchPhaseFlags(
                    ingest=False,
                    rankings=True,
                    validation=True,
                    recommendations=True,
                    regime_history=True,
                    regime_performance=True,
                    factor_ic=True,
                    research_intelligence=False,  # expensive, skip for replay
                    exit_research=False,          # skip for speed — backfill separately
                    portfolio=paper_trade,
                ),
                portfolio_phases=DailyBatchPortfolioPhaseFlags(
                    recompute=paper_trade,
                    exit_monitor=paper_trade,
                    paper_trading=paper_trade,
                    nav_snapshot=paper_trade,
                    reconcile=paper_trade,
                ),
                pilot_auto_approve=paper_trade,
            )
            response = batch_svc.create_and_execute(request)
            elapsed = time.perf_counter() - t0
            avg = elapsed / i
            remaining_est = avg * (len(remaining) - i)
            status_icon = "✓" if response.status == "completed" else "!"
            print(
                f"[{i}/{len(remaining)}] {day} {status_icon} {response.status} "
                f"| paper={paper_trade} "
                f"| eta ~{remaining_est/3600:.1f}h",
                flush=True,
            )
            if response.status != "completed":
                errors.append(f"{day}: {response.status}")
        except Exception as exc:
            print(f"[{i}/{len(remaining)}] {day} ERROR: {exc}", flush=True)
            errors.append(f"{day}: {exc}")
        finally:
            db.close()

    print()
    print(f"Done. {len(remaining)} days processed, {len(errors)} errors.")
    if errors:
        print("Errors:")
        for e in errors[:20]:
            print(f"  {e}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
