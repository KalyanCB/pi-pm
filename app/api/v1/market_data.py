import calendar
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, model_validator

from app.api.deps import get_market_data_service
from app.core.constants import IngestPeriod, IngestionMode
from app.db.repositories.universe_repository import UniverseRepository
from app.schemas.common import MarketDataIngestRequest
from app.schemas.market_data import MarketDataIngestResponse
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ingest", response_model=MarketDataIngestResponse)
def ingest_market_data(
    payload: MarketDataIngestRequest,
    response: Response,
    service: MarketDataService = Depends(get_market_data_service),
) -> MarketDataIngestResponse:
    result = service.ingest(
        payload.symbols,
        payload.period,
        ingestion_mode=payload.ingestion_mode,
        since_date=payload.since_date,
    )
    if result.is_unhealthy_batch:
        response.status_code = 207
    return result


class UniverseIngestRequest(BaseModel):
    universe_code: str = "NIFTY_500"
    months_back: int | None = Field(default=None, ge=1, le=120, description="Months of history. Ignored if from_date is set.")
    from_date: date | None = Field(default=None, description="Explicit start date. Overrides months_back.")
    to_date: date | None = Field(default=None, description="Explicit end date. Defaults to today.")
    batch_size: int = Field(default=25, ge=1, le=50)
    allow_partial: bool = True
    benchmark_symbol: str = "^NSEI"

    @model_validator(mode="after")
    def resolve_dates(self) -> "UniverseIngestRequest":
        if self.from_date is None and self.months_back is None:
            self.months_back = 13  # default
        return self


class UniverseIngestResponse(BaseModel):
    universe_code: str
    from_date: str
    to_date: str
    total_symbols: int
    symbols_succeeded: int
    symbols_failed: int
    rows_inserted: int
    rows_updated: int
    batches: int


@router.post("/ingest-universe", response_model=UniverseIngestResponse)
def ingest_universe(
    payload: UniverseIngestRequest,
    service: MarketDataService = Depends(get_market_data_service),
) -> UniverseIngestResponse:
    """Ingest market data for all stocks in a universe.

    Supports two modes:
    - months_back (default 13): fetch N months back from today
    - from_date + to_date: explicit date window for parallel year chunks

    Benchmark symbol (^NSEI) is always included automatically.
    Progress logged per batch — follow with: docker logs <container> -f
    """
    universe_repo = UniverseRepository(service.db)
    stocks = universe_repo.list_stocks_in_universe(payload.universe_code)
    if not stocks:
        raise HTTPException(
            status_code=404,
            detail=f"Universe '{payload.universe_code}' not found or has no stocks. Run POST /api/v1/stocks/bootstrap first.",
        )

    # Resolve date window
    today = date.today()
    to_date = payload.to_date or today

    if payload.from_date:
        from_date = payload.from_date
    else:
        # months_back calculation without dateutil
        month = today.month - payload.months_back
        year = today.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = min(today.day, calendar.monthrange(year, month)[1])
        from_date = date(year, month, day)

    if from_date >= to_date:
        raise HTTPException(status_code=422, detail=f"from_date {from_date} must be before to_date {to_date}")

    # Always include benchmark alongside universe stocks
    symbols = [payload.benchmark_symbol] + [s.symbol for s in stocks]
    total = len(symbols)

    logger.info(
        "universe_ingest_started universe=%s benchmark=%s total_symbols=%d from_date=%s to_date=%s batch_size=%d",
        payload.universe_code, payload.benchmark_symbol, total, from_date, to_date, payload.batch_size,
    )

    totals = dict(symbols_succeeded=0, symbols_failed=0, rows_inserted=0, rows_updated=0, batches=0)
    total_batches = (total + payload.batch_size - 1) // payload.batch_size

    for offset in range(0, total, payload.batch_size):
        batch = symbols[offset: offset + payload.batch_size]
        batch_num = offset // payload.batch_size + 1

        logger.info(
            "universe_ingest_batch batch=%d/%d from=%s to=%s symbols=%s",
            batch_num, total_batches, from_date, to_date, batch[:3],
        )

        result = service.ingest(
            batch,
            IngestPeriod.ONE_YEAR,          # period ignored when since_date is set
            ingestion_mode=IngestionMode.FULL_REFRESH,
            since_date=from_date,
            end_date=to_date,
        )

        totals["batches"] += 1
        totals["symbols_succeeded"] += result.symbols_processed
        totals["symbols_failed"] += result.symbols_failed
        totals["rows_inserted"] += result.rows_inserted
        totals["rows_updated"] += result.rows_updated

        logger.info(
            "universe_ingest_batch_done batch=%d/%d ok=%d failed=%d inserted=%d updated=%d cumulative=%d",
            batch_num, total_batches,
            result.symbols_processed, result.symbols_failed,
            result.rows_inserted, result.rows_updated, totals["rows_inserted"],
        )

        if result.symbols_failed and not payload.allow_partial:
            raise HTTPException(status_code=422, detail=f"Batch {batch_num} had {result.symbols_failed} failures.")

    logger.info(
        "universe_ingest_completed universe=%s succeeded=%d failed=%d rows_inserted=%d",
        payload.universe_code, totals["symbols_succeeded"], totals["symbols_failed"], totals["rows_inserted"],
    )

    return UniverseIngestResponse(
        universe_code=payload.universe_code,
        from_date=from_date.isoformat(),
        to_date=to_date.isoformat(),
        total_symbols=total,
        **totals,
    )
