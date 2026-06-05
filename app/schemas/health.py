"""Health check response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthCheckResult(BaseModel):
    status: str = Field(description="ok | fail")
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str = Field(description="ok | degraded | fail")
    service: str
    version: str
    environment: str
    uptime_seconds: float
    database: str = Field(description="connected | disconnected (legacy field)")
    checks: dict[str, HealthCheckResult]
