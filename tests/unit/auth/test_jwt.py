"""Unit tests for JWT token creation and validation."""
from uuid import uuid4

import pytest

from app.auth.exceptions import TokenError
from app.auth.jwt import create_access_token, decode_access_token
from app.auth.constants import UserRole
from app.core.config import Settings


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        jwt_secret_key="test-secret-key-for-jwt",
        jwt_algorithm="HS256",
        jwt_access_token_minutes=15,
    )


def test_access_token_roundtrip(auth_settings):
    user_id = uuid4()
    portfolio_id = uuid4()
    token, expires = create_access_token(
        user_id=user_id,
        email="test@example.com",
        roles=[UserRole.OWNER],
        portfolio_id=portfolio_id,
        settings=auth_settings,
    )
    payload = decode_access_token(token, auth_settings)
    assert payload["sub"] == str(user_id)
    assert payload["email"] == "test@example.com"
    assert "owner" in payload["roles"]
    assert payload["portfolio_id"] == str(portfolio_id)
    assert expires is not None


def test_invalid_token_rejected(auth_settings):
    with pytest.raises(TokenError):
        decode_access_token("not-a-valid-token", auth_settings)
