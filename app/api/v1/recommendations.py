"""Recommendation Engine REST API (Phase 2 / M1)."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_recommendation_service
from app.api.auth_deps import OwnerUser
from app.services.recommendation_service import RecommendationService

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────


class RunRecommendationRequest(BaseModel):
    ranking_run_id: UUID


class ConvictionComponentsRead(BaseModel):
    rank_quality: float
    validation: float
    ic_factor: float
    regime: float
    exit_health: float
    config_version: str


class RecommendationResultRead(BaseModel):
    id: UUID
    stock_id: UUID
    rank: int | None
    composite_score: float | None
    action: str
    lifecycle_state: str | None
    conviction_score: int
    conviction_band: str
    conviction_components: dict[str, Any]
    reason_codes: list[str]
    recommendation_run_id: UUID

    model_config = {"from_attributes": True}


class RecommendationRunRead(BaseModel):
    id: UUID
    ranking_run_id: UUID
    strategy_name: str
    universe_code: str
    as_of_date: date
    status: str
    config_version: str
    input_hash: str
    result_count: int = 0

    model_config = {"from_attributes": True}


class DailyStrategyResults(BaseModel):
    strategy_name: str
    as_of_date: date
    recommendation_run_id: UUID
    results: list[RecommendationResultRead]


class DailyRecommendationsRead(BaseModel):
    as_of_date: date
    strategies: list[DailyStrategyResults]
    total_results: int
    buy_count: int
    watch_count: int


class ApproveRequest(BaseModel):
    approval_type: str = "ENTRY"
    decision: str
    actor_id: str = "owner"
    note: str | None = None
    idempotency_key: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post("/run", response_model=RecommendationRunRead, status_code=201)
def run_recommendation(
    payload: RunRecommendationRequest,
    _owner: OwnerUser,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationRunRead:
    try:
        rec_run = service.run_for_ranking_run(payload.ranking_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    results = service.get_results(rec_run.id)
    return RecommendationRunRead(
        id=rec_run.id,
        ranking_run_id=rec_run.ranking_run_id,
        strategy_name=rec_run.strategy_name,
        universe_code=rec_run.universe_code,
        as_of_date=rec_run.as_of_date,
        status=rec_run.status,
        config_version=rec_run.config_version,
        input_hash=rec_run.input_hash,
        result_count=len(results),
    )


@router.get("/latest", response_model=RecommendationRunRead)
def get_latest(
    strategy_name: str = Query(...),
    as_of_date: date | None = Query(default=None),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationRunRead:
    rec_run = service.get_latest(strategy_name, as_of_date)
    if rec_run is None:
        raise HTTPException(status_code=404, detail="No completed recommendation run found")
    results = service.get_results(rec_run.id)
    return RecommendationRunRead(
        id=rec_run.id,
        ranking_run_id=rec_run.ranking_run_id,
        strategy_name=rec_run.strategy_name,
        universe_code=rec_run.universe_code,
        as_of_date=rec_run.as_of_date,
        status=rec_run.status,
        config_version=rec_run.config_version,
        input_hash=rec_run.input_hash,
        result_count=len(results),
    )


@router.get("/queue", response_model=list[RecommendationResultRead])
def get_approval_queue(
    service: RecommendationService = Depends(get_recommendation_service),
) -> list[RecommendationResultRead]:
    return service.get_approval_queue()  # type: ignore[return-value]


@router.get("/daily", response_model=DailyRecommendationsRead)
def get_daily(
    as_of_date: date = Query(..., description="Trading date, e.g. 2026-06-05"),
    action: str | None = Query(
        default=None, description="Filter by action: BUY, WATCH, HOLD, REJECT"
    ),
    service: RecommendationService = Depends(get_recommendation_service),
) -> DailyRecommendationsRead:
    """All strategies' recommendations for a given date in one call."""
    action_filter = [action] if action else None
    daily = service.get_daily(as_of_date, action_filter)

    if not daily:
        raise HTTPException(
            status_code=404,
            detail=f"No recommendation runs found for {as_of_date}",
        )

    strategies: list[DailyStrategyResults] = []
    total = buy_count = watch_count = 0

    for strategy_name, results in daily.items():
        # get run_id from first result's run
        run_id = results[0].recommendation_run_id if results else None
        # fetch run to get run id cleanly
        rec_run = service.recommendation_repo.get_latest_run_by_strategy(strategy_name, as_of_date)
        strategies.append(
            DailyStrategyResults(
                strategy_name=strategy_name,
                as_of_date=as_of_date,
                recommendation_run_id=rec_run.id,
                results=results,  # type: ignore[arg-type]
            )
        )
        total += len(results)
        buy_count += sum(1 for r in results if r.action == "BUY")
        watch_count += sum(1 for r in results if r.action == "WATCH")

    return DailyRecommendationsRead(
        as_of_date=as_of_date,
        strategies=strategies,
        total_results=total,
        buy_count=buy_count,
        watch_count=watch_count,
    )


@router.get("/{run_id}", response_model=list[RecommendationResultRead])
def get_run_results(
    run_id: UUID,
    action: str | None = Query(default=None),
    service: RecommendationService = Depends(get_recommendation_service),
) -> list[RecommendationResultRead]:
    action_filter = [action] if action else None
    return service.get_results(run_id, action_filter)  # type: ignore[return-value]


@router.get("/{run_id}/stocks/{symbol}", response_model=RecommendationResultRead)
def get_result_by_symbol(
    run_id: UUID,
    symbol: str,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResultRead:
    from sqlalchemy import select

    from app.models.stock import Stock

    db = service.db
    stock = db.scalar(select(Stock).where(Stock.symbol == symbol.upper()))
    if stock is None:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    result = service.recommendation_repo.get_result_by_symbol(run_id, stock.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return result  # type: ignore[return-value]


@router.get("/why-not/{symbol}", response_model=dict[str, Any])
def why_not_recommended(
    symbol: str,
    strategy_name: str = Query(...),
    service: RecommendationService = Depends(get_recommendation_service),
) -> dict[str, Any]:
    """Deterministic explanation for why a symbol was not recommended BUY."""
    from sqlalchemy import select

    from app.models.stock import Stock

    db = service.db
    stock = db.scalar(select(Stock).where(Stock.symbol == symbol.upper()))
    if stock is None:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

    rec_run = service.get_latest(strategy_name)
    if rec_run is None:
        raise HTTPException(status_code=404, detail="No recommendation run found")

    result = service.recommendation_repo.get_result_by_symbol(rec_run.id, stock.id)
    if result is None:
        return {
            "symbol": symbol.upper(),
            "action": "REJECT",
            "reason_codes": ["RANK_OUTSIDE_POOL"],
            "recommendation_run_id": str(rec_run.id),
            "as_of_date": rec_run.as_of_date.isoformat(),
        }
    return {
        "symbol": symbol.upper(),
        "action": result.action,
        "conviction_band": result.conviction_band,
        "conviction_score": result.conviction_score,
        "reason_codes": result.reason_codes,
        "recommendation_run_id": str(rec_run.id),
        "as_of_date": rec_run.as_of_date.isoformat(),
    }


@router.post("/{result_id}/approve", status_code=200)
def approve_recommendation(
    result_id: UUID,
    payload: ApproveRequest,
    owner: OwnerUser,
    service: RecommendationService = Depends(get_recommendation_service),
) -> dict[str, str]:
    try:
        service.approve(
            result_id,
            approval_type=payload.approval_type,
            decision=payload.decision,
            actor_id=str(owner.user_id),
            note=payload.note,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "decision": payload.decision}


@router.post("/{result_id}/reject", status_code=200)
def reject_recommendation(
    result_id: UUID,
    owner: OwnerUser,
    note: str | None = None,
    service: RecommendationService = Depends(get_recommendation_service),
) -> dict[str, str]:
    try:
        service.approve(
            result_id,
            approval_type="ENTRY",
            decision="REJECTED",
            actor_id=str(owner.user_id),
            note=note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "decision": "REJECTED"}
