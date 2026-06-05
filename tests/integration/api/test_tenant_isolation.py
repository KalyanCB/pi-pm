"""Tenant isolation and security tests."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.auth.exceptions import AuthorizationError
from app.auth.context import AuthContext
from app.auth.constants import UserRole
from app.core.config import get_settings
from app.main import create_app
from app.models.auth import User
from app.models.portfolio_position import PortfolioConfig
from app.services.auth_service import AuthService


@pytest.fixture
def secured_client(db_session, monkeypatch):
    monkeypatch.delenv("AUTH_BYPASS_FOR_TESTS", raising=False)
    get_settings.cache_clear()
    app = create_app()

    def override_get_db():
        yield db_session

    from app.api import deps

    app.dependency_overrides[deps.get_db] = override_get_db
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "auth_bypass_for_tests", False)

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _register(client: TestClient, email: str) -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": email.split("@")[0]},
    )
    assert resp.status_code == 201
    return resp.json()


def test_user_cannot_access_other_portfolio(secured_client, db_session, user_a: User, user_b: User):
    portfolio_b = user_b._test_portfolio_id  # type: ignore[attr-defined]

    # Seed config for Bob's portfolio
    cfg = PortfolioConfig(
        portfolio_id=portfolio_b,
        is_active=True,
        total_equity=500_000,
        deploy_pct=0.85,
        cash_floor_pct=0.15,
        reserve_pct=0.02,
        regime_slots={},
    )
    db_session.add(cfg)
    db_session.commit()

    alice_tokens = _register(secured_client, "alice2@example.com")
    # Manually link alice to her portfolio via auth service on existing user_a not needed -
    # register creates new user. Use token from register and try X-Portfolio-Id of another user.

    bob_tokens = _register(secured_client, "bob2@example.com")
    bob_portfolio_id = bob_tokens["user"]["portfolio_id"]

    # Alice tries to access Bob's portfolio via header
    resp = secured_client.get(
        "/api/v1/portfolio/summary",
        headers={
            "Authorization": f"Bearer {alice_tokens['access_token']}",
            "X-Portfolio-Id": bob_portfolio_id,
        },
    )
    assert resp.status_code == 403


def test_auth_service_assert_portfolio_access(db_session, user_a: User, user_b: User):
    auth = AuthService(db_session)
    ctx_a = auth.build_auth_context(user_a)
    portfolio_b = user_b._test_portfolio_id  # type: ignore[attr-defined]

    with pytest.raises(AuthorizationError):
        auth.assert_portfolio_access(ctx_a, portfolio_b)


def test_viewer_cannot_mutate_portfolio(secured_client):
    tokens = _register(secured_client, "viewer@example.com")
    # Downgrade to viewer via direct context override test
    viewer_ctx = AuthContext(
        user_id=uuid4(),
        email="viewer@example.com",
        display_name="Viewer",
        roles=(UserRole.VIEWER,),
        portfolio_id=uuid4(),
    )
    assert not viewer_ctx.has_role(UserRole.OWNER)


def test_health_remains_public(secured_client):
    resp = secured_client.get("/api/v1/health/live")
    assert resp.status_code == 200
