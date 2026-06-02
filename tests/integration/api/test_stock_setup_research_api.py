from datetime import date

from tests.integration.api.test_rankings_api import seed_benchmark, seed_ranking_universe


def test_stock_setup_research_generate_and_list(client, db_session):
    as_of = date(2025, 6, 1)
    seed_ranking_universe(db_session, as_of)
    seed_benchmark(db_session, as_of)

    ranking = client.post(
        "/api/v1/rankings/run",
        json={
            "universe_code": "PI_PM_CORE",
            "as_of_date": as_of.isoformat(),
            "strategy_name": "momentum_v1",
            "strategy_version": "1.0.0",
            "benchmark_symbol": "^NSEI",
        },
    )
    assert ranking.status_code == 201, ranking.text
    run_id = ranking.json()["id"]

    generate = client.post(f"/api/v1/research/stock-setup/runs/{run_id}/generate?limit=2")
    assert generate.status_code == 200, generate.text
    body = generate.json()
    assert body["candidates"] == 2
    assert body["completed"] >= 1

    listed = client.get(f"/api/v1/research/stock-setup/runs/{run_id}")
    assert listed.status_code == 200
    rows = listed.json()["rows"]
    assert len(rows) == 2
    assert all("status" in row for row in rows)
