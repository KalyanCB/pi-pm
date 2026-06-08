"""Execution service — orchestrates adapter, lifecycle, and audit (Track K)."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.execution.adapters.factory import ExecutionAdapterFactory
from app.execution.adapters.zerodha_kite import LiveTradingDisabledError
from app.execution.constants import ExecutionMode, ExecutionStatus, TERMINAL_STATUSES
from app.execution.domain import TradeRequest, TradeResult
from app.execution.repositories.execution_repository import ExecutionRepository
from app.execution.state_machine import InvalidExecutionTransition, validate_transition
from app.models.execution import ExecutionOrder
from app.models.portfolio_position import PortfolioConfig
from app.models.recommendation import RecommendationApproval, RecommendationResult, RecommendationRun
from app.db.repositories.market_data_repository import MarketDataRepository
from app.models.stock import Stock
from app.services.portfolio_service import PortfolioService


class ExecutionValidationError(ValueError):
    pass


class ExecutionService:
    def __init__(
        self,
        db: Session,
        *,
        portfolio_id: UUID | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.portfolio_id = portfolio_id
        self.settings = settings or get_settings()
        self.repo = ExecutionRepository(db)

    def resolve_execution_mode(self, portfolio_id: UUID) -> ExecutionMode:
        config = self.repo.get_active_config(portfolio_id)
        if config:
            return ExecutionMode(config.execution_mode)
        portfolio_cfg = self.db.scalar(
            select(PortfolioConfig)
            .where(PortfolioConfig.portfolio_id == portfolio_id, PortfolioConfig.is_active.is_(True))
            .order_by(PortfolioConfig.created_at.desc())
        )
        if portfolio_cfg and portfolio_cfg.execution_mode:
            return ExecutionMode(portfolio_cfg.execution_mode)
        return ExecutionMode.PAPER

    def submit_from_recommendation(
        self,
        *,
        recommendation_id: UUID,
        requested_by: UUID,
        approval_id: UUID | None = None,
        as_of_date: date | None = None,
        idempotency_key: str | None = None,
        portfolio_id: UUID | None = None,
        execution_mode: ExecutionMode | None = None,
    ) -> ExecutionOrder:
        resolved_approval = approval_id or self._resolve_latest_approval(recommendation_id)
        if resolved_approval is None:
            raise ExecutionValidationError("No APPROVED approval found for recommendation")
        return self.submit_order(
            recommendation_id=recommendation_id,
            approval_id=resolved_approval,
            requested_by=requested_by,
            as_of_date=as_of_date,
            idempotency_key=idempotency_key,
            portfolio_id=portfolio_id,
            execution_mode=execution_mode,
        )

    def submit_order(
        self,
        *,
        recommendation_id: UUID,
        approval_id: UUID,
        requested_by: UUID,
        as_of_date: date | None = None,
        idempotency_key: str | None = None,
        portfolio_id: UUID | None = None,
        execution_mode: ExecutionMode | None = None,
    ) -> ExecutionOrder:
        pid = portfolio_id or self.portfolio_id
        if pid is None:
            raise ExecutionValidationError("portfolio_id is required")

        if idempotency_key:
            existing = self.repo.get_order_by_idempotency(idempotency_key)
            if existing:
                return existing

        result, approval = self._validate_approval(recommendation_id, approval_id)
        mode = execution_mode or self.resolve_execution_mode(pid)
        self._guard_live_mode(mode)

        side, strategy_name, symbol, quantity = self._build_order_fields(result, pid, as_of_date)
        client_order_id = f"exec-{uuid.uuid4().hex}"
        approved_by = self._resolve_user_id(approval.actor_id)

        order = self.repo.create_order(
            portfolio_id=pid,
            symbol=symbol,
            side=side,
            quantity=quantity,
            strategy_name=strategy_name,
            recommendation_id=recommendation_id,
            approval_id=approval_id,
            requested_by=requested_by,
            approved_by=approved_by,
            execution_mode=mode,
            client_order_id=client_order_id,
            idempotency_key=idempotency_key,
        )
        self.repo.record_event(
            order_id=order.id,
            from_status=None,
            to_status=ExecutionStatus.EXECUTION_PENDING.value,
            actor_id=requested_by,
            event_type="ORDER_CREATED",
        )
        self.repo.record_audit(
            order_id=order.id,
            action="CREATE_ORDER",
            execution_mode=mode,
            actor_id=requested_by,
            broker_name=None,
            request_payload={
                "recommendation_id": str(recommendation_id),
                "approval_id": str(approval_id),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
            },
            response_payload={"order_id": str(order.id), "status": order.status},
            correlation_id=client_order_id,
        )

        factory = ExecutionAdapterFactory(self.db, settings=self.settings, portfolio_id=str(pid))
        adapter = factory.get_adapter(mode)
        trade_request = TradeRequest(
            portfolio_id=pid,
            symbol=symbol,
            side=side,
            quantity=Decimal(str(quantity)),
            strategy_name=strategy_name or "",
            recommendation_id=recommendation_id,
            approval_id=approval_id,
            requested_by=requested_by,
            execution_mode=mode,
            timestamp=datetime.now(UTC),
            client_order_id=client_order_id,
            idempotency_key=idempotency_key,
            metadata={"as_of_date": (as_of_date or date.today()).isoformat()},
        )

        try:
            self._transition(order, ExecutionStatus.SUBMITTED, requested_by)
            self.repo.record_audit(
                order_id=order.id,
                action="SUBMIT_ORDER",
                execution_mode=mode,
                actor_id=requested_by,
                broker_name=adapter.broker_name,
                request_payload={"client_order_id": client_order_id},
                response_payload={"status": ExecutionStatus.SUBMITTED.value},
                correlation_id=client_order_id,
            )

            trade_result = adapter.place_order(trade_request)
            self._apply_adapter_result(order, trade_result, requested_by, mode)

            if trade_result.execution_status == ExecutionStatus.FILLED:
                paper_trade_id = trade_result.raw_response.get("paper_trade_id")
                if paper_trade_id:
                    self.repo.update_order_status(
                        order,
                        status=ExecutionStatus.FILLED,
                        paper_trade_id=UUID(paper_trade_id),
                    )
                self._update_recommendation_lifecycle(result, side)
        except LiveTradingDisabledError as exc:
            self._transition(order, ExecutionStatus.REJECTED, requested_by, reason=str(exc))
            self.repo.record_audit(
                order_id=order.id,
                action="LIVE_DISABLED",
                execution_mode=mode,
                actor_id=requested_by,
                broker_name=adapter.broker_name,
                request_payload={},
                response_payload={"error": str(exc)},
                correlation_id=client_order_id,
            )
        except Exception as exc:
            if order.status not in {s.value for s in TERMINAL_STATUSES}:
                self._transition(order, ExecutionStatus.FAILED, requested_by, reason=str(exc))
            self.repo.record_audit(
                order_id=order.id,
                action="EXECUTION_FAILED",
                execution_mode=mode,
                actor_id=requested_by,
                broker_name=getattr(adapter, "broker_name", None),
                request_payload={},
                response_payload={"error": str(exc)},
                correlation_id=client_order_id,
            )
            raise

        return order

    def cancel_order(self, order_id: UUID, *, actor_id: UUID) -> ExecutionOrder:
        order = self.repo.get_order(order_id)
        if order is None:
            raise ExecutionValidationError(f"Execution order {order_id} not found")
        current = ExecutionStatus(order.status)
        if current in TERMINAL_STATUSES:
            raise ExecutionValidationError(f"Cannot cancel terminal order in {current.value}")

        mode = ExecutionMode(order.execution_mode)
        factory = ExecutionAdapterFactory(
            self.db, settings=self.settings, portfolio_id=str(order.portfolio_id)
        )
        adapter = factory.get_adapter(mode)
        if not order.broker_order_id:
            self._transition(order, ExecutionStatus.CANCELLED, actor_id)
            return order

        self.repo.record_audit(
            order_id=order.id,
            action="CANCEL_ORDER",
            execution_mode=mode,
            actor_id=actor_id,
            broker_name=adapter.broker_name,
            request_payload={"broker_order_id": order.broker_order_id},
            response_payload={},
        )
        result = adapter.cancel_order(order.broker_order_id)
        self._apply_adapter_result(order, result, actor_id, mode)
        return order

    def get_order(self, order_id: UUID) -> ExecutionOrder | None:
        return self.repo.get_order(order_id)

    def list_orders(
        self,
        *,
        portfolio_id: UUID | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ExecutionOrder]:
        return self.repo.list_orders(portfolio_id=portfolio_id, status=status, limit=limit)

    def list_events(self, *, order_id: UUID | None = None, limit: int = 200) -> list:
        return self.repo.list_events(order_id=order_id, limit=limit)

    def health_check(self, portfolio_id: UUID | None = None) -> dict[str, Any]:
        pid = portfolio_id or self.portfolio_id
        mode = ExecutionMode.PAPER
        if pid:
            mode = self.resolve_execution_mode(pid)
        factory = ExecutionAdapterFactory(
            self.db, settings=self.settings, portfolio_id=str(pid) if pid else None
        )
        adapter = factory.get_adapter(mode)
        result = adapter.health_check()
        return {
            "execution_mode": mode.value,
            "broker_name": adapter.broker_name,
            "healthy": result.execution_status
            in (ExecutionStatus.FILLED, ExecutionStatus.ACCEPTED),
            "status": result.execution_status.value,
            "detail": result.raw_response,
            "rejection_reason": result.rejection_reason,
        }

    def get_config(self, portfolio_id: UUID | None = None) -> dict[str, Any]:
        pid = portfolio_id or self.portfolio_id
        config = self.repo.get_active_config(pid) if pid else self.repo.get_active_config()
        mode = self.resolve_execution_mode(pid) if pid else ExecutionMode.PAPER
        return {
            "portfolio_id": str(pid) if pid else None,
            "execution_mode": config.execution_mode if config else mode.value,
            "broker_name": config.broker_name if config else ("paper" if mode == ExecutionMode.PAPER else "zerodha_kite"),
            "enable_live_trading": self.settings.enable_live_trading,
            "settings": config.settings if config else {},
            "notes": config.notes if config else None,
        }

    def update_config(
        self,
        *,
        execution_mode: ExecutionMode,
        portfolio_id: UUID | None = None,
        broker_name: str | None = None,
        settings_payload: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        pid = portfolio_id or self.portfolio_id
        if execution_mode == ExecutionMode.LIVE:
            self._guard_live_mode(ExecutionMode.LIVE)
        config = self.repo.upsert_config(
            portfolio_id=pid,
            execution_mode=execution_mode,
            broker_name=broker_name,
            settings=settings_payload,
            notes=notes,
        )
        if pid:
            portfolio_cfg = self.db.scalar(
                select(PortfolioConfig)
                .where(PortfolioConfig.portfolio_id == pid, PortfolioConfig.is_active.is_(True))
                .order_by(PortfolioConfig.created_at.desc())
            )
            if portfolio_cfg:
                portfolio_cfg.execution_mode = execution_mode.value
                self.db.flush()
        return self.get_config(pid)

    def _guard_live_mode(self, mode: ExecutionMode) -> None:
        if mode == ExecutionMode.LIVE and not self.settings.enable_live_trading:
            raise LiveTradingDisabledError(
                "LIVE execution rejected — ENABLE_LIVE_TRADING must be true"
            )

    def _validate_approval(
        self, recommendation_id: UUID, approval_id: UUID
    ) -> tuple[RecommendationResult, RecommendationApproval]:
        result = self.db.get(RecommendationResult, recommendation_id)
        if result is None:
            raise ExecutionValidationError(f"Recommendation {recommendation_id} not found")
        approval = self.db.get(RecommendationApproval, approval_id)
        if approval is None:
            raise ExecutionValidationError(f"Approval {approval_id} not found")
        if approval.recommendation_result_id != recommendation_id:
            raise ExecutionValidationError("Approval does not match recommendation")
        if approval.decision != "APPROVED":
            raise ExecutionValidationError(f"Approval decision is {approval.decision}, expected APPROVED")
        if result.action == "EXIT_APPROVED":
            if result.lifecycle_state not in ("ACTIVE", "APPROVED", "CANDIDATE"):
                raise ExecutionValidationError(
                    f"Exit recommendation lifecycle is {result.lifecycle_state}"
                )
        elif result.lifecycle_state not in ("APPROVED", "ACTIVE"):
            raise ExecutionValidationError(
                f"Recommendation lifecycle is {result.lifecycle_state}, expected APPROVED or ACTIVE"
            )
        return result, approval

    def _build_order_fields(
        self,
        result: RecommendationResult,
        portfolio_id: UUID,
        as_of_date: date | None,
    ) -> tuple[str, str | None, str, float]:
        stock = self.db.get(Stock, result.stock_id)
        symbol = stock.symbol if stock else "UNKNOWN"
        rec_run = self.db.get(RecommendationRun, result.recommendation_run_id)
        strategy_name = rec_run.strategy_name if rec_run else None

        if result.action == "BUY":
            side = "BUY"
        elif result.action == "EXIT_APPROVED":
            side = "SELL"
        else:
            raise ExecutionValidationError(f"Cannot execute action {result.action}")

        portfolio_svc = PortfolioService(self.db, portfolio_id=portfolio_id)
        market_repo = MarketDataRepository(self.db)
        if side == "BUY":
            try:
                latest = market_repo.get_latest_market_data(result.stock_id)
                last_price = float(latest.close) if latest else 1.0
                alloc = portfolio_svc.compute_allocation(
                    conviction_band=result.conviction_band or "MEDIUM",
                    last_price=last_price,
                )
                quantity = max(1.0, alloc.quantity_estimate)
            except Exception:
                quantity = 1.0
        else:
            positions = portfolio_svc.get_positions()
            pos = next((p for p in positions if p.stock_id == result.stock_id), None)
            quantity = float(pos.quantity) if pos else 0.0
            if quantity <= 0:
                raise ExecutionValidationError("No position to exit")

        return side, strategy_name, symbol, quantity

    def _transition(
        self,
        order: ExecutionOrder,
        target: ExecutionStatus,
        actor_id: UUID,
        *,
        reason: str | None = None,
    ) -> None:
        current = ExecutionStatus(order.status)
        try:
            validate_transition(current, target)
        except InvalidExecutionTransition:
            if target in TERMINAL_STATUSES:
                target = ExecutionStatus.FAILED
            else:
                raise
        self.repo.update_order_status(order, status=target, executed_by=actor_id)
        payload: dict[str, Any] = {}
        if reason:
            payload["reason"] = reason
        self.repo.record_event(
            order_id=order.id,
            from_status=current.value,
            to_status=target.value,
            actor_id=actor_id,
            payload=payload,
        )

    def _apply_adapter_result(
        self,
        order: ExecutionOrder,
        result: TradeResult,
        actor_id: UUID,
        mode: ExecutionMode,
    ) -> None:
        current = ExecutionStatus(order.status)
        target = result.execution_status

        if target == ExecutionStatus.SUBMITTED and current == ExecutionStatus.EXECUTION_PENDING:
            self._transition(order, ExecutionStatus.SUBMITTED, actor_id)
            current = ExecutionStatus.SUBMITTED

        if target in (ExecutionStatus.ACCEPTED, ExecutionStatus.FILLED, ExecutionStatus.PARTIALLY_FILLED):
            if current == ExecutionStatus.SUBMITTED:
                self._transition(order, ExecutionStatus.ACCEPTED, actor_id)
                current = ExecutionStatus.ACCEPTED
            if target == ExecutionStatus.PARTIALLY_FILLED:
                self._transition(order, ExecutionStatus.PARTIALLY_FILLED, actor_id)
                current = ExecutionStatus.PARTIALLY_FILLED

        if target == ExecutionStatus.FILLED:
            self.repo.update_order_status(
                order,
                status=ExecutionStatus.FILLED,
                broker_name=result.broker_name,
                broker_order_id=result.broker_order_id,
                filled_quantity=float(result.filled_quantity),
                avg_fill_price=float(result.avg_fill_price) if result.avg_fill_price else None,
                fees=float(result.fees) if result.fees else None,
                slippage=float(result.slippage) if result.slippage else None,
                raw_response=result.raw_response,
                executed_by=actor_id,
            )
            self.repo.record_event(
                order_id=order.id,
                from_status=current.value,
                to_status=ExecutionStatus.FILLED.value,
                actor_id=actor_id,
            )
        elif target in (ExecutionStatus.REJECTED, ExecutionStatus.CANCELLED, ExecutionStatus.FAILED):
            self._transition(
                order,
                target,
                actor_id,
                reason=result.rejection_reason,
            )
            self.repo.update_order_status(
                order,
                status=target,
                broker_name=result.broker_name,
                broker_order_id=result.broker_order_id,
                raw_response=result.raw_response,
                rejection_reason=result.rejection_reason,
            )

        self.repo.record_audit(
            order_id=order.id,
            action="BROKER_RESPONSE",
            execution_mode=mode,
            actor_id=actor_id,
            broker_name=result.broker_name,
            request_payload={"broker_order_id": result.broker_order_id},
            response_payload={
                "status": result.execution_status.value,
                "filled_quantity": str(result.filled_quantity),
                "avg_fill_price": str(result.avg_fill_price) if result.avg_fill_price else None,
                "raw_response": result.raw_response,
            },
        )

    def _resolve_latest_approval(self, recommendation_id: UUID) -> UUID | None:
        approval = self.db.scalar(
            select(RecommendationApproval)
            .where(
                RecommendationApproval.recommendation_result_id == recommendation_id,
                RecommendationApproval.decision == "APPROVED",
            )
            .order_by(RecommendationApproval.decided_at.desc())
        )
        return approval.id if approval else None

    @staticmethod
    def _resolve_user_id(actor_id: str) -> UUID | None:
        try:
            return UUID(actor_id)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _update_recommendation_lifecycle(result: RecommendationResult, side: str) -> None:
        if side == "BUY" and result.lifecycle_state == "APPROVED":
            result.lifecycle_state = "ACTIVE"
        elif side == "SELL":
            result.lifecycle_state = "CLOSED"
