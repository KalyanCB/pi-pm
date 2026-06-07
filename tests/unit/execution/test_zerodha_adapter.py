from decimal import Decimal

from app.core.config import Settings
from app.execution.adapters.zerodha_kite import LiveTradingDisabledError, ZerodhaKiteExecutionAdapter
from app.execution.constants import ExecutionMode, ExecutionStatus
from app.execution.domain import TradeRequest
from datetime import UTC, datetime
from uuid import uuid4


def _request() -> TradeRequest:
    return TradeRequest(
        portfolio_id=uuid4(),
        symbol="RELIANCE",
        side="BUY",
        quantity=Decimal("10"),
        strategy_name="momentum_v1",
        recommendation_id=uuid4(),
        approval_id=uuid4(),
        requested_by=uuid4(),
        execution_mode=ExecutionMode.LIVE,
        timestamp=datetime.now(UTC),
        client_order_id="test-1",
    )


def test_live_disabled_by_default():
    adapter = ZerodhaKiteExecutionAdapter(Settings(enable_live_trading=False))
    result = adapter.health_check()
    assert result.execution_status == ExecutionStatus.REJECTED
    assert "disabled" in (result.rejection_reason or "").lower()


def test_place_order_raises_when_live_disabled():
    adapter = ZerodhaKiteExecutionAdapter(Settings(enable_live_trading=False))
    try:
        adapter.place_order(_request())
        raised = False
    except LiveTradingDisabledError:
        raised = True
    assert raised


def test_health_accepted_when_credentials_and_flag_set():
    adapter = ZerodhaKiteExecutionAdapter(
        Settings(
            enable_live_trading=True,
            kite_api_key="key",
            kite_api_secret="secret",
            kite_access_token="token",
        )
    )
    result = adapter.health_check()
    assert result.execution_status == ExecutionStatus.ACCEPTED
