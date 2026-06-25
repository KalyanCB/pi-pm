"""Recommendation Engine REST API (Phase 2 / M1)."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.auth_deps import OwnerUser
from app.api.deps import get_db, get_recommendation_service
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


class RecommendationApprovalRead(BaseModel):
    approval_type: str
    decision: str
    decided_at: str
    actor_id: str


class RecommendationTradeRead(BaseModel):
    side: str
    fill_price: float
    fill_quantity: float
    status: str
    filled_at: str | None


class RecommendationPositionRead(BaseModel):
    id: str
    symbol: str | None
    quantity: float
    avg_cost: float
    entry_price: float | None
    entry_date: str | None
    exit_price: float | None
    exit_date: str | None
    market_value: float | None
    unrealized_pnl: float | None
    realized_pnl: float | None
    weight_pct: float | None
    position_status: str
    strategy_name: str | None
    conviction_band: str | None
    sector: str | None


class RecommendationOutcomeRead(BaseModel):
    outcome_status: str
    entry_date: str
    exit_date: str | None
    pnl_pct: float | None
    days_held: int | None
    exit_reason: str | None


class RecommendationExecutionContextRead(BaseModel):
    approvals: list[RecommendationApprovalRead]
    trades: list[RecommendationTradeRead]
    position: RecommendationPositionRead | None
    outcome: RecommendationOutcomeRead | None


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
    portfolio_position_id: UUID | None = None

    # ADR-034: deterministic trade levels (BUY)
    reference_close: float | None = None
    atr_pct: float | None = None
    entry_low: float | None = None
    entry_high: float | None = None
    stop_advisory: float | None = None
    stop_critical: float | None = None
    levels_basis: str | None = None

    # Live LTP from Kite (populated at read time when MARKET_DATA_PROVIDER=kite)
    ltp: float | None = None

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
    execution_context: dict[str, RecommendationExecutionContextRead] = {}


class DailyRecommendationsRead(BaseModel):
    as_of_date: date
    strategies: list[DailyStrategyResults]
    total_results: int
    buy_count: int
    watch_count: int


class RecommendationDatesRead(BaseModel):
    dates: list[date]
    latest_date: date | None


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


@router.get("/dates", response_model=RecommendationDatesRead)
def list_recommendation_dates(
    strategy_name: str | None = Query(default=None),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationDatesRead:
    """Distinct dates with completed recommendation runs (newest first)."""
    dates = service.list_available_dates(strategy_name)
    return RecommendationDatesRead(dates=dates, latest_date=dates[0] if dates else None)


@router.get("/daily", response_model=DailyRecommendationsRead)
def get_daily(
    as_of_date: date = Query(..., description="Trading date, e.g. 2026-06-05"),
    action: str | None = Query(
        default=None, description="Filter by action: BUY, WATCH, HOLD, REJECT"
    ),
    include_rejected: bool = Query(
        default=False,
        description=(
            "Include REJECT/HOLD results. Off by default: the UI only shows "
            "BUY/WATCH/EXIT_APPROVED, and REJECTs are ~96% of a NIFTY_1000 day "
            "(2.5MB / ~12-32s vs ~80KB / ~2s). Ignored when `action` is set."
        ),
    ),
    db=Depends(get_db),
    service: RecommendationService = Depends(get_recommendation_service),
) -> DailyRecommendationsRead:
    """All strategies' recommendations for a given date in one call."""
    # Mirrors the Recommendations screen TABS; keep in sync if a tab is added.
    DISPLAY_ACTIONS = ["BUY", "WATCH", "EXIT_APPROVED"]
    if action:
        action_filter = [action]
    elif include_rejected:
        action_filter = None
    else:
        action_filter = DISPLAY_ACTIONS
    resolved_date = as_of_date
    daily = service.get_daily(resolved_date, action_filter)

    if not daily and resolved_date == date.today():
        latest = service.recommendation_repo.get_latest_run_date()
        if latest is not None and latest != resolved_date:
            resolved_date = latest
            daily = service.get_daily(resolved_date, action_filter)

    if not daily:
        raise HTTPException(
            status_code=404,
            detail=f"No recommendation runs found for {as_of_date}",
        )

    # Bulk LTP for all recommended symbols (best-effort, Kite only)
    ltp_map: dict[str, float] = {}
    try:
        from app.core.config import get_settings
        if get_settings().market_data_provider == "kite":
            from app.providers.kite.quote import bulk_ltp
            all_symbols = [
                r.stock.symbol
                for results in daily.values()
                for r in results
                if r.stock and r.stock.symbol
            ]
            if all_symbols:
                ltp_map = bulk_ltp(list(set(all_symbols)), db)
    except Exception:
        pass

    strategies: list[DailyStrategyResults] = []
    total = buy_count = watch_count = 0

    for strategy_name, results in daily.items():
        rec_run = service.recommendation_repo.get_latest_run_by_strategy(
            strategy_name, resolved_date
        )
        if rec_run is None:
            continue
        result_ids = [r.id for r in results]
        raw_ctx = service.get_execution_context(result_ids)
        execution_context = {
            k: RecommendationExecutionContextRead(**v) for k, v in raw_ctx.items()
        }
        # Inject LTP into each result read model
        enriched = []
        for r in results:
            sym = r.stock.symbol if r.stock else None
            row = RecommendationResultRead.model_validate(r)
            row.ltp = ltp_map.get(sym) if sym else None
            enriched.append(row)
        strategies.append(
            DailyStrategyResults(
                strategy_name=strategy_name,
                as_of_date=resolved_date,
                recommendation_run_id=rec_run.id,
                results=enriched,
                execution_context=execution_context,
            )
        )
        total += len(results)
        buy_count += sum(1 for r in results if r.action == "BUY")
        watch_count += sum(1 for r in results if r.action == "WATCH")

    return DailyRecommendationsRead(
        as_of_date=resolved_date,
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
