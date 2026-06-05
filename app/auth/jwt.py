"""JWT access and refresh token helpers."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt

from app.auth.constants import UserRole
from app.auth.exceptions import TokenError
from app.core.config import Settings


def create_access_token(
    *,
    user_id: UUID,
    email: str,
    roles: list[UserRole],
    portfolio_id: UUID | None,
    settings: Settings,
) -> tuple[str, datetime]:
    expires = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "roles": [r.value for r in roles],
        "portfolio_id": str(portfolio_id) if portfolio_id else None,
        "type": "access",
        "exp": expires,
        "iat": datetime.now(UTC),
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise TokenError("Invalid token type")
    return payload


def create_refresh_token_value() -> str:
    return str(uuid4())
