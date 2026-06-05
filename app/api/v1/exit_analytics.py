from fastapi import APIRouter, Depends, Query

from app.api.deps import get_exit_research_service
from app.schemas.exit_research import ExitResearchBackfillRequest, ExitResearchBackfillResponse
from app.services.exit_research_service import ExitResearchService
from app.workspace_exit_research.constants import (
    POLICY_FAMILY_RANK_DETERIORATION,
    POLICY_FAMILY_REGIME_EXIT,
    POLICY_FAMILY_TREND_FAILURE,
)

router = APIRouter()


@router.post("/backfill")
def run_backfill(
    payload: ExitResearchBackfillRequest,
    service: ExitResearchService = Depends(get_exit_research_service),
) -> ExitResearchBackfillResponse:
    run = service.backfill(
        strategy_name=payload.strategy_name,
        strategy_version=payload.strategy_version,
        universe_code=payload.universe_code,
        start_date=payload.start_date,
        end_date=payload.end_date,
        holdout_start_date=payload.holdout_start_date,
        force_recompute=payload.force_recompute,
    )
    return ExitResearchBackfillResponse(
        run_id=str(run.id),
        status=run.status,
        signals_processed=run.signals_processed,
        metrics_written=run.metrics_written,
    )


@router.get("/reports/exit-policy-comparison")
def exit_policy_comparison(
    universe_code: str = Query(...),
    strategy_name: str = "breakout_v1",
    regime_label: str | None = None,
    dataset_split: str = Query(default="HOLDOUT"),
    service: ExitResearchService = Depends(get_exit_research_service),
) -> dict:
    return service.get_policy_comparison(
        universe_code=universe_code,
        strategy_name=strategy_name,
        regime_label=regime_label,
        dataset_split=dataset_split,
    )


@router.get("/reports/alpha-decay")
def alpha_decay_report(
    universe_code: str = Query(...),
    regime_label: str = Query(default="BULL_LOW_VOL"),
    dataset_split: str = Query(default="HOLDOUT"),
    service: ExitResearchService = Depends(get_exit_research_service),
) -> dict:
    return service.get_alpha_decay_report(
        universe_code=universe_code,
        regime_label=regime_label,
        dataset_split=dataset_split,
    )


@router.get("/reports/rank-deterioration")
def rank_deterioration_report(
    universe_code: str = Query(...),
    dataset_split: str = Query(default="HOLDOUT"),
    service: ExitResearchService = Depends(get_exit_research_service),
) -> dict:
    return service.get_family_report(
        POLICY_FAMILY_RANK_DETERIORATION,
        "rank_deterioration_analysis",
        universe_code=universe_code,
        dataset_split=dataset_split,
    )


@router.get("/reports/regime-transition")
def regime_transition_report(
    universe_code: str = Query(...),
    dataset_split: str = Query(default="HOLDOUT"),
    service: ExitResearchService = Depends(get_exit_research_service),
) -> dict:
    return service.get_family_report(
        POLICY_FAMILY_REGIME_EXIT,
        "regime_transition_analysis",
        universe_code=universe_code,
        dataset_split=dataset_split,
    )


@router.get("/reports/trend-failure")
def trend_failure_report(
    universe_code: str = Query(...),
    dataset_split: str = Query(default="HOLDOUT"),
    service: ExitResearchService = Depends(get_exit_research_service),
) -> dict:
    return service.get_family_report(
        POLICY_FAMILY_TREND_FAILURE,
        "trend_failure_analysis",
        universe_code=universe_code,
        dataset_split=dataset_split,
    )


@router.get("/reports/recommended-exit-policy")
def recommended_exit_policy(
    universe_code: str = Query(...),
    dataset_split: str = Query(default="HOLDOUT"),
    service: ExitResearchService = Depends(get_exit_research_service),
) -> dict:
    return service.get_recommended_policy(universe_code=universe_code, dataset_split=dataset_split)


@router.get("/runs")
def list_runs(
    limit: int = Query(default=50, ge=1, le=200),
    service: ExitResearchService = Depends(get_exit_research_service),
) -> list[dict]:
    return service.list_runs(limit=limit)
