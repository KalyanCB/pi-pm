from datetime import date

from tests.unit.factor_analytics.conftest import seed_factor_run


def _backfill(client, *, start: date, end: date):
    response = client.post(
        "/api/v1/analytics/factors/backfill",
        json={
            "universe_code": "PI_PM_CORE",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "holdout_start_date": "2025-01-01",
            "write_daily_metrics": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_performance_endpoint_filters(db_session, client):
    seed_factor_run(db_session, as_of=date(2024, 9, 3))
    _backfill(client, start=date(2024, 9, 1), end=date(2024, 9, 30))

    response = client.get(
        "/api/v1/analytics/factors/performance",
        params={
            "universe_code": "PI_PM_CORE",
            "factor_name": "volume_surge",
            "regime_label": "BULL_LOW_VOL",
            "horizon": 20,
            "dataset_split": "TRAIN",
        },
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) >= 1
    row = rows[0]
    assert row["factor_name"] == "volume_surge"
    assert row["stability_score"] is not None
    assert row["regime_coverage_pct"] is not None
    assert row["bootstrap_sample_count"] == 1000


def test_leaderboard_defaults_to_holdout(db_session, client):
    seed_factor_run(db_session, as_of=date(2025, 2, 3))
    _backfill(client, start=date(2025, 2, 1), end=date(2025, 2, 28))

    response = client.get(
        "/api/v1/analytics/factors/leaderboard",
        params={
            "regime_label": "BULL_LOW_VOL",
            "horizon": 20,
            "universe_code": "PI_PM_CORE",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dataset_split"] == "HOLDOUT"
    assert len(body["entries"]) >= 1
    assert "train_ic" in body["entries"][0]
    assert "holdout_ic" in body["entries"][0]


def test_train_holdout_drift_endpoint(db_session, client):
    seed_factor_run(db_session, as_of=date(2024, 11, 4))
    _backfill(client, start=date(2024, 11, 1), end=date(2024, 11, 30))

    response = client.get(
        "/api/v1/analytics/factors/train-holdout-drift",
        params={
            "universe_code": "PI_PM_CORE",
            "regime_label": "BULL_LOW_VOL",
            "horizon": 20,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["holdout_start_date"] == "2025-01-01"
    assert isinstance(body["factors"], list)


def test_compare_and_runs_endpoints(db_session, client):
    seed_factor_run(db_session, as_of=date(2024, 12, 2))
    backfill = _backfill(client, start=date(2024, 12, 1), end=date(2024, 12, 31))

    compare = client.get(
        "/api/v1/analytics/factors/compare",
        params={
            "factor_name": "volume_surge",
            "universe_code": "PI_PM_CORE",
        },
    )
    assert compare.status_code == 200
    compare_body = compare.json()
    assert compare_body["factor_name"] == "volume_surge"
    assert "ic_drift" in compare_body

    runs = client.get("/api/v1/analytics/factors/runs")
    assert runs.status_code == 200
    assert len(runs.json()) >= 1

    run_detail = client.get(f"/api/v1/analytics/factors/runs/{backfill['run_id']}")
    assert run_detail.status_code == 200
    assert run_detail.json()["status"] == "completed"
