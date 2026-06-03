"""QRC-facing validation status normalization for current-day ranking runs."""

from __future__ import annotations

from typing import Any

from app.validation.constants import (
    VALIDATION_STATUS_INSUFFICIENT_DATA,
    VALIDATION_STATUS_PENDING,
)

PENDING_REASON_FORWARD_HORIZONS = "forward_return_horizons_not_available"


def normalize_validation_status_for_packet(
    raw_status: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Return (packet_status, database_status, pending_reason) for investment packets."""
    if raw_status is None:
        return None, None, None
    if raw_status == VALIDATION_STATUS_INSUFFICIENT_DATA:
        return (
            VALIDATION_STATUS_PENDING,
            raw_status,
            PENDING_REASON_FORWARD_HORIZONS,
        )
    return raw_status, raw_status, None


def is_current_validation_pending(validation: dict[str, Any] | None) -> bool:
    """True when forward validation for the current ranking run is not yet usable."""
    if not validation:
        return False
    status = validation.get("status")
    if status in (VALIDATION_STATUS_PENDING, VALIDATION_STATUS_INSUFFICIENT_DATA):
        return True
    return validation.get("database_status") == VALIDATION_STATUS_INSUFFICIENT_DATA


def latest_historical_validation_block(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Most recent completed validation from historical_validation_context."""
    hist = payload.get("historical_validation_context") or {}
    recent = list(hist.get("recent_completed_validations") or [])
    if not recent:
        return {}
    latest = recent[-1]
    return {
        "status": "completed",
        "source": "historical_validation_context",
        "as_of_date": latest.get("as_of_date"),
        "report_id": latest.get("report_id"),
        "regime_label": latest.get("regime_label"),
        "horizon_metrics": list(latest.get("horizon_metrics") or []),
        "decile_metrics": list(latest.get("decile_metrics") or []),
    }
