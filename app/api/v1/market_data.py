from fastapi import APIRouter, Depends, Response

from app.api.deps import get_market_data_service
from app.schemas.common import MarketDataIngestRequest
from app.schemas.market_data import MarketDataIngestResponse
from app.services.market_data_service import MarketDataService

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
