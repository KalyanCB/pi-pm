from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_daily_batch_service
from app.schemas.daily_batch import (
    DailyBatchRunCreateRequest,
    DailyBatchRunCreateResponse,
    DailyBatchRunStatusResponse,
    DailyBatchRunSummary,
    DailyBatchTraceResponse,
)
from app.services.daily_batch_service import DailyBatchService

router = APIRouter()


@router.post("/runs", response_model=DailyBatchRunCreateResponse, status_code=status.HTTP_201_CREATED)
def create_daily_batch_run(
    payload: DailyBatchRunCreateRequest,
    service: DailyBatchService = Depends(get_daily_batch_service),
) -> DailyBatchRunCreateResponse:
    return service.create_and_execute(payload)


@router.get("/runs", response_model=list[DailyBatchRunSummary])
def list_daily_batch_runs(
    limit: int = Query(default=50, ge=1, le=200),
    service: DailyBatchService = Depends(get_daily_batch_service),
) -> list[DailyBatchRunSummary]:
    return service.list_runs(limit=limit)


@router.get("/runs/{run_id}", response_model=DailyBatchRunStatusResponse)
def get_daily_batch_run(
    run_id: UUID,
    service: DailyBatchService = Depends(get_daily_batch_service),
) -> DailyBatchRunStatusResponse:
    return service.get_run(run_id)


@router.get("/runs/{run_id}/trace", response_model=DailyBatchTraceResponse)
def get_daily_batch_trace(
    run_id: UUID,
    service: DailyBatchService = Depends(get_daily_batch_service),
) -> DailyBatchTraceResponse:
    return service.get_trace(run_id)
