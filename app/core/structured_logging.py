from __future__ import annotations

import logging
from typing import Any


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit a structured key=value log line for operational traceability."""
    parts = [f"{key}={_format_value(value)}" for key, value in fields.items()]
    logger.info("%s %s", event, " ".join(parts))


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.6f}"
    text = str(value)
    if " " in text:
        return f'"{text}"'
    return text
