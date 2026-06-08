"""Exit notification events (ADR-033 §4).

NotificationEvent is a plain dataclass — no DB table.
The delivery layer (API response, push, email) is caller's concern.

Dedup rule: emit only on NEW trigger or SEVERITY UPGRADE.
The caller (intraday service) enforces this by checking existing state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class NotificationEvent:
    """One notification that should reach the owner."""

    position_id: UUID
    stock_symbol: str
    trigger_code: str          # EXIT_STOP_LOSS | EXIT_TRAILING_STOP | …
    urgency: str               # LOW | NORMAL | HIGH | CRITICAL
    unrealized_pnl_pct: float | None
    message: str
    auto_executed: bool = False
    fired_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def channel_critical(self) -> bool:
        """Should this go to high-urgency channels (banner, push)?"""
        return self.urgency == "CRITICAL"

    @property
    def channel_high(self) -> bool:
        """Should this go to EXIT tab badge and dashboard?"""
        return self.urgency in ("HIGH", "CRITICAL")


def build_notification(
    *,
    position_id: UUID,
    symbol: str,
    trigger_code: str,
    urgency: str,
    unrealized_pnl_pct: float | None,
    auto_executed: bool = False,
) -> NotificationEvent:
    pnl_str = f"{unrealized_pnl_pct:.1f}%" if unrealized_pnl_pct is not None else "unknown"
    if auto_executed:
        msg = (
            f"AUTO-EXIT executed for {symbol}: {trigger_code} — "
            f"unrealized {pnl_str} breached critical stop. "
            f"Position closed automatically (ADR-033 critical override)."
        )
    elif urgency == "CRITICAL":
        msg = (
            f"CRITICAL: {symbol} at {pnl_str} — {trigger_code}. "
            f"Confirm exit immediately."
        )
    elif urgency == "HIGH":
        msg = (
            f"{symbol} exit candidate: {trigger_code} ({pnl_str}). "
            f"Review pending exits."
        )
    else:
        msg = f"{symbol}: {trigger_code} ({pnl_str})."

    return NotificationEvent(
        position_id=position_id,
        stock_symbol=symbol,
        trigger_code=trigger_code,
        urgency=urgency,
        unrealized_pnl_pct=unrealized_pnl_pct,
        message=msg,
        auto_executed=auto_executed,
    )
