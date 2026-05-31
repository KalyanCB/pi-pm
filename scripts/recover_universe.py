#!/usr/bin/env python3
"""Sprint 5.1A — recover NIFTY 500 universe via batched Yahoo OHLCV ingestion."""

from __future__ import annotations

import argparse
import sys
import time

from app.core.config import get_settings
from app.core.constants import DataStatus, IngestPeriod
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
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
    return MarketDataService(db, stock_repo, market_data_repo, ingestion_run_repo, provider)


def _error_symbols(stock_repo: StockRepository) -> list[str]:
    return [stock.symbol for stock in stock_repo.list_stocks(data_status=DataStatus.ERROR.value)]


def _active_count(stock_repo: StockRepository) -> int:
    return len(stock_repo.list_stocks(data_status=DataStatus.ACTIVE.value))


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _print_batch_progress(
    *,
    batch_number: int,
    total_batches: int,
    attempted: int,
    succeeded: int,
    failed: int,
    active_total: int,
) -> None:
    print(f"Batch {batch_number}/{total_batches}", flush=True)
    print(f"attempted: {attempted}", flush=True)
    print(f"succeeded: {succeeded}", flush=True)
    print(f"failed: {failed}", flush=True)
    print(f"active_total: {active_total}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recover ERROR-status stocks via batched MarketDataService ingestion."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Symbols per ingest batch (default: 10).",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=2.0,
        help="Pause between batches (default: 2).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retry passes for remaining ERROR symbols after initial pass (default: 3).",
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
    if args.max_retries < 0:
        print("max-retries must be non-negative", file=sys.stderr)
        return 1

    period = IngestPeriod(args.period)
    max_passes = 1 + args.max_retries

    session_factory = get_session_factory()
    db = session_factory()
    started = time.perf_counter()

    total_attempted = 0
    total_succeeded = 0
    total_failed_ops = 0
    total_rows_inserted = 0
    total_rows_updated = 0

    try:
        stock_repo = StockRepository(db)
        service = _build_market_data_service(db)

        initial_errors = _error_symbols(stock_repo)
        if not initial_errors:
            print("No ERROR-status symbols to recover.")
            print("symbols_attempted: 0")
            print("succeeded: 0")
            print("failed: 0")
            print("rows_inserted: 0")
            print("elapsed_minutes: 0.00")
            return 0

        print(f"Starting recovery for {len(initial_errors)} ERROR symbols")
        print(f"batch_size: {args.batch_size}")
        print(f"period: {period.value}")
        print(f"max_passes: {max_passes} (initial + {args.max_retries} retries)")
        print(f"sleep_seconds: {args.sleep_seconds}")
        print()

        for pass_number in range(1, max_passes + 1):
            error_symbols = _error_symbols(stock_repo)
            if not error_symbols:
                break

            batches = _chunked(error_symbols, args.batch_size)
            total_batches = len(batches)

            if pass_number > 1:
                print(f"\n--- Retry pass {pass_number - 1}/{args.max_retries} "
                      f"({len(error_symbols)} symbols remaining) ---")

            for batch_index, batch in enumerate(batches, start=1):
                result = service.ingest(batch, period)

                total_attempted += len(batch)
                total_succeeded += result.symbols_processed
                total_failed_ops += result.symbols_failed
                total_rows_inserted += result.rows_inserted
                total_rows_updated += result.rows_updated

                _print_batch_progress(
                    batch_number=batch_index,
                    total_batches=total_batches,
                    attempted=len(batch),
                    succeeded=result.symbols_processed,
                    failed=result.symbols_failed,
                    active_total=_active_count(stock_repo),
                )
                print()

                if batch_index < total_batches and args.sleep_seconds > 0:
                    time.sleep(args.sleep_seconds)

        remaining_errors = len(_error_symbols(stock_repo))
        elapsed_minutes = (time.perf_counter() - started) / 60

        print("=== Final Summary ===")
        print(f"symbols_attempted: {total_attempted}")
        print(f"succeeded: {total_succeeded}")
        print(f"failed: {remaining_errors}")
        print(f"rows_inserted: {total_rows_inserted}")
        print(f"rows_updated: {total_rows_updated}")
        print(f"active_total: {_active_count(stock_repo)}")
        print(f"elapsed_minutes: {elapsed_minutes:.2f}")

        if remaining_errors:
            print(f"\nRemaining ERROR symbols: {remaining_errors}")
            return 1
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
