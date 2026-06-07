"""Paper execution adapter — simulates broker lifecycle (Track K)."""
from __future__ import annotations

import time
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.execution.constants import ExecutionStatus
from app.execution.domain import TradeRequest, TradeResult
from app.services.paper_trade_service import PaperTradeService
from app.services.portfolio_service import PortfolioService


class PaperExecutionAdapter:
    """Simulates SUBMITTED → ACCEPTED → FILLED using the existing paper engine."""

    def __init__(
        self,
        db: Session,
        *,
        portfolio_service: PortfolioService | None = None,
        latency_ms: int = 0,
    ) -> None:
        self.db = db
        self._latency_ms = latency_ms
        self._paper_service = PaperTradeService(
            db,
            portfolio_service=portfolio_service or PortfolioService(db),
        )

    @property
    def broker_name(self) -> str:
        return "paper"

    def _simulate_latency(self) -> None:
        if self._latency_ms > 0:
            time.sleep(self._latency_ms / 1000.0)

    def place_order(self, request: TradeRequest) -> TradeResult:
        paper_order_id = f"paper-{uuid.uuid4().hex[:12]}"
        as_of = request.metadata.get("as_of_date")
        fill_date = date.fromisoformat(as_of) if isinstance(as_of, str) else date.today()

        self._simulate_latency()
        submitted = self._status_result(
            paper_order_id,
            ExecutionStatus.SUBMITTED,
            filled_quantity=Decimal("0"),
        )

        self._simulate_latency()
        accepted = self._status_result(
            paper_order_id,
            ExecutionStatus.ACCEPTED,
            filled_quantity=Decimal("0"),
            prior=submitted,
        )

        side = request.side.upper()
        if side == "BUY":
            trade = self._paper_service.execute_entry(
                recommendation_result_id=request.recommendation_id,
                as_of_date=fill_date,
                idempotency_key=request.idempotency_key,
            )
        elif side == "SELL":
            trade = self._paper_service.execute_exit(
                recommendation_result_id=request.recommendation_id,
                as_of_date=fill_date,
                idempotency_key=request.idempotency_key,
            )
        else:
            return TradeResult(
                broker_name=self.broker_name,
                broker_order_id=paper_order_id,
                execution_status=ExecutionStatus.REJECTED,
                filled_quantity=Decimal("0"),
                avg_fill_price=None,
                rejection_reason=f"Unsupported side: {request.side}",
            )

        fees = Decimal(str(trade.metadata_.get("fee", trade.metadata_.get("fees", 20))))
        slippage_bps = Decimal(str(trade.metadata_.get("slippage_bps", 5)))
        fill_price = Decimal(str(trade.fill_price))
        fill_qty = Decimal(str(trade.fill_quantity))

        return TradeResult(
            broker_name=self.broker_name,
            broker_order_id=paper_order_id,
            execution_status=ExecutionStatus.FILLED,
            filled_quantity=fill_qty,
            avg_fill_price=fill_price,
            fees=fees,
            slippage=slippage_bps,
            filled_at=trade.filled_at or datetime.now(UTC),
            raw_response={
                "paper_trade_id": str(trade.id),
                "lifecycle": [
                    submitted.execution_status.value,
                    accepted.execution_status.value,
                    ExecutionStatus.FILLED.value,
                ],
                "last_close": trade.metadata_.get("last_close"),
            },
        )

    def get_order_status(self, broker_order_id: str) -> TradeResult:
        return TradeResult(
            broker_name=self.broker_name,
            broker_order_id=broker_order_id,
            execution_status=ExecutionStatus.FILLED,
            filled_quantity=Decimal("0"),
            avg_fill_price=None,
            raw_response={"note": "paper orders are synchronous; status is terminal"},
        )

    def cancel_order(self, broker_order_id: str) -> TradeResult:
        return TradeResult(
            broker_name=self.broker_name,
            broker_order_id=broker_order_id,
            execution_status=ExecutionStatus.CANCELLED,
            filled_quantity=Decimal("0"),
            avg_fill_price=None,
            raw_response={"note": "paper order already terminal or not found"},
        )

    def health_check(self) -> TradeResult:
        return TradeResult(
            broker_name=self.broker_name,
            broker_order_id=None,
            execution_status=ExecutionStatus.FILLED,
            filled_quantity=Decimal("0"),
            avg_fill_price=None,
            raw_response={"healthy": True},
        )

    def sync_holdings(self, portfolio_id: str) -> list[dict]:
        return []

    def sync_positions(self, portfolio_id: str) -> list[dict]:
        return []

    @staticmethod
    def _status_result(
        broker_order_id: str,
        status: ExecutionStatus,
        *,
        filled_quantity: Decimal,
        prior: TradeResult | None = None,
    ) -> TradeResult:
        lifecycle = []
        if prior and prior.raw_response.get("lifecycle"):
            lifecycle = list(prior.raw_response["lifecycle"])
        lifecycle.append(status.value)
        return TradeResult(
            broker_name="paper",
            broker_order_id=broker_order_id,
            execution_status=status,
            filled_quantity=filled_quantity,
            avg_fill_price=None,
            raw_response={"lifecycle": lifecycle},
        )
