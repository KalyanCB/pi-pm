"""Pilot command center service tests."""
from datetime import date

from sqlalchemy import func, select

from app.models.recommendation import RecommendationRun
from app.services.pilot_command_center_service import PilotCommandCenterService


def test_command_center_structure(db_session):
    svc = PilotCommandCenterService(db_session)
    result = svc.get_command_center(date(2026, 6, 5))
    assert result["as_of_date"] == "2026-06-05"
    assert "alert_summary" in result
    assert "dashboards" in result
    assert result["pilot_day"] >= 1


def test_alerts_endpoint_delegates(db_session):
    svc = PilotCommandCenterService(db_session)
    alerts = svc.get_alerts(date(2026, 6, 5))
    assert isinstance(alerts, list)


def test_daily_report_structure(db_session):
    svc = PilotCommandCenterService(db_session)
    report = svc.get_report("daily", as_of_date=date(2026, 6, 5))
    assert report["report_type"] == "daily"
    assert "sections" in report
    assert "batch" in report["sections"]


def test_recommendation_dashboard_today_counts(db_session):
    svc = PilotCommandCenterService(db_session)
    result = svc.get_recommendation_dashboard(as_of_date=date(2026, 6, 5))
    today = result["today"]
    assert "buy_count" in today
    assert "watch_count" in today
    assert "exit_count" in today
    assert today["buy_count"] == today["actions"].get("BUY", 0)
    assert today["watch_count"] == today["actions"].get("WATCH", 0)
    assert today["exit_count"] == today["actions"].get("EXIT_APPROVED", 0)


def test_list_recommendation_dates(client, db_session):
    response = client.get("/api/v1/recommendations/dates", params={"strategy_name": "momentum_v1"})
    assert response.status_code == 200
    body = response.json()
    assert "dates" in body
    assert isinstance(body["dates"], list)


def test_daily_includes_execution_context(client, db_session):
    latest = db_session.scalar(select(func.max(RecommendationRun.as_of_date)))
    if latest is None:
        return
    response = client.get(
        "/api/v1/recommendations/daily",
        params={"as_of_date": latest.isoformat(), "action": "WATCH"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["strategies"]
    block = next((s for s in body["strategies"] if s["strategy_name"] == "momentum_v1"), body["strategies"][0])
    assert "execution_context" in block
    if block["results"]:
        assert str(block["results"][0]["id"]) in block["execution_context"]


def test_daily_recommendations_falls_back_to_latest_run_day(client, db_session):
    from datetime import date as date_cls

    latest = db_session.scalar(select(func.max(RecommendationRun.as_of_date)))
    if latest is None or date_cls.today() <= latest:
        return

    response = client.get(
        "/api/v1/recommendations/daily",
        params={"as_of_date": date_cls.today().isoformat(), "action": "WATCH"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["as_of_date"] == latest.isoformat()
    assert body["watch_count"] > 0


def test_recommendation_dashboard_falls_back_to_latest_run_day(db_session):
    svc = PilotCommandCenterService(db_session)
    latest = db_session.scalar(select(func.max(RecommendationRun.as_of_date)))
    if latest is None:
        return

    result = svc.get_recommendation_dashboard()
    if date.today() > latest:
        assert result["as_of_date"] == latest.isoformat()
        assert result["today"]["runs"] > 0
        assert result["today"]["watch_count"] == result["today"]["actions"].get("WATCH", 0)
