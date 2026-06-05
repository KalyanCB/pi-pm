"""Integration tests for authentication API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def auth_client(db_session, monkeypatch):
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


def test_register_and_login(auth_client):
    reg = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "password123",
            "display_name": "New User",
        },
    )
    assert reg.status_code == 201
    body = reg.json()
    assert "access_token" in body
    assert "refresh_token" in body

    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "newuser@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_login_invalid_password(auth_client):
    auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "fail@example.com",
            "password": "password123",
            "display_name": "Fail User",
        },
    )
    resp = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "fail@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_protected_route_requires_auth(auth_client):
    resp = auth_client.get("/api/v1/portfolio/summary")
    assert resp.status_code == 401


def test_refresh_token_rotation(auth_client):
    reg = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "password123",
            "display_name": "Refresh User",
        },
    )
    old_refresh = reg.json()["refresh_token"]
    refresh_resp = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refresh_resp.status_code == 200
    new_refresh = refresh_resp.json()["refresh_token"]
    assert new_refresh != old_refresh

    # Old token should be revoked
    again = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert again.status_code == 401


def test_me_endpoint(auth_client):
    reg = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "password": "password123",
            "display_name": "Me User",
        },
    )
    token = reg.json()["access_token"]
    resp = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"
    assert "owner" in resp.json()["roles"]
