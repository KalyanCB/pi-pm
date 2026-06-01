#!/usr/bin/env python3
"""Sprint 5.1 — NIFTY 500 universe expansion and breakout_v1 validation pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.core.config import get_settings
from app.core.constants import (
    DEFAULT_BENCHMARK_SYMBOL,
    IngestPeriod,
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V1_VERSION,
    RANKING_STRATEGY_MOMENTUM_V1,
    RANKING_STRATEGY_MOMENTUM_V1_VERSION,
    UNIVERSE_NIFTY_500,
)
from app.db.repositories.ingestion_batch_repository import IngestionBatchRepository
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_factor_contribution_repository import (
    RankingFactorContributionRepository,
)
from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.db.repositories.validation_metrics_repository import ValidationMetricsRepository
from app.db.session import get_session_factory
from app.providers.yahoo.client import YahooFinanceProvider
from app.ranking.registry import RankingStrategyRegistry
from app.schemas.backtest import GenerateRankingsRequest
from app.schemas.ranking import RankingRunRequest
from app.services.backtest_service import BacktestService
from app.services.market_data_service import MarketDataService
from app.services.ranking_service import RankingService
from app.services.signal_validation_service import SignalValidationService
from app.services.traceability_service import TraceabilityService
from app.services.universe_bootstrap_service import UniverseBootstrapService
from app.services.universe_coverage_service import UniverseCoverageService
from app.services.universe_filter_service import UniverseFilterService

logger = logging.getLogger(__name__)

VALIDATION_START = date(2024, 1, 1)
VALIDATION_END = date(2026, 5, 29)
MIN_RANKED_COUNT = 450
TOP_N = 20


def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _build_services(db):
    settings = get_settings()
    stock_repo = StockRepository(db)
    market_data_repo = MarketDataRepository(db)
    ingestion_run_repo = IngestionRunRepository(db)
    universe_repo = UniverseRepository(db)
    provider = YahooFinanceProvider(timeout_seconds=settings.yahoo_request_timeout_seconds)
    market_data_service = MarketDataService(
        db,
        stock_repo,
        market_data_repo,
        ingestion_run_repo,
        IngestionBatchRepository(db),
        RunLineageRepository(db),
        provider,
    )
    traceability_service = TraceabilityService(
        db,
        RankingFactorContributionRepository(db),
        ValidationMetricsRepository(db),
        RunLineageRepository(db),
        ingestion_run_repo,
    )
    bootstrap_service = UniverseBootstrapService(db, stock_repo, universe_repo)
    coverage_service = UniverseCoverageService(stock_repo, universe_repo, market_data_repo)
    universe_filter_service = UniverseFilterService(universe_repo, market_data_repo)
    strategy_registry = RankingStrategyRegistry()
    ranking_service = RankingService(
        db,
        settings,
        universe_filter_service,
        RankingRunRepository(db),
        RankingResultRepository(db),
        RankingPerformanceRepository(db),
        stock_repo,
        universe_repo,
        strategy_registry,
        traceability_service,
    )
    backtest_service = BacktestService(
        db,
        settings,
        ranking_service,
        universe_repo,
        stock_repo,
        market_data_repo,
    )
    validation_service = SignalValidationService(
        db,
        settings,
        RankingRunRepository(db),
        RankingResultRepository(db),
        RankingPerformanceRepository(db),
        RankingValidationRepository(db),
        stock_repo,
        market_data_repo,
        traceability_service,
    )
    return {
        "db": db,
        "settings": settings,
        "stock_repo": stock_repo,
        "universe_repo": universe_repo,
        "market_data_service": market_data_service,
        "bootstrap_service": bootstrap_service,
        "coverage_service": coverage_service,
        "ranking_service": ranking_service,
        "ranking_run_repo": RankingRunRepository(db),
        "ranking_result_repo": RankingResultRepository(db),
        "backtest_service": backtest_service,
        "validation_service": validation_service,
    }


def phase_reactivate_stocks_with_data(services) -> dict:
    from sqlalchemy import select

    from app.core.constants import DataStatus
    from app.models.market_data import MarketData
    from app.models.stock import Stock

    db = services["db"]
    stmt = (
        select(Stock)
        .where(Stock.data_status == DataStatus.ERROR.value)
        .where(Stock.id.in_(select(MarketData.stock_id).distinct()))
    )
    reactivated = []
    for stock in db.scalars(stmt).all():
        stock.data_status = DataStatus.ACTIVE.value
        reactivated.append(stock.symbol)
    db.commit()
    return {"reactivated_count": len(reactivated), "symbols": reactivated}


def phase_bootstrap(services, *, fetch_live: bool) -> dict:
    result = services["bootstrap_service"].bootstrap_nifty500(fetch_live=fetch_live)
    return {
        "universe_code": result.universe_code,
        "constituents_loaded": result.constituents_loaded,
        "stocks_created": result.stocks_created,
        "stocks_existing": result.stocks_existing,
        "memberships_changed": result.memberships_added,
        "membership_total": result.membership_total,
    }


def phase_ingest(services, *, batch_size: int, skip_benchmark: bool) -> dict:
    stocks = services["universe_repo"].list_stocks_in_universe(UNIVERSE_NIFTY_500)
    symbols = [stock.symbol for stock in stocks]
    if not skip_benchmark and DEFAULT_BENCHMARK_SYMBOL not in symbols:
        symbols.append(DEFAULT_BENCHMARK_SYMBOL)

    batches = [symbols[i : i + batch_size] for i in range(0, len(symbols), batch_size)]
    totals = {
        "symbols_total": len(symbols),
        "batches": len(batches),
        "symbols_succeeded": 0,
        "symbols_failed": 0,
        "rows_inserted": 0,
        "rows_updated": 0,
    }
    for index, batch in enumerate(batches, start=1):
        logger.info("Ingesting batch %s/%s (%s symbols)", index, len(batches), len(batch))
        response = services["market_data_service"].ingest(batch, IngestPeriod.FIVE_YEARS)
        totals["symbols_succeeded"] += response.symbols_processed
        totals["symbols_failed"] += response.symbols_failed
        totals["rows_inserted"] += response.rows_inserted
        totals["rows_updated"] += response.rows_updated
    return totals


def phase_coverage(services, as_of_date: date) -> dict:
    report = services["coverage_service"].build_report(UNIVERSE_NIFTY_500, as_of_date)
    return services["coverage_service"].report_to_dict(report)


def phase_rank(services, as_of_date: date) -> dict:
    run = services["ranking_service"].run_ranking(
        RankingRunRequest(
            universe_code=UNIVERSE_NIFTY_500,
            as_of_date=as_of_date,
            strategy_name=RANKING_STRATEGY_BREAKOUT_V1,
            strategy_version=RANKING_STRATEGY_BREAKOUT_V1_VERSION,
            benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL,
        )
    )
    ranked_count = len(services["ranking_result_repo"].list_by_run_id(run.id))
    metadata = run.metadata_ or {}
    return {
        "run_id": str(run.id),
        "as_of_date": run.as_of_date.isoformat(),
        "ranked_stock_count": ranked_count,
        "benchmark_available": metadata.get("benchmark_available"),
        "exclusion_summary": metadata.get("exclusion_summary"),
        "meets_threshold": ranked_count > MIN_RANKED_COUNT,
    }


def phase_generate_rankings(
    services,
    *,
    start_date: date,
    end_date: date,
    strategy_name: str,
    strategy_version: str,
) -> dict:
    response = services["backtest_service"].generate_rankings(
        GenerateRankingsRequest(
            universe_code=UNIVERSE_NIFTY_500,
            start_date=start_date,
            end_date=end_date,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL,
        )
    )
    return {
        "strategy_name": response.strategy_name,
        "strategy_version": response.strategy_version,
        "trading_days_total": response.trading_days_total,
        "runs_created": response.runs_created,
        "runs_reused": response.runs_reused,
        "runs_failed": response.runs_failed,
        "failed_dates": [d.isoformat() for d in response.failed_dates],
    }


def phase_validate(services, *, start_date: date, end_date: date) -> dict:
    result = services["validation_service"].backfill(start_date, end_date)
    return {
        "runs_found": result.runs_found,
        "validated": result.validated,
        "reused": result.reused,
        "failed": result.failed,
    }


def phase_compare(services, *, start_date: date, end_date: date) -> dict:
    summaries = {}
    for strategy_name, strategy_version in (
        (RANKING_STRATEGY_MOMENTUM_V1, RANKING_STRATEGY_MOMENTUM_V1_VERSION),
        (RANKING_STRATEGY_BREAKOUT_V1, RANKING_STRATEGY_BREAKOUT_V1_VERSION),
    ):
        summaries[strategy_name] = services["validation_service"].get_summary(
            universe_code=UNIVERSE_NIFTY_500,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            start_date=start_date,
            end_date=end_date,
        )
    return summaries


def phase_top20(services, run_id: str | None) -> list[dict]:
    if run_id is None:
        latest = services["ranking_run_repo"].get_latest(
            universe_code=UNIVERSE_NIFTY_500,
            strategy_name=RANKING_STRATEGY_BREAKOUT_V1,
            strategy_version=RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        )
        if latest is None:
            return []
        run_id = str(latest.id)

    from uuid import UUID

    results = services["ranking_result_repo"].list_top(UUID(run_id), TOP_N)
    stock_repo = services["stock_repo"]
    top: list[dict] = []
    for result in results:
        stock = stock_repo.get_by_id(result.stock_id)
        top.append(
            {
                "rank": result.rank,
                "symbol": stock.symbol if stock else str(result.stock_id),
                "name": stock.name if stock else None,
                "score": float(result.score),
            }
        )
    return top


def run_pipeline(args: argparse.Namespace) -> dict:
    session_factory = get_session_factory()
    db = session_factory()
    report: dict = {"phases": {}}

    try:
        services = _build_services(db)

        if "bootstrap" in args.phases:
            report["phases"]["bootstrap"] = phase_bootstrap(
                services, fetch_live=args.fetch_live
            )
            report["universe_size"] = report["phases"]["bootstrap"]["membership_total"]

        if "reactivate" in args.phases:
            report["phases"]["reactivate"] = phase_reactivate_stocks_with_data(services)

        if "ingest" in args.phases:
            report["phases"]["ingest"] = phase_ingest(
                services, batch_size=args.batch_size, skip_benchmark=False
            )

        as_of = args.as_of_date or VALIDATION_END
        if "coverage" in args.phases:
            coverage = phase_coverage(services, as_of)
            report["phases"]["coverage"] = coverage
            report["data_coverage"] = coverage

        if "rank" in args.phases:
            ranking = phase_rank(services, as_of)
            report["phases"]["ranking"] = ranking
            report["ranking_coverage"] = ranking

        if "backfill-rankings" in args.phases:
            backfill_rankings = {}
            for strategy_name, strategy_version in (
                (RANKING_STRATEGY_MOMENTUM_V1, RANKING_STRATEGY_MOMENTUM_V1_VERSION),
                (RANKING_STRATEGY_BREAKOUT_V1, RANKING_STRATEGY_BREAKOUT_V1_VERSION),
            ):
                backfill_rankings[strategy_name] = phase_generate_rankings(
                    services,
                    start_date=VALIDATION_START,
                    end_date=VALIDATION_END,
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                )
            report["phases"]["backfill_rankings"] = backfill_rankings

        if "validate" in args.phases:
            report["phases"]["validation"] = phase_validate(
                services, start_date=VALIDATION_START, end_date=VALIDATION_END
            )

        if "compare" in args.phases:
            report["validation_comparison"] = phase_compare(
                services, start_date=VALIDATION_START, end_date=VALIDATION_END
            )
            report["phases"]["compare"] = report["validation_comparison"]

        if "top20" in args.phases:
            report["top_20_breakout_candidates"] = phase_top20(services, args.run_id)

    finally:
        db.close()

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint 5.1 NIFTY 500 pipeline")
    parser.add_argument(
        "--phases",
        nargs="+",
        default=["all"],
        choices=[
            "bootstrap",
            "reactivate",
            "ingest",
            "coverage",
            "rank",
            "backfill-rankings",
            "validate",
            "compare",
            "top20",
            "all",
        ],
    )
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=None)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--fetch-live", action="store_true")
    parser.add_argument("--run-id", default=None, help="Breakout ranking run id for top20")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/sprint51-nifty500-report.json"),
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if "all" in args.phases:
        args.phases = [
            "bootstrap",
            "reactivate",
            "ingest",
            "coverage",
            "rank",
            "backfill-rankings",
            "validate",
            "compare",
            "top20",
        ]

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    report = run_pipeline(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=_json_default), encoding="utf-8")
    print(json.dumps(report, indent=2, default=_json_default))
    print(f"\nReport written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
