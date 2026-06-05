"""Structured JSON logging with correlation ID support."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.core.context import correlation_id_var, request_id_var


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        correlation_id = correlation_id_var.get()
        request_id = request_id_var.get()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        if request_id:
            payload["request_id"] = request_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key in ("method", "path", "status_code", "duration_ms", "client_ip"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        return json.dumps(payload, default=str)


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit a structured log line with arbitrary key-value fields."""
    extra = {k: v for k, v in fields.items() if v is not None}
    logger.info(event, extra=extra)


def setup_structured_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
