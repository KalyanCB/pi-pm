"""Tests for request context middleware and structured logging."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import create_app


def test_request_id_headers_present():
    app = create_app()
    mock_session = MagicMock()
    mock_session.execute.return_value = None

    def override_get_db():
        yield mock_session

    from app.api import deps

    app.dependency_overrides[deps.get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID")
    assert response.headers.get("X-Request-ID")
    app.dependency_overrides.clear()


def test_error_response_includes_error_code():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/stocks/UNKNOWN_SYMBOL_XYZ")
    assert response.status_code in {404, 422}
    body = response.json()
    assert "detail" in body
    if response.status_code == 404:
        assert body.get("error_code") == "not_found"
