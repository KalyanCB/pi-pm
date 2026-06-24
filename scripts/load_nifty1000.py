#!/usr/bin/env python3
"""Bootstrap the NIFTY_1000 universe and ingest OHLCV via batched Yahoo Finance calls."""

from __future__ import annotations

import argparse
import sys
import time

from app.core.config import get_settings
from app.core.constants import UNIVERSE_NIFTY_1000, IngestPeriod
from app.db.repositories.ingestion_batch_repository import IngestionBatchRepository
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.db.session import get_session_factory
from app.providers.yahoo.client import YahooFinanceProvider
from app.services.market_data_service import MarketDataService
from app.services.universe_bootstrap_service import UniverseBootstrapService


def _build_market_data_service(db) -> MarketDataService:
    settings = get_settings()
    if settings.market_data_provider == "kite":
        from app.providers.kite import token_store
        from app.providers.kite.client import KiteConnectProvider
        token = token_store.get_token(db) or settings.kite_access_token
        provider = KiteConnectProvider(api_key=settings.kite_api_key, access_token=token)
    else:
        provider = YahooFinanceProvider(timeout_seconds=settings.yahoo_request_timeout_seconds)
    return MarketDataService(
        db,
        StockRepository(db),
        MarketDataRepository(db),
        IngestionRunRepository(db),
        IngestionBatchRepository(db),
        RunLineageRepository(db),
        provider,
    )


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Load NIFTY_1000 universe + market data.")
    parser.add_argument("--batch-size", type=int, default=20, help="Symbols per batch.")
    parser.add_argument("--sleep-seconds", type=float, default=1.0, help="Pause between batches.")
    parser.add_argument(
        "--period",
        default=IngestPeriod.FIVE_YEARS.value,
        choices=[p.value for p in IngestPeriod],
        help="Yahoo history period (default: 5y).",
    )
    parser.add_argument("--skip-ingest", action="store_true", help="Only bootstrap memberships.")
    args = parser.parse_args()

    if args.batch_size < 1:
        print("batch-size must be at least 1", file=sys.stderr)
        return 1

    period = IngestPeriod(args.period)
    session_factory = get_session_factory()
    db = session_factory()
    started = time.perf_counter()

    try:
        stock_repo = StockRepository(db)
        universe_repo = UniverseRepository(db)
        bootstrap_service = UniverseBootstrapService(db, stock_repo, universe_repo)

        result = bootstrap_service.bootstrap_nifty1000()
        print("=== Bootstrap ===")
        print(f"constituents_loaded: {result.constituents_loaded}")
        print(f"stocks_created: {result.stocks_created}")
        print(f"stocks_existing: {result.stocks_existing}")
        print(f"memberships_added: {result.memberships_added}")
        print(f"membership_total: {result.membership_total}")
        print()

        if args.skip_ingest:
            return 0

        symbols = [s.symbol for s in universe_repo.list_stocks_in_universe(UNIVERSE_NIFTY_1000)]
        batches = _chunked(symbols, args.batch_size)
        total_batches = len(batches)
        print(f"=== Ingest ({len(symbols)} symbols, period={period.value}) ===")

        service = _build_market_data_service(db)
        total_processed = 0
        total_failed = 0
        total_rows = 0

        for batch_index, batch in enumerate(batches, start=1):
            response = service.ingest(batch, period)
            total_processed += response.symbols_processed
            total_failed += response.symbols_failed
            total_rows += response.rows_inserted + response.rows_updated
            print(
                f"batch {batch_index}/{total_batches}: "
                f"processed={response.symbols_processed} failed={response.symbols_failed} "
                f"rows={response.rows_inserted + response.rows_updated}",
                flush=True,
            )
            if batch_index < total_batches and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)

        elapsed_minutes = (time.perf_counter() - started) / 60
        print()
        print("=== Final Summary ===")
        print(f"symbols_total: {len(symbols)}")
        print(f"symbols_processed: {total_processed}")
        print(f"symbols_failed: {total_failed}")
        print(f"rows_written: {total_rows}")
        print(f"elapsed_minutes: {elapsed_minutes:.2f}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
