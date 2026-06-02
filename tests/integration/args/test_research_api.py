from datetime import UTC, date, datetime

from app.core.constants import DataStatus, RankingRunStatus
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.models.stock import Stock
from app.validation.constants import VALIDATION_STATUS_COMPLETED


def _seed_ranking(db_session):
    stock = Stock(
        symbol="ARGS.NS",
        name="ARGS Test",
        exchange="NSE",
        data_status=DataStatus.ACTIVE.value,
        is_active=True,
    )
    db_session.add(stock)
    db_session.flush()
    as_of = date(2026, 6, 1)
    run = RankingRun(
        strategy_name="breakout_v1",
        strategy_version="1.0.0",
        as_of_date=as_of,
        inputs_hash="hash-args",
        universe_code="NIFTY_500",
        benchmark_symbol="^NSEI",
        filter_config_hash="fc",
        normalization_method="percentile",
        status=RankingRunStatus.COMPLETED.value,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()
    db_session.add(
        RankingResult(
            ranking_run_id=run.id,
            stock_id=stock.id,
            rank=1,
            score=0.91,
            score_components={"momentum": {"raw": "1", "normalized": "0.9"}},
            created_at=datetime.now(UTC),
        )
    )
    db_session.add(
        RankingValidationReport(
            ranking_run_id=run.id,
            status=VALIDATION_STATUS_COMPLETED,
            regime_label="BULL_LOW_VOL",
            computed_at=datetime.now(UTC),
        )
    )
    db_session.commit()
    return run, stock


def test_research_run_e2e(client, db_session):
    run, _stock = _seed_ranking(db_session)
    resp = client.post(
        "/api/v1/research/run",
        json={
            "ranking_run_id": str(run.id),
            "top_n": 1,
            "committee_codes": ["TARC", "QRC"],
            "require_completed_validation": True,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["candidates_reviewed"] == 1
    assert body["governance_reports_issued"] == 1

    run_id = body["run_id"]
    detail = client.get(f"/api/v1/research/{run_id}")
    assert detail.status_code == 200

    packets = client.get(f"/api/v1/research/{run_id}/packet")
    assert packets.status_code == 200
    assert len(packets.json()["packets"]) == 1
    packet_hash = packets.json()["packets"][0]["packet_hash"]
    assert len(packet_hash) == 64

    explain = client.get(f"/api/v1/research/{run_id}/explain")
    assert explain.status_code == 200
    assert explain.json()["packet_count"] == 1

    lineage = client.get(f"/api/v1/research/{run_id}/lineage")
    assert lineage.status_code == 200
    assert len(lineage.json()["edges"]) >= 1

    latest = client.get("/api/v1/research/latest?strategy_name=breakout_v1")
    assert latest.status_code == 200
