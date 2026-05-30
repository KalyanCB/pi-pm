from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.core.constants import (
    MARKET_DATA_SOURCE_YAHOO,
    DataStatus,
    IngestBatchStatus,
    IngestPeriod,
)
from app.core.exceptions import InvalidSymbolError, NotFoundError, PiPMError
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.stock_repository import StockRepository
from app.models.market_data import MarketData
from app.models.market_data_ingestion_run import MarketDataIngestionRun
from app.providers.yahoo.client import YahooFinanceProvider
from app.schemas.market_data import MarketDataIngestResponse

logger = logging.getLogger(__name__)


class MarketDataService:
    def __init__(
        self,
        db: Session,
        stock_repo: StockRepository,
        market_data_repo: MarketDataRepository,
        ingestion_run_repo: IngestionRunRepository,
        provider: YahooFinanceProvider,
    ) -> None:
        self.db = db
        self.stock_repo = stock_repo
        self.market_data_repo = market_data_repo
        self.ingestion_run_repo = ingestion_run_repo
        self.provider = provider

    def get_market_data(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
        source: str | None = MARKET_DATA_SOURCE_YAHOO,
        limit: int | None = None,
    ) -> list[MarketData]:
        stock = self.stock_repo.get_by_symbol(symbol.strip().upper())
        if stock is None:
            raise NotFoundError(f"Stock not found: {symbol}")
        return self.market_data_repo.get_by_stock_and_date_range(
            stock.id,
            start_date=start_date,
            end_date=end_date,
            source=source,
            limit=limit,
        )

    def ingest(self, symbols: list[str], period: IngestPeriod) -> MarketDataIngestResponse:
        runs: list[MarketDataIngestionRun] = []
        symbols_succeeded = 0
        symbols_failed = 0
        total_inserted = 0
        total_updated = 0
        total_skipped = 0

        for symbol in symbols:
            run = self.ingestion_run_repo.create_running(
                symbol=symbol,
                provider=MARKET_DATA_SOURCE_YAHOO,
                requested_period=period.value,
            )
            try:
                result = self._ingest_single_symbol(symbol, period, run)
                runs.append(result)
                symbols_succeeded += 1
                total_inserted += run.rows_inserted
                total_updated += run.rows_updated
                total_skipped += run.rows_skipped
            except PiPMError as exc:
                logger.warning("Ingestion failed for %s: %s", symbol, exc)
                self.ingestion_run_repo.fail(run, str(exc))
                self.stock_repo.set_data_status(symbol, DataStatus.ERROR)
                runs.append(run)
                symbols_failed += 1
            except Exception as exc:
                logger.exception("Unexpected ingestion failure for %s", symbol)
                self.ingestion_run_repo.fail(run, str(exc))
                self.stock_repo.set_data_status(symbol, DataStatus.ERROR)
                runs.append(run)
                symbols_failed += 1

        self.db.commit()

        if symbols_failed == 0:
            batch_status = IngestBatchStatus.SUCCESS
        else:
            batch_status = IngestBatchStatus.PARTIAL_SUCCESS

        return MarketDataIngestResponse(
            symbols_processed=symbols_succeeded,
            symbols_failed=symbols_failed,
            rows_inserted=total_inserted,
            rows_updated=total_updated,
            rows_skipped=total_skipped,
            status=batch_status,
            runs=runs,
        )

    def _ingest_single_symbol(
        self,
        symbol: str,
        period: IngestPeriod,
        run: MarketDataIngestionRun,
    ) -> MarketDataIngestionRun:
        metadata = self.provider.fetch_metadata(symbol)
        bars = self.provider.fetch_history(symbol, period)

        if not bars:
            raise InvalidSymbolError(f"No OHLCV history returned for symbol: {symbol}")

        stock = self.stock_repo.upsert_from_metadata(metadata)
        counts = self.market_data_repo.upsert_bars(stock.id, bars, source=MARKET_DATA_SOURCE_YAHOO)

        if counts.inserted == 0 and counts.updated == 0:
            raise InvalidSymbolError(f"No valid OHLCV rows ingested for symbol: {symbol}")

        return self.ingestion_run_repo.complete(
            run,
            rows_inserted=counts.inserted,
            rows_updated=counts.updated,
            rows_skipped=counts.skipped,
        )
