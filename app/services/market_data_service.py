from __future__ import annotations

import logging
import time
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.constants import (
    DataStatus,
    IngestBatchStatus,
    IngestionMode,
    IngestionRunStatus,
    IngestPeriod,
    LineageEntityType,
    LineageRelationshipType,
)
from app.core.exceptions import InvalidSymbolError, NotFoundError, PiPMError
from app.core.structured_logging import log_event
from app.db.repositories.ingestion_batch_repository import IngestionBatchRepository
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.models.market_data import MarketData
from app.models.market_data_ingestion_run import MarketDataIngestionRun
from app.providers.yahoo.client import YahooFinanceProvider
from app.providers.yahoo.models import YahooOHLCVBar
from app.schemas.market_data import MarketDataIngestResponse

logger = logging.getLogger(__name__)


class MarketDataService:
    def __init__(
        self,
        db: Session,
        stock_repo: StockRepository,
        market_data_repo: MarketDataRepository,
        ingestion_run_repo: IngestionRunRepository,
        ingestion_batch_repo: IngestionBatchRepository,
        lineage_repo: RunLineageRepository,
        provider: YahooFinanceProvider,
    ) -> None:
        self.db = db
        self.stock_repo = stock_repo
        self.market_data_repo = market_data_repo
        self.ingestion_run_repo = ingestion_run_repo
        self.ingestion_batch_repo = ingestion_batch_repo
        self.lineage_repo = lineage_repo
        self.provider = provider
        self._source: str = getattr(provider, "source", "yahoo")

    def get_market_data(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
        source: str | None = None,
        limit: int | None = None,
    ) -> list[MarketData]:
        if source is None:
            source = self._source
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

    def has_historical_data(self, *, universe_code: str | None = None, min_rows: int = 100) -> bool:
        """Return True if meaningful historical market data exists (not just a fresh-DB bootstrap).

        Used by the daily batch to decide FULL_REFRESH vs INCREMENTAL ingest mode.
        """
        from sqlalchemy import func, select

        from app.models.market_data import MarketData

        count = self.db.scalar(select(func.count(MarketData.id)).limit(min_rows + 1))
        return (count or 0) >= min_rows

    def ingest(
        self,
        symbols: list[str],
        period: IngestPeriod,
        *,
        ingestion_mode: IngestionMode = IngestionMode.FULL_REFRESH,
        since_date: date | None = None,
        end_date: date | None = None,
    ) -> MarketDataIngestResponse:
        started = time.perf_counter()
        batch = self.ingestion_batch_repo.create_running(
            provider=self._source,
            period=period.value,
            ingestion_mode=ingestion_mode.value,
            symbol_count_requested=len(symbols),
        )
        log_event(
            logger,
            "ingestion_started",
            batch_id=batch.id,
            provider=self._source,
            period=period.value,
            ingestion_mode=ingestion_mode.value,
            symbol_count=len(symbols),
        )

        runs: list[MarketDataIngestionRun] = []
        symbols_succeeded = 0
        symbols_failed = 0
        total_inserted = 0
        total_updated = 0
        total_skipped = 0
        errors: list[str] = []

        for symbol in symbols:
            run = self.ingestion_run_repo.create_running(
                symbol=symbol,
                provider=self._source,
                requested_period=period.value,
                batch_id=batch.id,
                ingestion_mode=ingestion_mode.value,
            )
            self.lineage_repo.link(
                child_entity_type=LineageEntityType.INGESTION_SYMBOL.value,
                child_entity_id=run.id,
                parent_entity_type=LineageEntityType.INGESTION_BATCH.value,
                parent_entity_id=batch.id,
                relationship_type=LineageRelationshipType.BATCH_SYMBOL.value,
            )
            try:
                result = self._ingest_single_symbol(
                    symbol, period, run, ingestion_mode, since_date=since_date, end_date=end_date
                )
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
                errors.append(f"{symbol}: {exc}")
            except Exception as exc:
                logger.exception("Unexpected ingestion failure for %s", symbol)
                self.ingestion_run_repo.fail(run, str(exc))
                self.stock_repo.set_data_status(symbol, DataStatus.ERROR)
                runs.append(run)
                symbols_failed += 1
                errors.append(f"{symbol}: {exc}")

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if symbols_failed == 0:
            batch_status = IngestBatchStatus.SUCCESS.value
        elif symbols_succeeded == 0:
            batch_status = IngestionRunStatus.FAILED.value
        else:
            batch_status = IngestBatchStatus.PARTIAL_SUCCESS.value

        error_summary = "; ".join(errors[:10]) if errors else None
        self.ingestion_batch_repo.complete(
            batch,
            symbol_count_succeeded=symbols_succeeded,
            symbol_count_failed=symbols_failed,
            rows_inserted=total_inserted,
            rows_updated=total_updated,
            rows_skipped=total_skipped,
            execution_duration_ms=elapsed_ms,
            status=batch_status,
            error_summary=error_summary,
        )
        self.db.commit()

        log_event(
            logger,
            "ingestion_completed",
            batch_id=batch.id,
            status=batch_status,
            symbols_succeeded=symbols_succeeded,
            symbols_failed=symbols_failed,
            rows_inserted=total_inserted,
            rows_updated=total_updated,
            rows_skipped=total_skipped,
            execution_duration_ms=elapsed_ms,
        )

        response_status = (
            IngestBatchStatus.SUCCESS if symbols_failed == 0 else IngestBatchStatus.PARTIAL_SUCCESS
        )
        return MarketDataIngestResponse(
            batch_id=batch.id,
            symbols_processed=symbols_succeeded,
            symbols_failed=symbols_failed,
            rows_inserted=total_inserted,
            rows_updated=total_updated,
            rows_skipped=total_skipped,
            status=response_status,
            ingestion_mode=ingestion_mode,
            execution_duration_ms=elapsed_ms,
            runs=runs,
        )

    def _ingest_single_symbol(  # noqa: PLR0913
        self,
        symbol: str,
        period: IngestPeriod,
        run: MarketDataIngestionRun,
        ingestion_mode: IngestionMode,
        *,
        since_date: date | None = None,
        end_date: date | None = None,
    ) -> MarketDataIngestionRun:
        metadata = self.provider.fetch_metadata(symbol)
        stock = self.stock_repo.upsert_from_metadata(metadata)
        latest = self.market_data_repo.get_latest_market_data(stock.id)

        bars = self._fetch_bars(
            symbol, period, ingestion_mode, latest, since_date=since_date, end_date=end_date
        )
        if not bars:
            if (
                since_date is None
                and ingestion_mode == IngestionMode.INCREMENTAL
                and latest is not None
            ):
                completed = self.ingestion_run_repo.complete(
                    run,
                    rows_inserted=0,
                    rows_updated=0,
                    rows_skipped=0,
                    first_date_loaded=latest.date,
                    last_date_loaded=latest.date,
                )
                self.stock_repo.set_data_status(symbol, DataStatus.ACTIVE)
                return completed
            raise InvalidSymbolError(f"No OHLCV history returned for symbol: {symbol}")

        counts = self.market_data_repo.upsert_bars(stock.id, bars, source=self._source)

        if (
            counts.inserted == 0
            and counts.updated == 0
            and ingestion_mode != IngestionMode.INCREMENTAL
        ):
            raise InvalidSymbolError(f"No valid OHLCV rows ingested for symbol: {symbol}")

        first_date, last_date = _bar_date_range(bars)
        completed = self.ingestion_run_repo.complete(
            run,
            rows_inserted=counts.inserted,
            rows_updated=counts.updated,
            rows_skipped=counts.skipped,
            first_date_loaded=first_date,
            last_date_loaded=last_date,
        )
        self.stock_repo.set_data_status(symbol, DataStatus.ACTIVE)
        return completed

    def _fetch_bars(
        self,
        symbol: str,
        period: IngestPeriod,
        ingestion_mode: IngestionMode,
        latest: MarketData | None,
        *,
        since_date: date | None = None,
        end_date: date | None = None,
    ) -> list[YahooOHLCVBar]:
        if since_date is not None:
            return self.provider.fetch_history_since(symbol, since_date, end_date=end_date)
        if ingestion_mode == IngestionMode.INCREMENTAL and latest is not None:
            start_date = latest.date + timedelta(days=1)
            return self.provider.fetch_history_since(symbol, start_date)

        bars = self.provider.fetch_history(symbol, period)
        if ingestion_mode == IngestionMode.INCREMENTAL and latest is not None:
            return [bar for bar in bars if bar.date > latest.date]
        if ingestion_mode == IngestionMode.BACKFILL and latest is not None:
            return [bar for bar in bars if bar.date < latest.date]
        return bars


def _bar_date_range(bars: list[YahooOHLCVBar]) -> tuple[date | None, date | None]:
    if not bars:
        return None, None
    dates = [bar.date for bar in bars]
    return min(dates), max(dates)
