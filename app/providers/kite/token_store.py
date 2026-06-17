"""Kite access token persistence.

Access tokens expire at 06:00 IST the next morning. This module
reads/writes the token to the DB settings table so it survives
container restarts and can be updated via the /ops/kite/callback
OAuth endpoint without touching the .env file.

Fall-back chain:
  1. DB row  kite_access_token
  2. env var KITE_ACCESS_TOKEN (from Settings)
  3. None → Kite calls will fail until authenticated
"""
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_SETTING_KEY = "kite_access_token"


def get_token(db) -> str | None:
    """Read the access token from the app_settings table, then env fall-back."""
    try:
        from sqlalchemy import text
        row = db.execute(
            text("SELECT value FROM app_settings WHERE key = :k"),
            {"k": _SETTING_KEY},
        ).first()
        if row and row[0]:
            return row[0]
    except Exception:
        logger.debug("app_settings not available, falling back to env")

    from app.core.config import get_settings
    token = get_settings().kite_access_token
    return token or None


def save_token(db, token: str) -> None:
    """Upsert the access token into app_settings."""
    from sqlalchemy import text
    db.execute(
        text("""
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (:k, :v, now())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
        """),
        {"k": _SETTING_KEY, "v": token},
    )
    db.commit()
    logger.info("kite_token_store: access token saved to DB")
