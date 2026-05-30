from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_market_data_service, get_stock_service
from app.schemas.market_data import MarketDataRead
from app.schemas.stock import StockRead
from app.services.market_data_service import MarketDataService
from app.services.stock_service import StockService

router = APIRouter()


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
