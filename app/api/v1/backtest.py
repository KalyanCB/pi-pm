from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_backtest_service, get_signal_validation_service
from app.schemas.backtest import GenerateRankingsRequest, GenerateRankingsResponse
from app.schemas.validation import BacktestSummaryRead
from app.services.backtest_serializers import backtest_result_to_read
from app.services.backtest_service import BacktestService
from app.services.signal_validation_service import SignalValidationService

router = APIRouter()


@router.post("/generate-rankings", response_model=GenerateRankingsResponse, status_code=201)
def generate_rankings(
    payload: GenerateRankingsRequest,
    service: BacktestService = Depends(get_backtest_service),
) -> GenerateRankingsResponse:
    result = service.generate_rankings(payload)
    return backtest_result_to_read(result)


@router.get("/summary", response_model=BacktestSummaryRead)
def get_backtest_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    universe_code: str | None = Query(default=None),
    strategy_name: str | None = Query(default=None),
    strategy_version: str | None = Query(default=None),
    service: SignalValidationService = Depends(get_signal_validation_service),
) -> BacktestSummaryRead:
    summary = service.get_backtest_summary(
        universe_code=universe_code,
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        start_date=start_date,
        end_date=end_date,
    )
    return BacktestSummaryRead(**summary)
