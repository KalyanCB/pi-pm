"""Zerodha Kite execution adapter — contract only, live disabled by default (Track K)."""
from __future__ import annotations

from decimal import Decimal

from app.core.config import Settings, get_settings
from app.execution.constants import ExecutionStatus
from app.execution.domain import TradeRequest, TradeResult


class LiveTradingDisabledError(Exception):
    """Raised when LIVE execution is attempted without safety gates."""


class ZerodhaKiteExecutionAdapter:
    """Zerodha Kite adapter stub — requires env credentials and ENABLE_LIVE_TRADING."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def broker_name(self) -> str:
        return "zerodha_kite"

    def _credentials_configured(self) -> bool:
        return bool(
            self._settings.kite_api_key
            and self._settings.kite_api_secret
            and self._settings.kite_access_token
        )

    def _assert_live_enabled(self) -> None:
        if not self._settings.enable_live_trading:
            raise LiveTradingDisabledError(
                "LIVE trading disabled — set ENABLE_LIVE_TRADING=true to enable"
            )
        if not self._credentials_configured():
            raise LiveTradingDisabledError(
                "Zerodha credentials missing — set KITE_API_KEY, KITE_API_SECRET, KITE_ACCESS_TOKEN"
            )

    def place_order(self, request: TradeRequest) -> TradeResult:
        self._assert_live_enabled()
        # Future: kite.place_order(...) — not enabled in development
        return TradeResult(
            broker_name=self.broker_name,
            broker_order_id=None,
            execution_status=ExecutionStatus.REJECTED,
            filled_quantity=Decimal("0"),
            avg_fill_price=None,
            rejection_reason="Zerodha Kite adapter not yet connected",
            raw_response={"mode": "live", "configured": True},
        )

    def get_order_status(self, broker_order_id: str) -> TradeResult:
        self._assert_live_enabled()
        return TradeResult(
            broker_name=self.broker_name,
            broker_order_id=broker_order_id,
            execution_status=ExecutionStatus.SUBMITTED,
            filled_quantity=Decimal("0"),
            avg_fill_price=None,
            raw_response={"status": "not_implemented"},
        )

    def cancel_order(self, broker_order_id: str) -> TradeResult:
        self._assert_live_enabled()
        return TradeResult(
            broker_name=self.broker_name,
            broker_order_id=broker_order_id,
            execution_status=ExecutionStatus.CANCELLED,
            filled_quantity=Decimal("0"),
            avg_fill_price=None,
            raw_response={"status": "not_implemented"},
        )

    def health_check(self) -> TradeResult:
        if not self._settings.enable_live_trading:
            return TradeResult(
                broker_name=self.broker_name,
                broker_order_id=None,
                execution_status=ExecutionStatus.REJECTED,
                filled_quantity=Decimal("0"),
                avg_fill_price=None,
                rejection_reason="LIVE trading disabled",
                raw_response={"enable_live_trading": False},
            )
        if not self._credentials_configured():
            return TradeResult(
                broker_name=self.broker_name,
                broker_order_id=None,
                execution_status=ExecutionStatus.REJECTED,
                filled_quantity=Decimal("0"),
                avg_fill_price=None,
                rejection_reason="Credentials not configured",
                raw_response={"credentials_configured": False},
            )
        return TradeResult(
            broker_name=self.broker_name,
            broker_order_id=None,
            execution_status=ExecutionStatus.ACCEPTED,
            filled_quantity=Decimal("0"),
            avg_fill_price=None,
            raw_response={"credentials_configured": True, "connected": False},
        )

    def sync_holdings(self, portfolio_id: str) -> list[dict]:
        self._assert_live_enabled()
        return []

    def sync_positions(self, portfolio_id: str) -> list[dict]:
        self._assert_live_enabled()
        return []
