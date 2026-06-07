"""Paper Trading Pilot Command Center — read-only operational visibility."""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_pilot_command_center_service
from app.services.pilot_command_center_service import PilotCommandCenterService

router = APIRouter()


@router.get("/command-center")
def get_command_center(
    as_of_date: date | None = Query(default=None),
    service: PilotCommandCenterService = Depends(get_pilot_command_center_service),
) -> Any:
    """Pilot overview — status, alerts, success metrics, dashboard links."""
    return service.get_command_center(as_of_date)


@router.get("/dashboard/pilot")
def get_pilot_dashboard(
    as_of_date: date | None = Query(default=None),
    service: PilotCommandCenterService = Depends(get_pilot_command_center_service),
) -> Any:
    """Pilot dashboard — portfolio health, NAV trend, daily activity."""
    return service.get_pilot_dashboard(as_of_date)


@router.get("/dashboard/health")
def get_health_dashboard(
    as_of_date: date | None = Query(default=None),
    service: PilotCommandCenterService = Depends(get_pilot_command_center_service),
) -> Any:
    """Portfolio health — limits, reconciliation, risk, analytics gate."""
    return service.get_health_dashboard(as_of_date)


@router.get("/dashboard/recommendations")
def get_recommendation_dashboard(
    as_of_date: date | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    service: PilotCommandCenterService = Depends(get_pilot_command_center_service),
) -> Any:
    """Recommendation performance — quality, conviction, regime, exits."""
    return service.get_recommendation_dashboard(
        as_of_date=as_of_date, from_date=from_date, to_date=to_date
    )


@router.get("/dashboard/committee")
def get_committee_dashboard(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    service: PilotCommandCenterService = Depends(get_pilot_command_center_service),
) -> Any:
    """Committee effectiveness — ARGS advisory value (observation only)."""
    return service.get_committee_dashboard(from_date=from_date, to_date=to_date)


@router.get("/dashboard/trust")
def get_trust_dashboard(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    service: PilotCommandCenterService = Depends(get_pilot_command_center_service),
) -> Any:
    """Trust dashboard — calibration, stability, reliability trends."""
    return service.get_trust_dashboard(from_date=from_date, to_date=to_date)


@router.get("/dashboard/operational")
def get_operational_dashboard(
    as_of_date: date | None = Query(default=None),
    service: PilotCommandCenterService = Depends(get_pilot_command_center_service),
) -> Any:
    """Operational dashboard — batch history, alerts, success metrics."""
    return service.get_operational_dashboard(as_of_date)


@router.get("/alerts")
def get_alerts(
    as_of_date: date | None = Query(default=None),
    service: PilotCommandCenterService = Depends(get_pilot_command_center_service),
) -> Any:
    """Current pilot alerts — batch, recon, NAV, recommendation, portfolio."""
    return service.get_alerts(as_of_date)


@router.get("/metrics/success")
def get_success_metrics(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    service: PilotCommandCenterService = Depends(get_pilot_command_center_service),
) -> Any:
    """Pilot success metrics for a date window."""
    return service.get_success_metrics(from_date=from_date, to_date=to_date)


@router.get("/reports/{report_type}")
def get_report(
    report_type: str,
    as_of_date: date | None = Query(default=None),
    pilot_start: date | None = Query(default=None),
    pilot_end: date | None = Query(default=None),
    service: PilotCommandCenterService = Depends(get_pilot_command_center_service),
) -> Any:
    """Pilot report — daily | weekly | monthly | final."""
    if report_type not in ("daily", "weekly", "monthly", "final"):
        raise HTTPException(status_code=422, detail="report_type must be daily|weekly|monthly|final")
    return service.get_report(
        report_type,
        as_of_date=as_of_date,
        pilot_start=pilot_start,
        pilot_end=pilot_end,
    )
