"""Health, liveness, and readiness endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import Settings, get_settings
from app.schemas.health import HealthCheckResult, HealthResponse

router = APIRouter()

_APP_VERSION = "0.4.1"
_START_TIME = time.monotonic()


def _uptime_seconds() -> float:
    return round(time.monotonic() - _START_TIME, 2)


def _check_database(db: Session) -> HealthCheckResult:
    try:
        db.execute(text("SELECT 1"))
        return HealthCheckResult(status="ok", detail="connected")
    except Exception as exc:
        return HealthCheckResult(status="fail", detail=str(exc))


@router.get("/health/live")
def liveness() -> dict[str, str]:
    """Process liveness probe — no dependency checks."""
    return {"status": "ok", "service": "pi-pm"}


@router.get("/health/ready", response_model=HealthResponse)
def readiness(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Readiness probe — verifies database connectivity."""
    db_check = _check_database(db)
    checks = {"database": db_check}
    overall = "ok" if db_check.status == "ok" else "fail"
    if overall != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status=overall,
        service="pi-pm",
        version=_APP_VERSION,
        environment=settings.app_env,
        uptime_seconds=_uptime_seconds(),
        database="connected" if db_check.status == "ok" else "disconnected",
        checks=checks,
    )


@router.get("/health", response_model=HealthResponse)
def health_check(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Detailed health status (backward-compatible database field)."""
    db_check = _check_database(db)
    checks = {"database": db_check}
    overall = "ok" if db_check.status == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        service="pi-pm",
        version=_APP_VERSION,
        environment=settings.app_env,
        uptime_seconds=_uptime_seconds(),
        database="connected" if db_check.status == "ok" else "disconnected",
        checks=checks,
    )
