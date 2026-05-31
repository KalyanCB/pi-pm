#!/usr/bin/env python3
"""Temporary batch-ingest probe for NIFTY 500 recovery scalability testing."""

from __future__ import annotations

import argparse
import sys
import time

from app.core.config import get_settings
from app.core.constants import DataStatus, IngestPeriod
from app.db.repositories.ingestion_batch_repository import IngestionBatchRepository
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.session import get_session_factory
from app.providers.yahoo.client import YahooFinanceProvider
from app.services.market_data_service import MarketDataService


def _build_market_data_service(db) -> MarketDataService:
    settings = get_settings()
    stock_repo = StockRepository(db)
    market_data_repo = MarketDataRepository(db)
    ingestion_run_repo = IngestionRunRepository(db)
    provider = YahooFinanceProvider(timeout_seconds=settings.yahoo_request_timeout_seconds)
    return MarketDataService(
        db,
        stock_repo,
        market_data_repo,
        ingestion_run_repo,
        IngestionBatchRepository(db),
        RunLineageRepository(db),
        provider,
    )


def _error_symbols(stock_repo: StockRepository, batch_size: int) -> list[str]:
    stocks = stock_repo.list_stocks(data_status=DataStatus.ERROR.value)
    return [stock.symbol for stock in stocks[:batch_size]]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest first N ERROR-status stocks via MarketDataService (production path)."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        required=True,
        help="Number of ERROR-status symbols to ingest (e.g. 10, 25, 50).",
    )
    parser.add_argument(
        "--period",
        default=IngestPeriod.FIVE_YEARS.value,
        choices=[p.value for p in IngestPeriod],
        help="Yahoo history period (default: 5y).",
    )
    args = parser.parse_args()

    if args.batch_size < 1:
        print("batch-size must be at least 1", file=sys.stderr)
        return 1

    period = IngestPeriod(args.period)
    session_factory = get_session_factory()
    db = session_factory()

    try:
        stock_repo = StockRepository(db)
        symbols = _error_symbols(stock_repo, args.batch_size)

        print(f"batch_size: {args.batch_size}")
        print(f"period: {period.value}")
        print(f"symbols_attempted: {len(symbols)}")
        print(f"symbols: {', '.join(symbols) if symbols else '(none)'}")

        if not symbols:
            print("succeeded: 0")
            print("failed: 0")
            print("elapsed_seconds: 0.00")
            return 0

        service = _build_market_data_service(db)
        started = time.perf_counter()
        result = service.ingest(symbols, period)
        elapsed = time.perf_counter() - started

        succeeded = [run.symbol for run in result.runs if run.status == "COMPLETED"]
        failed = [run.symbol for run in result.runs if run.status == "FAILED"]

        print(f"succeeded: {result.symbols_processed}")
        print(f"failed: {result.symbols_failed}")
        print(f"rows_inserted: {result.rows_inserted}")
        print(f"rows_updated: {result.rows_updated}")
        print(f"batch_status: {result.status.value}")
        print(f"elapsed_seconds: {elapsed:.2f}")

        if succeeded:
            print(f"succeeded_symbols: {', '.join(succeeded)}")
        if failed:
            print(f"failed_symbols: {', '.join(failed)}")
            for run in result.runs:
                if run.status == "FAILED" and run.error_message:
                    print(f"  {run.symbol}: {run.error_message}")

        return 0 if result.symbols_failed == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
