from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_signal_validation_service, get_stock_repository
from app.db.repositories.stock_repository import StockRepository
from app.schemas.validation import (
    ValidationBackfillRequest,
    ValidationBackfillResponse,
    ValidationReportRead,
    ValidationSnapshotRead,
    ValidationSummaryRead,
)
from app.services.signal_validation_service import SignalValidationService
from app.services.validation_serializers import (
    report_to_read,
    snapshot_to_read,
    summary_to_read,
    symbol_map,
)

router = APIRouter()


@router.post("/backfill", response_model=ValidationBackfillResponse)
def backfill_validation(
    payload: ValidationBackfillRequest,
    service: SignalValidationService = Depends(get_signal_validation_service),
) -> ValidationBackfillResponse:
    result = service.backfill(
        payload.start_date,
        payload.end_date,
        force_recompute=payload.force_recompute,
    )
    return ValidationBackfillResponse(
        runs_found=result.runs_found,
        validated=result.validated,
        reused=result.reused,
        failed=result.failed,
    )


@router.post("/runs/{run_id}/compute", response_model=ValidationReportRead, status_code=201)
def compute_validation(
    run_id: UUID,
    force_recompute: bool = Query(default=False),
    service: SignalValidationService = Depends(get_signal_validation_service),
) -> ValidationReportRead:
    report = service.compute_run(run_id, force_recompute=force_recompute)
    return report_to_read(report)


@router.get("/runs/{run_id}", response_model=ValidationReportRead)
def get_validation_report(
    run_id: UUID,
    service: SignalValidationService = Depends(get_signal_validation_service),
) -> ValidationReportRead:
    report = service.get_report(run_id)
    return report_to_read(report)


@router.get("/runs/{run_id}/snapshots", response_model=list[ValidationSnapshotRead])
def get_validation_snapshots(
    run_id: UUID,
    service: SignalValidationService = Depends(get_signal_validation_service),
    stock_repo: StockRepository = Depends(get_stock_repository),
) -> list[ValidationSnapshotRead]:
    snapshots = service.get_snapshots(run_id)
    symbols = symbol_map(stock_repo, [snap.stock_id for snap in snapshots])
    return [snapshot_to_read(snap, symbols.get(snap.stock_id)) for snap in snapshots]


@router.get("/summary", response_model=ValidationSummaryRead)
def get_validation_summary(
    universe_code: str | None = Query(default=None),
    strategy_name: str | None = Query(default=None),
    strategy_version: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    horizon: int = Query(default=20),
    service: SignalValidationService = Depends(get_signal_validation_service),
) -> ValidationSummaryRead:
    summary = service.get_summary(
        universe_code=universe_code,
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        start_date=start_date,
        end_date=end_date,
        horizon=horizon,
    )
    return summary_to_read(summary)
