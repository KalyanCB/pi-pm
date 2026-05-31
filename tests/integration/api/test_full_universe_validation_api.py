from datetime import date
from uuid import UUID, uuid4

from app.db.repositories.full_universe_validation_repository import (
    FullUniverseValidationRepository,
)
from app.validation.campaign_aggregator import compute_campaign_metrics
from tests.integration.api.test_validation_api import (
    _create_ranking_run,
    seed_forward_bars,
    seed_validation_universe,
)


def _seed_campaign_metrics(db_session, client):
    as_of = date(2024, 3, 15)
    stocks = seed_validation_universe(db_session, as_of)
    for stock in stocks:
        seed_forward_bars(db_session, stock, as_of, days=80)

    run_id = _create_ranking_run(client, as_of)
    client.post(f"/api/v1/validation/runs/{run_id}/compute")

    repo = FullUniverseValidationRepository(db_session)
    campaign = repo.create_campaign(
        universe_code="PI_PM_CORE",
        strategy_name="momentum_v1",
        strategy_version="1.0.0",
        start_date=as_of,
        end_date=as_of,
    )
    repo.mark_running(campaign)
    repo.create_validation_run(campaign.id, UUID(run_id), as_of)
    metrics = compute_campaign_metrics(db_session, [UUID(run_id)])
    repo.save_metrics(campaign.id, metrics)
    repo.save_deciles(campaign.id, metrics)
    repo.complete_campaign(campaign, validation_days_completed=1, validation_days_failed=0)
    db_session.commit()
    return campaign.id


def test_full_universe_summary_endpoint(client, db_session):
    campaign_id = _seed_campaign_metrics(db_session, client)

    response = client.get(
        "/api/v1/validation/full-universe/summary",
        params={"campaign_id": str(campaign_id), "horizon": 20},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["campaign_id"] == str(campaign_id)
    assert body["horizon"] == 20
    assert body["ic"] is not None
    assert body["rank_ic"] is not None
    assert body["spread"] is not None
    assert body["best_horizon"] is not None
    assert body["worst_horizon"] is not None
    assert "20" in body["horizons"]


def test_full_universe_deciles_endpoint(client, db_session):
    campaign_id = _seed_campaign_metrics(db_session, client)

    response = client.get(
        "/api/v1/validation/full-universe/deciles",
        params={"campaign_id": str(campaign_id), "horizon": 20},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["horizon"] == 20
    assert len(body["deciles"]) >= 1
    assert body["deciles"][0]["count"] >= 1
    assert body["deciles"][0]["avg_return"] is not None


def test_full_universe_run_invalid_date_range(client):
    response = client.post(
        "/api/v1/validation/full-universe/run",
        json={"start_date": "2025-05-31", "end_date": "2024-01-01"},
    )
    assert response.status_code == 422


def test_full_universe_summary_not_found(client):
    response = client.get(
        "/api/v1/validation/full-universe/summary",
        params={"campaign_id": str(uuid4())},
    )
    assert response.status_code == 404
