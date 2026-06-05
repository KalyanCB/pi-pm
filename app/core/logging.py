import logging

from app.core.config import Settings
from app.core.structured_logging import setup_structured_logging


def setup_logging(settings: Settings) -> None:
    """Configure application logging (structured JSON by default)."""
    if settings.app_env in {"production", "staging", "test"}:
        setup_structured_logging(settings)
        return

    # Human-readable format for local development
    import sys

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
        force=True,
    )
