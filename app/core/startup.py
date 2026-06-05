"""Startup validation for production readiness."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import text

from app.core.config import Settings
from app.db.session import get_engine

logger = logging.getLogger(__name__)


@dataclass
class StartupCheck:
    name: str
    ok: bool
    detail: str | None = None


def run_startup_checks(settings: Settings) -> list[StartupCheck]:
    """Validate critical dependencies before serving traffic."""
    checks: list[StartupCheck] = []

    try:
        engine = get_engine(settings)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks.append(StartupCheck(name="database", ok=True, detail="connected"))
    except Exception as exc:
        checks.append(StartupCheck(name="database", ok=False, detail=str(exc)))

    if settings.app_env == "production" and settings.debug:
        checks.append(
            StartupCheck(
                name="config",
                ok=False,
                detail="DEBUG must be disabled in production",
            )
        )
    else:
        checks.append(StartupCheck(name="config", ok=True))

    return checks


def validate_startup(settings: Settings, *, fail_fast: bool = False) -> list[StartupCheck]:
    checks = run_startup_checks(settings)
    failures = [c for c in checks if not c.ok]

    for check in checks:
        if check.ok:
            logger.info("startup check passed: %s", check.name)
        else:
            logger.error("startup check failed: %s — %s", check.name, check.detail)

    if failures and fail_fast:
        messages = ", ".join(f"{c.name}: {c.detail}" for c in failures)
        raise RuntimeError(f"Startup validation failed: {messages}")

    return checks
