from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import create_app


def _client_with_mock_db():
    app = create_app()
    mock_session = MagicMock()
    mock_session.execute.return_value = None

    def override_get_db():
        yield mock_session

    from app.api import deps

    app.dependency_overrides[deps.get_db] = override_get_db
    return app, TestClient(app)


def test_health_endpoint_ok():
    app, client = _client_with_mock_db()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["service"] == "pi-pm"
    assert "version" in body
    assert "uptime_seconds" in body
    assert body["checks"]["database"]["status"] == "ok"
    app.dependency_overrides.clear()


def test_liveness_endpoint():
    app, client = _client_with_mock_db()
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    app.dependency_overrides.clear()


def test_readiness_endpoint_ok():
    app, client = _client_with_mock_db()
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "ok"
    app.dependency_overrides.clear()


def test_readiness_endpoint_db_failure():
    app = create_app()
    mock_session = MagicMock()
    mock_session.execute.side_effect = RuntimeError("connection refused")

    def override_get_db():
        yield mock_session

    from app.api import deps

    app.dependency_overrides[deps.get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "fail"
    assert body["database"] == "disconnected"
    app.dependency_overrides.clear()


def test_correlation_id_header():
    app, client = _client_with_mock_db()
    response = client.get("/api/v1/health/live", headers={"X-Correlation-ID": "test-corr-123"})
    assert response.headers.get("X-Correlation-ID") == "test-corr-123"
    assert response.headers.get("X-Request-ID")
    app.dependency_overrides.clear()
