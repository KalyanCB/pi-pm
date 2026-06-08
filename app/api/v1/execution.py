"""Unified execution API — paper and live trading (Track K)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth_deps import OwnerUser, PortfolioScope, require_permission
from app.api.deps import get_db
from app.auth.constants import Permission
from app.execution.adapters.zerodha_kite import LiveTradingDisabledError
from app.execution.schemas.execution import (
    ExecutionConfigRead,
    ExecutionConfigUpdate,
    ExecutionEventRead,
    ExecutionHealthRead,
    ExecutionOrderRead,
    SubmitOrderRequest,
)
from app.execution.services.execution_service import ExecutionService, ExecutionValidationError

router = APIRouter()


def _svc(db=Depends(get_db), portfolio_id: PortfolioScope = ...) -> ExecutionService:
    return ExecutionService(db, portfolio_id=portfolio_id)


def _order_read(order) -> ExecutionOrderRead:
    return ExecutionOrderRead(
        id=order.id,
        portfolio_id=order.portfolio_id,
        symbol=order.symbol,
        side=order.side,
        quantity=float(order.quantity),
        strategy_name=order.strategy_name,
        recommendation_id=order.recommendation_id,
        approval_id=order.approval_id,
        requested_by=order.requested_by,
        approved_by=order.approved_by,
        executed_by=order.executed_by,
        execution_mode=order.execution_mode,
        status=order.status,
        broker_name=order.broker_name,
        broker_order_id=order.broker_order_id,
        filled_quantity=float(order.filled_quantity) if order.filled_quantity is not None else None,
        avg_fill_price=float(order.avg_fill_price) if order.avg_fill_price is not None else None,
        fees=float(order.fees) if order.fees is not None else None,
        slippage=float(order.slippage) if order.slippage is not None else None,
        paper_trade_id=order.paper_trade_id,
        rejection_reason=order.rejection_reason,
        submitted_at=order.submitted_at,
        completed_at=order.completed_at,
        created_at=order.created_at,
        raw_response=order.raw_response or {},
    )


@router.post(
    "/orders",
    status_code=201,
    response_model=ExecutionOrderRead,
    dependencies=[Depends(require_permission(Permission.EXECUTION_WRITE))],
)
def submit_order(
    payload: SubmitOrderRequest,
    owner: OwnerUser,
    svc: ExecutionService = Depends(_svc),
) -> ExecutionOrderRead:
    """Submit an execution request for an approved recommendation."""
    try:
        order = svc.submit_from_recommendation(
            recommendation_id=payload.recommendation_id,
            approval_id=payload.approval_id,
            requested_by=owner.user_id,
            as_of_date=payload.as_of_date,
            idempotency_key=payload.idempotency_key,
            execution_mode=payload.execution_mode,
        )
        svc.db.commit()
        return _order_read(order)
    except LiveTradingDisabledError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ExecutionValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/orders/{order_id}/cancel",
    response_model=ExecutionOrderRead,
    dependencies=[Depends(require_permission(Permission.EXECUTION_WRITE))],
)
def cancel_order(
    order_id: UUID,
    owner: OwnerUser,
    svc: ExecutionService = Depends(_svc),
) -> ExecutionOrderRead:
    try:
        order = svc.cancel_order(order_id, actor_id=owner.user_id)
        svc.db.commit()
        return _order_read(order)
    except ExecutionValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/orders/{order_id}",
    response_model=ExecutionOrderRead,
    dependencies=[Depends(require_permission(Permission.EXECUTION_READ))],
)
def get_order(order_id: UUID, svc: ExecutionService = Depends(_svc)) -> ExecutionOrderRead:
    order = svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Execution order not found")
    return _order_read(order)


@router.get(
    "/orders",
    response_model=list[ExecutionOrderRead],
    dependencies=[Depends(require_permission(Permission.EXECUTION_READ))],
)
def list_orders(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    svc: ExecutionService = Depends(_svc),
) -> list[ExecutionOrderRead]:
    orders = svc.list_orders(portfolio_id=svc.portfolio_id, status=status, limit=limit)
    return [_order_read(o) for o in orders]


@router.get(
    "/events",
    response_model=list[ExecutionEventRead],
    dependencies=[Depends(require_permission(Permission.EXECUTION_READ))],
)
def list_events(
    order_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    svc: ExecutionService = Depends(_svc),
) -> list[ExecutionEventRead]:
    events = svc.list_events(order_id=order_id, limit=limit)
    return [ExecutionEventRead.model_validate(e) for e in events]


@router.get(
    "/health",
    response_model=ExecutionHealthRead,
    dependencies=[Depends(require_permission(Permission.EXECUTION_READ))],
)
def execution_health(svc: ExecutionService = Depends(_svc)) -> ExecutionHealthRead:
    data = svc.health_check()
    return ExecutionHealthRead(**data)


@router.get(
    "/config",
    response_model=ExecutionConfigRead,
    dependencies=[Depends(require_permission(Permission.EXECUTION_READ))],
)
def get_config(svc: ExecutionService = Depends(_svc)) -> ExecutionConfigRead:
    return ExecutionConfigRead(**svc.get_config())


@router.post(
    "/config",
    response_model=ExecutionConfigRead,
    dependencies=[Depends(require_permission(Permission.EXECUTION_WRITE))],
)
def update_config(
    payload: ExecutionConfigUpdate,
    owner: OwnerUser,
    svc: ExecutionService = Depends(_svc),
) -> ExecutionConfigRead:
    try:
        data = svc.update_config(
            execution_mode=payload.execution_mode,
            broker_name=payload.broker_name,
            settings_payload=payload.settings,
            notes=payload.notes,
        )
        svc.db.commit()
        return ExecutionConfigRead(**data)
    except LiveTradingDisabledError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
