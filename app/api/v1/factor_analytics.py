from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_factor_predictive_power_service
from app.schemas.factor_analytics import (
    FactorAnalyticsBackfillRequest,
    FactorAnalyticsBackfillResponse,
)
from app.services.factor_predictive_power_service import FactorPredictivePowerService

router = APIRouter()


@router.get("/performance")
def get_performance(
    factor_name: str | None = None,
    regime_label: str | None = None,
    horizon: int | None = Query(default=None, ge=5, le=60),
    strategy_name: str | None = None,
    strategy_version: str | None = None,
    universe_code: str | None = None,
    dataset_split: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=500, ge=1, le=1000),
    service: FactorPredictivePowerService = Depends(get_factor_predictive_power_service),
) -> list[dict]:
    return service.get_performance(
        factor_name=factor_name,
        regime_label=regime_label,
        horizon=horizon,
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        universe_code=universe_code,
        dataset_split=dataset_split,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@router.get("/leaderboard")
def get_leaderboard(
    regime_label: str = Query(...),
    horizon: int = Query(..., ge=5, le=60),
    strategy_name: str = "breakout_v1",
    strategy_version: str = "1.0.0",
    universe_code: str = Query(...),
    dataset_split: str = Query(default="HOLDOUT"),
    start_date: date | None = None,
    end_date: date | None = None,
    sort_by: str = Query(default="ic_spearman"),
    service: FactorPredictivePowerService = Depends(get_factor_predictive_power_service),
) -> dict:
    return service.get_leaderboard(
        regime_label=regime_label,
        horizon=horizon,
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        universe_code=universe_code,
        dataset_split=dataset_split,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
    )


@router.get("/compare")
def compare_factor(
    factor_name: str = Query(...),
    strategy_name: str = "breakout_v1",
    strategy_version: str = "1.0.0",
    universe_code: str = Query(...),
    start_date: date | None = None,
    end_date: date | None = None,
    service: FactorPredictivePowerService = Depends(get_factor_predictive_power_service),
) -> dict:
    return service.compare_factor(
        factor_name=factor_name,
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        universe_code=universe_code,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/train-holdout-drift")
def get_train_holdout_drift(
    regime_label: str = Query(default="BULL_LOW_VOL"),
    horizon: int = Query(default=20, ge=5, le=60),
    strategy_name: str = "breakout_v1",
    strategy_version: str = "1.0.0",
    universe_code: str = Query(...),
    start_date: date | None = None,
    end_date: date | None = None,
    min_train_ic: float = Query(default=0.03),
    holdout_start_date: date = Query(default=date(2025, 1, 1)),
    service: FactorPredictivePowerService = Depends(get_factor_predictive_power_service),
) -> dict:
    return service.get_train_holdout_drift(
        regime_label=regime_label,
        horizon=horizon,
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        universe_code=universe_code,
        start_date=start_date,
        end_date=end_date,
        min_train_ic=min_train_ic,
        holdout_start_date=holdout_start_date,
    )


@router.post("/backfill")
def run_backfill(
    payload: FactorAnalyticsBackfillRequest,
    service: FactorPredictivePowerService = Depends(get_factor_predictive_power_service),
) -> FactorAnalyticsBackfillResponse:
    try:
        run = service.backfill(
            strategy_name=payload.strategy_name,
            strategy_version=payload.strategy_version,
            universe_code=payload.universe_code,
            start_date=payload.start_date,
            end_date=payload.end_date,
            holdout_start_date=payload.holdout_start_date,
            force_recompute=payload.force_recompute,
            write_daily_metrics=payload.write_daily_metrics,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return FactorAnalyticsBackfillResponse(
        run_id=str(run.id),
        status=run.status,
        reports_processed=run.reports_processed,
        metrics_written=run.metrics_written,
    )


@router.get("/runs")
def list_runs(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    service: FactorPredictivePowerService = Depends(get_factor_predictive_power_service),
) -> list[dict]:
    return service.list_runs(status=status, limit=limit)


@router.get("/runs/{run_id}")
def get_run(
    run_id: UUID,
    service: FactorPredictivePowerService = Depends(get_factor_predictive_power_service),
) -> dict:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run
