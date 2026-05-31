from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date

from app.api.deps import (
    get_experiment_service,
    get_observability_service,
    get_regime_analytics_service,
    get_traceability_service,
)
from app.core.exceptions import NotFoundError
from app.schemas.observability import ExperimentRunCreate, ScoreReconstructionRead
from app.services.experiment_service import ExperimentService
from app.services.observability_service import ObservabilityService
from app.services.regime_analytics_service import RegimeAnalyticsService
from app.services.traceability_service import TraceabilityService

router = APIRouter()


@router.get("/health/platform")
def platform_health(service: ObservabilityService = Depends(get_observability_service)) -> dict:
    return service.get_platform_health()


@router.get("/ingestion/batches")
def list_ingestion_batches(
    limit: int = Query(default=20, ge=1, le=100),
    service: ObservabilityService = Depends(get_observability_service),
) -> list[dict]:
    return service.list_recent_ingestion_batches(limit)


@router.get("/ingestion/batches/{batch_id}")
def get_ingestion_batch(
    batch_id: UUID,
    service: ObservabilityService = Depends(get_observability_service),
) -> dict:
    batch = service.get_ingestion_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"Ingestion batch not found: {batch_id}")
    return batch


@router.get("/rankings/runs")
def list_ranking_runs(
    limit: int = Query(default=20, ge=1, le=100),
    service: ObservabilityService = Depends(get_observability_service),
) -> list[dict]:
    return service.list_recent_ranking_runs(limit)


@router.get("/validation/metrics")
def list_validation_metrics(
    strategy_name: str | None = None,
    strategy_version: str | None = None,
    regime_label: str | None = None,
    horizon: int | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    service: ObservabilityService = Depends(get_observability_service),
) -> list[dict]:
    return service.get_validation_metrics_summary(
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        regime_label=regime_label,
        horizon=horizon,
        limit=limit,
    )


@router.get("/lineage/{entity_type}/{entity_id}")
def get_lineage(
    entity_type: str,
    entity_id: UUID,
    service: ObservabilityService = Depends(get_observability_service),
) -> list[dict]:
    return service.get_lineage(entity_type, entity_id)


@router.get(
    "/rankings/{ranking_run_id}/stocks/{stock_id}/score-reconstruction",
    response_model=ScoreReconstructionRead,
)
def reconstruct_score(
    ranking_run_id: UUID,
    stock_id: UUID,
    service: TraceabilityService = Depends(get_traceability_service),
) -> ScoreReconstructionRead:
    return ScoreReconstructionRead(**service.reconstruct_score(ranking_run_id, stock_id))


@router.get("/experiments")
def list_experiments(
    limit: int = Query(default=20, ge=1, le=100),
    service: ObservabilityService = Depends(get_observability_service),
) -> list[dict]:
    return service.list_recent_experiments(limit)


@router.post("/experiments")
def create_experiment(
    payload: ExperimentRunCreate,
    service: ExperimentService = Depends(get_experiment_service),
) -> dict:
    run = service.start(
        experiment_name=payload.experiment_name,
        strategy_name=payload.strategy_name,
        strategy_version=payload.strategy_version,
        parameter_set=payload.parameter_set,
        notes=payload.notes,
    )
    return {
        "experiment_id": str(run.id),
        "experiment_name": run.experiment_name,
        "status": run.status,
        "started_at": run.started_at.isoformat(),
    }


@router.post("/experiments/{experiment_id}/complete")
def complete_experiment(
    experiment_id: UUID,
    service: ExperimentService = Depends(get_experiment_service),
) -> dict:
    try:
        run = service.complete(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "experiment_id": str(run.id),
        "status": run.status,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get("/regime/current")
def get_current_regime(
    benchmark_symbol: str | None = None,
    as_of_date: date | None = None,
    service: RegimeAnalyticsService = Depends(get_regime_analytics_service),
) -> dict:
    regime = service.get_current_regime(
        benchmark_symbol=benchmark_symbol,
        as_of_date=as_of_date,
    )
    if regime is None:
        raise HTTPException(status_code=404, detail="Regime not available")
    return {
        "as_of_date": regime.as_of_date.isoformat(),
        "benchmark_symbol": regime.benchmark_symbol,
        "trend_regime": regime.trend_regime,
        "vol_regime": regime.vol_regime,
        "regime_label": regime.regime_label,
        "recorded_at": regime.recorded_at.isoformat(),
    }


@router.post("/regime/performance/refresh")
def refresh_regime_performance(
    strategy_name: str,
    strategy_version: str,
    horizon: int = 20,
    service: RegimeAnalyticsService = Depends(get_regime_analytics_service),
) -> list[dict]:
    rows = service.refresh_strategy_regime_performance(
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        horizon=horizon,
    )
    return [
        {
            "strategy_name": row.strategy_name,
            "strategy_version": row.strategy_version,
            "regime_label": row.regime_label,
            "horizon": row.horizon,
            "avg_ic": float(row.avg_ic) if row.avg_ic is not None else None,
            "avg_spread": float(row.avg_spread) if row.avg_spread is not None else None,
            "sample_count": row.sample_count,
            "last_updated": row.last_updated.isoformat(),
        }
        for row in rows
    ]


@router.get("/regime/performance")
def list_regime_performance(
    strategy_name: str | None = None,
    strategy_version: str | None = None,
    horizon: int | None = None,
    service: RegimeAnalyticsService = Depends(get_regime_analytics_service),
) -> list[dict]:
    rows = service.list_strategy_regime_performance(
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        horizon=horizon,
    )
    return [
        {
            "strategy_name": row.strategy_name,
            "strategy_version": row.strategy_version,
            "regime_label": row.regime_label,
            "horizon": row.horizon,
            "avg_ic": float(row.avg_ic) if row.avg_ic is not None else None,
            "avg_spread": float(row.avg_spread) if row.avg_spread is not None else None,
            "sample_count": row.sample_count,
            "last_updated": row.last_updated.isoformat(),
        }
        for row in rows
    ]
