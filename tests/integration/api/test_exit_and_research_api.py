from datetime import date

from fastapi.testclient import TestClient


def test_research_intelligence_generate_requires_data(client: TestClient):
    response = client.post(
        "/api/v1/analytics/research-intelligence/generate",
        json={
            "universe_code": "PI_PM_CORE",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "persist": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "executive_committee_summary" in body["reports"]


def test_exit_analytics_runs_empty(client: TestClient):
    response = client.get("/api/v1/analytics/exit/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
