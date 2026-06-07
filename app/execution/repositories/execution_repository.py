"""Execution persistence layer — Track K."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.execution.constants import ExecutionMode, ExecutionStatus
from app.models.execution import ExecutionAudit, ExecutionConfig, ExecutionEvent, ExecutionOrder


class ExecutionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_order(self, order_id: UUID) -> ExecutionOrder | None:
        return self.db.get(ExecutionOrder, order_id)

    def get_order_by_client_id(self, client_order_id: str) -> ExecutionOrder | None:
        return self.db.scalar(
            select(ExecutionOrder).where(ExecutionOrder.client_order_id == client_order_id)
        )

    def get_order_by_idempotency(self, key: str) -> ExecutionOrder | None:
        return self.db.scalar(
            select(ExecutionOrder).where(ExecutionOrder.idempotency_key == key)
        )

    def list_orders(
        self,
        *,
        portfolio_id: UUID | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ExecutionOrder]:
        q = select(ExecutionOrder).order_by(ExecutionOrder.created_at.desc()).limit(limit)
        if portfolio_id:
            q = q.where(ExecutionOrder.portfolio_id == portfolio_id)
        if status:
            q = q.where(ExecutionOrder.status == status)
        return list(self.db.scalars(q).all())

    def list_events(
        self,
        *,
        order_id: UUID | None = None,
        limit: int = 200,
    ) -> list[ExecutionEvent]:
        q = select(ExecutionEvent).order_by(ExecutionEvent.created_at.desc()).limit(limit)
        if order_id:
            q = q.where(ExecutionEvent.execution_order_id == order_id)
        return list(self.db.scalars(q).all())

    def create_order(
        self,
        *,
        portfolio_id: UUID,
        symbol: str,
        side: str,
        quantity: float,
        strategy_name: str | None,
        recommendation_id: UUID,
        approval_id: UUID,
        requested_by: UUID,
        approved_by: UUID | None,
        execution_mode: ExecutionMode,
        client_order_id: str,
        idempotency_key: str | None = None,
    ) -> ExecutionOrder:
        order = ExecutionOrder(
            portfolio_id=portfolio_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            strategy_name=strategy_name,
            recommendation_id=recommendation_id,
            approval_id=approval_id,
            requested_by=requested_by,
            approved_by=approved_by,
            execution_mode=execution_mode.value,
            status=ExecutionStatus.EXECUTION_PENDING.value,
            client_order_id=client_order_id,
            idempotency_key=idempotency_key,
        )
        self.db.add(order)
        self.db.flush()
        return order

    def record_event(
        self,
        *,
        order_id: UUID,
        from_status: str | None,
        to_status: str,
        actor_id: UUID | None = None,
        event_type: str = "STATE_TRANSITION",
        payload: dict[str, Any] | None = None,
    ) -> ExecutionEvent:
        event = ExecutionEvent(
            execution_order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            event_type=event_type,
            actor_id=actor_id,
            payload=payload or {},
            created_at=datetime.now(UTC),
        )
        self.db.add(event)
        self.db.flush()
        return event

    def record_audit(
        self,
        *,
        order_id: UUID,
        action: str,
        execution_mode: ExecutionMode,
        actor_id: UUID | None,
        broker_name: str | None,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> ExecutionAudit:
        audit = ExecutionAudit(
            execution_order_id=order_id,
            action=action,
            actor_id=actor_id,
            execution_mode=execution_mode.value,
            broker_name=broker_name,
            request_payload=request_payload,
            response_payload=response_payload,
            correlation_id=correlation_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(audit)
        self.db.flush()
        return audit

    def update_order_status(
        self,
        order: ExecutionOrder,
        *,
        status: ExecutionStatus,
        broker_name: str | None = None,
        broker_order_id: str | None = None,
        filled_quantity: float | None = None,
        avg_fill_price: float | None = None,
        fees: float | None = None,
        slippage: float | None = None,
        paper_trade_id: UUID | None = None,
        raw_response: dict[str, Any] | None = None,
        rejection_reason: str | None = None,
        executed_by: UUID | None = None,
    ) -> ExecutionOrder:
        order.status = status.value
        if broker_name is not None:
            order.broker_name = broker_name
        if broker_order_id is not None:
            order.broker_order_id = broker_order_id
        if filled_quantity is not None:
            order.filled_quantity = filled_quantity
        if avg_fill_price is not None:
            order.avg_fill_price = avg_fill_price
        if fees is not None:
            order.fees = fees
        if slippage is not None:
            order.slippage = slippage
        if paper_trade_id is not None:
            order.paper_trade_id = paper_trade_id
        if raw_response is not None:
            order.raw_response = raw_response
        if rejection_reason is not None:
            order.rejection_reason = rejection_reason
        if executed_by is not None:
            order.executed_by = executed_by
        now = datetime.now(UTC)
        if status == ExecutionStatus.SUBMITTED and order.submitted_at is None:
            order.submitted_at = now
        if status in (
            ExecutionStatus.FILLED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.REJECTED,
            ExecutionStatus.FAILED,
        ):
            order.completed_at = now
        self.db.flush()
        return order

    def get_active_config(self, portfolio_id: UUID | None = None) -> ExecutionConfig | None:
        q = (
            select(ExecutionConfig)
            .where(ExecutionConfig.is_active.is_(True))
            .order_by(ExecutionConfig.created_at.desc())
        )
        if portfolio_id:
            q = q.where(ExecutionConfig.portfolio_id == portfolio_id)
        return self.db.scalar(q)

    def upsert_config(
        self,
        *,
        portfolio_id: UUID | None,
        execution_mode: ExecutionMode,
        broker_name: str | None = None,
        settings: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> ExecutionConfig:
        existing = self.get_active_config(portfolio_id)
        if existing:
            existing.execution_mode = execution_mode.value
            existing.broker_name = broker_name
            if settings is not None:
                existing.settings = settings
            if notes is not None:
                existing.notes = notes
            self.db.flush()
            return existing
        config = ExecutionConfig(
            portfolio_id=portfolio_id,
            execution_mode=execution_mode.value,
            broker_name=broker_name,
            is_active=True,
            settings=settings or {},
            notes=notes,
        )
        self.db.add(config)
        self.db.flush()
        return config
