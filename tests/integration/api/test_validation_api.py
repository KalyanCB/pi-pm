from datetime import UTC, date, datetime, timedelta

from app.core.constants import DataStatus
from app.models.market_data import MarketData
from app.models.stock import Stock
from tests.integration.api.test_rankings_api import seed_benchmark


def seed_forward_bars(db_session, stock: Stock, after: date, days: int = 80):
    for i in range(1, days + 1):
        bar_date = after + timedelta(days=i)
        close = 200 + i
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


def seed_validation_universe(db_session, as_of: date):
    from app.models.stock_universe import StockUniverse
    from app.models.universe_membership import UniverseMembership

    universe = StockUniverse(code="PI_PM_CORE", name="Core", is_active=True)
    db_session.add(universe)
    db_session.flush()

    symbols = ["AAA.NS", "BBB.NS", "CCC.NS", "DDD.NS", "EEE.NS", "FFF.NS"]
    stocks = []
    for idx, symbol in enumerate(symbols):
        stock = Stock(
            symbol=symbol,
            name=symbol,
            exchange="NSE",
            data_status=DataStatus.ACTIVE.value,
            is_active=True,
        )
        db_session.add(stock)
        db_session.flush()
        db_session.add(
            UniverseMembership(universe_id=universe.id, stock_id=stock.id, removed_at=None)
        )
        for i in range(220):
            bar_date = as_of - timedelta(days=219 - i)
            close = 100 + idx * 10 + (i * 2)
            db_session.add(
                MarketData(
                    stock_id=stock.id,
                    date=bar_date,
                    close=close,
                    adj_close=close,
                    volume=1_000_000 + i * 1000,
                    source="yahoo",
                    ingested_at=datetime.now(UTC),
                )
            )
        stocks.append(stock)
    seed_benchmark(db_session, as_of)
    db_session.commit()
    return stocks


def test_ranking_to_validation_flow(client, db_session):
    as_of = date(2025, 6, 1)
    stocks = seed_validation_universe(db_session, as_of)
    for stock in stocks:
        seed_forward_bars(db_session, stock, as_of, days=80)

    run_resp = client.post(
        "/api/v1/rankings/run",
        json={
            "universe_code": "PI_PM_CORE",
            "as_of_date": as_of.isoformat(),
            "strategy_name": "momentum_v1",
            "strategy_version": "1.0.0",
            "benchmark_symbol": "^NSEI",
        },
    )
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    val_resp = client.post(f"/api/v1/validation/runs/{run_id}/compute")
    assert val_resp.status_code == 201
    body = val_resp.json()
    assert body["status"] == "completed"
    assert body["regime_label"] is not None
    assert "20" in (body.get("horizon_metrics") or {})

    rerun = client.post(f"/api/v1/validation/runs/{run_id}/compute")
    assert rerun.status_code == 201
    assert rerun.json()["validation_hash"] == body.get("validation_hash")

    snaps = client.get(f"/api/v1/validation/runs/{run_id}/snapshots")
    assert snaps.status_code == 200
    assert len(snaps.json()) == 6


def test_validation_summary_endpoint(client, db_session):
    as_of = date(2025, 6, 1)
    stocks = seed_validation_universe(db_session, as_of)
    for stock in stocks:
        seed_forward_bars(db_session, stock, as_of)

    run_resp = client.post(
        "/api/v1/rankings/run",
        json={"universe_code": "PI_PM_CORE", "as_of_date": as_of.isoformat()},
    )
    run_id = run_resp.json()["id"]
    client.post(f"/api/v1/validation/runs/{run_id}/compute")

    summary = client.get(
        "/api/v1/validation/summary",
        params={
            "universe_code": "PI_PM_CORE",
            "start_date": as_of.isoformat(),
            "end_date": as_of.isoformat(),
            "horizon": 20,
        },
    )
    assert summary.status_code == 200
    data = summary.json()
    assert data["reports_count"] >= 1
    assert data["validated_runs"] >= 1
    assert data["average_ic_20d"] is not None
    assert data["median_ic_20d"] is not None
    assert data["hit_rate_20d"] is not None
    assert data["spread_20d"] is not None
    assert data["best_regime"] is not None
    assert data["worst_regime"] is not None


def test_empty_universe_validation(client, db_session):
    as_of = date(2025, 6, 1)
    from app.models.stock_universe import StockUniverse

    db_session.add(StockUniverse(code="PI_PM_CORE", name="Core", is_active=True))
    db_session.commit()

    run_resp = client.post(
        "/api/v1/rankings/run",
        json={"universe_code": "PI_PM_CORE", "as_of_date": as_of.isoformat()},
    )
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    val_resp = client.post(f"/api/v1/validation/runs/{run_id}/compute")
    assert val_resp.status_code == 201
    assert val_resp.json()["status"] == "insufficient_data"


def _create_ranking_run(client, as_of: date) -> str:
    response = client.post(
        "/api/v1/rankings/run",
        json={
            "universe_code": "PI_PM_CORE",
            "as_of_date": as_of.isoformat(),
            "strategy_name": "momentum_v1",
            "strategy_version": "1.0.0",
            "benchmark_symbol": "^NSEI",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_validation_backfill_endpoint(client, db_session):
    as_of = date(2024, 3, 15)
    stocks = seed_validation_universe(db_session, as_of)
    for stock in stocks:
        seed_forward_bars(db_session, stock, as_of, days=80)

    _create_ranking_run(client, as_of)

    first = client.post(
        "/api/v1/validation/backfill",
        json={
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "force_recompute": False,
        },
    )
    assert first.status_code == 200
    body = first.json()
    assert body["runs_found"] == 1
    assert body["validated"] == 1
    assert body["reused"] == 0
    assert body["failed"] == 0

    second = client.post(
        "/api/v1/validation/backfill",
        json={
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "force_recompute": False,
        },
    )
    assert second.status_code == 200
    reuse_body = second.json()
    assert reuse_body["runs_found"] == 1
    assert reuse_body["validated"] == 0
    assert reuse_body["reused"] == 1
    assert reuse_body["failed"] == 0


def test_validation_backfill_multiple_runs(client, db_session):
    as_of_dates = [date(2024, 1, 15), date(2024, 2, 1), date(2024, 3, 15)]
    latest_as_of = max(as_of_dates)
    stocks = seed_validation_universe(db_session, latest_as_of)
    for stock in stocks:
        seed_forward_bars(db_session, stock, latest_as_of, days=80)

    for as_of in as_of_dates:
        _create_ranking_run(client, as_of)

    response = client.post(
        "/api/v1/validation/backfill",
        json={
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "force_recompute": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["runs_found"] == 3
    assert body["validated"] + body["reused"] + body["failed"] == 3
    assert body["failed"] == 0


def test_validation_backfill_invalid_date_range(client):
    response = client.post(
        "/api/v1/validation/backfill",
        json={
            "start_date": "2024-03-31",
            "end_date": "2024-01-01",
            "force_recompute": False,
        },
    )
    assert response.status_code == 422


def test_validation_summary_filtered_and_backfill_flow(client, db_session):
    as_of_dates = [date(2024, 1, 15), date(2024, 2, 1), date(2024, 3, 15)]
    latest_as_of = max(as_of_dates)
    stocks = seed_validation_universe(db_session, latest_as_of)
    for stock in stocks:
        seed_forward_bars(db_session, stock, latest_as_of, days=80)

    for as_of in as_of_dates:
        _create_ranking_run(client, as_of)

    backfill = client.post(
        "/api/v1/validation/backfill",
        json={
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "force_recompute": False,
        },
    )
    assert backfill.status_code == 200
    assert backfill.json()["runs_found"] == 3

    summary = client.get(
        "/api/v1/validation/summary",
        params={
            "universe_code": "PI_PM_CORE",
            "strategy_name": "momentum_v1",
            "strategy_version": "1.0.0",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "horizon": 20,
        },
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["reports_count"] >= 1
    assert body["validated_runs"] >= 1
    assert body["average_ic_20d"] is not None
    assert body["median_ic_20d"] is not None
    assert body["hit_rate_20d"] is not None
    assert body["spread_20d"] is not None
    assert body["directional_hit_rate_20d"] is not None
    assert body["regime_ic"] is not None
    assert body["best_regime"] is not None
    assert body["worst_regime"] is not None

    second_backfill = client.post(
        "/api/v1/validation/backfill",
        json={
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "force_recompute": False,
        },
    )
    assert second_backfill.status_code == 200
    reuse = second_backfill.json()
    assert reuse["runs_found"] == 3
    assert reuse["validated"] == 0
    assert reuse["reused"] + reuse["failed"] + reuse["validated"] == 3
