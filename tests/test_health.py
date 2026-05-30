from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_ok():
    app = create_app()
    client = TestClient(app)

    mock_session = MagicMock()
    mock_session.execute.return_value = None

    def override_get_db():
        yield mock_session

    from app.api import deps

    app.dependency_overrides[deps.get_db] = override_get_db

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"

    app.dependency_overrides.clear()
