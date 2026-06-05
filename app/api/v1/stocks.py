import logging
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_market_data_service, get_stock_service, get_universe_bootstrap_service
from app.schemas.market_data import MarketDataRead
from app.schemas.stock import StockRead
from app.services.market_data_service import MarketDataService
from app.services.stock_service import StockService
from app.services.universe_bootstrap_service import UniverseBootstrapService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/bootstrap", status_code=201)
def bootstrap_nifty500(
    service: UniverseBootstrapService = Depends(get_universe_bootstrap_service),
) -> dict:
    """Load NIFTY 500 stocks from CSV into the universe.

    Safe to call multiple times — idempotent. Existing stocks are updated,
    not duplicated. Logs progress every 50 stocks.
    """
    logger.info("bootstrap_nifty500_started")
    result = service.bootstrap_nifty500(fetch_live=False)
    logger.info(
        "bootstrap_nifty500_completed constituents=%d stocks_created=%d stocks_existing=%d memberships=%d",
        result.constituents_loaded,
        result.stocks_created,
        result.stocks_existing,
        result.membership_total,
    )
    return {
        "universe_code": result.universe_code,
        "constituents_loaded": result.constituents_loaded,
        "stocks_created": result.stocks_created,
        "stocks_existing": result.stocks_existing,
        "memberships_added": result.memberships_added,
        "membership_total": result.membership_total,
    }


@router.get("", response_model=list[StockRead])
def list_stocks(
    data_status: str | None = Query(default=None),
    service: StockService = Depends(get_stock_service),
) -> list[StockRead]:
    return service.list_stocks(data_status=data_status)


@router.get("/{symbol}", response_model=StockRead)
def get_stock(symbol: str, service: StockService = Depends(get_stock_service)) -> StockRead:
    return service.get_stock(symbol)


@router.get("/{symbol}/market-data", response_model=list[MarketDataRead])
def get_stock_market_data(
    symbol: str,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    source: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=5000),
    service: MarketDataService = Depends(get_market_data_service),
) -> list[MarketDataRead]:
    return service.get_market_data(
        symbol,
        start_date=start_date,
        end_date=end_date,
        source=source,
        limit=limit,
    )
