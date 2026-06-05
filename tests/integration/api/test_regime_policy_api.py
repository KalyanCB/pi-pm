from datetime import date

from tests.integration.api.test_validation_api import seed_forward_bars, seed_validation_universe


def _seed_breakout_validation(client, db_session, as_of: date) -> str:
    stocks = seed_validation_universe(db_session, as_of)
    for stock in stocks:
        seed_forward_bars(db_session, stock, as_of, days=80)
        # breakout_v1 requires 252+ trading days of history
        from datetime import UTC, datetime, timedelta

        from app.models.market_data import MarketData

        for i in range(40):
            bar_date = as_of - timedelta(days=221 + i)
            close = 150 + i
            db_session.add(
                MarketData(
                    stock_id=stock.id,
                    date=bar_date,
                    close=close,
                    adj_close=close,
                    volume=1_000_000,
                    source="yahoo",
                    ingested_at=datetime.now(UTC),
                )
            )
    db_session.commit()
    response = client.post(
        "/api/v1/rankings/run",
        json={
            "universe_code": "PI_PM_CORE",
            "as_of_date": as_of.isoformat(),
            "strategy_name": "breakout_v1",
            "strategy_version": "1.0.0",
            "benchmark_symbol": "^NSEI",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_load_presets_endpoint(client):
    response = client.post("/api/v1/regime-policy/configs/presets/load", json={"dry_run": False})
    assert response.status_code == 200
    body = response.json()
    assert body["loaded_count"] == 4
    assert len(body["config_ids"]) == 4


def test_list_configs_after_presets(client):
    client.post("/api/v1/regime-policy/configs/presets/load", json={"dry_run": False})
    response = client.get(
        "/api/v1/regime-policy/configs",
        params={"strategy_name": "breakout_v1"},
    )
    assert response.status_code == 200
    configs = response.json()
    assert len(configs) >= 4
    policy_types = {item["policy_type"] for item in configs}
    assert "BASELINE_E1" in policy_types
    assert "HARD_GATE_E2" in policy_types


def test_evaluate_policy_dry_run(client, db_session):
    client.post("/api/v1/regime-policy/configs/presets/load", json={"dry_run": False})
    configs = client.get("/api/v1/regime-policy/configs").json()
    e2 = next(c for c in configs if c["policy_type"] == "HARD_GATE_E2")

    as_of = date(2024, 6, 3)
    run_id = _seed_breakout_validation(client, db_session, as_of)
    client.post(f"/api/v1/validation/runs/{run_id}/compute")

    response = client.post(
        "/api/v1/regime-policy/evaluate",
        json={
            "ranking_run_id": run_id,
            "policy_config_id": e2["id"],
            "persist": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action"] in {"ALLOW", "BLOCK", "REDUCE"}
    assert "regime_label" in body

    decisions = client.get(
        "/api/v1/regime-policy/decisions",
        params={"ranking_run_id": run_id},
    )
    assert decisions.status_code == 200
    assert len(decisions.json()) >= 1


def test_backtest_run_endpoint(client, db_session):
    client.post("/api/v1/regime-policy/configs/presets/load", json={"dry_run": False})
    configs = client.get("/api/v1/regime-policy/configs").json()
    by_type = {c["policy_type"]: c for c in configs}
    policy_ids = [
        by_type[t]["id"]
        for t in ("BASELINE_E1", "HARD_GATE_E2", "SOFT_GATE_E3", "THRESHOLD_GATE_E4")
    ]

    as_of_dates = (date(2024, 6, 3), date(2024, 9, 10), date(2025, 3, 5))
    stocks = seed_validation_universe(db_session, as_of_dates[0])
    for as_of in as_of_dates:
        for stock in stocks:
            seed_forward_bars(db_session, stock, as_of, days=80)
        response = client.post(
            "/api/v1/rankings/run",
            json={
                "universe_code": "PI_PM_CORE",
                "as_of_date": as_of.isoformat(),
                "strategy_name": "breakout_v1",
                "strategy_version": "1.0.0",
                "benchmark_symbol": "^NSEI",
            },
        )
        assert response.status_code == 201
        client.post(f"/api/v1/validation/runs/{response.json()['id']}/compute")

    response = client.post(
        "/api/v1/regime-policy/backtest/run",
        json={
            "strategy_name": "breakout_v1",
            "strategy_version": "1.0.0",
            "universe_code": "PI_PM_CORE",
            "horizon": 20,
            "start_date": "2024-01-01",
            "end_date": "2025-12-31",
            "holdout_start_date": "2025-01-01",
            "policy_config_ids": policy_ids,
            "baseline_policy_config_id": by_type["BASELINE_E1"]["id"],
            "experiment_name": "test_sprint81_backtest",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["experiment_run_id"]
    assert len(body["backtest_run_ids"]) == 4
    assert "BASELINE_E1" in body["summary"]
    assert "research_findings" in body["summary"]["HARD_GATE_E2"]

    runs = client.get(
        "/api/v1/regime-policy/backtest/runs",
        params={"experiment_run_id": body["experiment_run_id"]},
    )
    assert runs.status_code == 200
    assert len(runs.json()) == 4
    for run in runs.json():
        assert run["holdout_metrics"]
        assert (
            run["research_findings"] is not None
            or run["policy_config_id"] == by_type["BASELINE_E1"]["id"]
        )
