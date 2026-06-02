from datetime import UTC, date, datetime

from app.core.constants import (
    DataStatus,
    LineageEntityType,
    LineageRelationshipType,
    RankingRunStatus,
)
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.models.stock import Stock
from app.validation.constants import VALIDATION_STATUS_COMPLETED


def _seed_ranking(db_session):
    stock = Stock(
        symbol="LN.NS",
        name="Lineage",
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
        inputs_hash="ln-hash",
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
            score=0.88,
            score_components={},
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
    return run


def test_lineage_chain_includes_governance_and_ranking(client, db_session):
    run = _seed_ranking(db_session)
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
    run_id = resp.json()["run_id"]
    lineage = client.get(f"/api/v1/research/{run_id}/lineage").json()
    rel_types = {e["relationship_type"] for e in lineage["edges"]}
    entity_types = {e["child_entity_type"] for e in lineage["edges"]} | {
        e["parent_entity_type"] for e in lineage["edges"]
    }
    assert LineageRelationshipType.CRO_ISSUES_GOVERNANCE_REPORT.value in rel_types
    assert LineageRelationshipType.PACKET_SOURCES_RANKING_RESULT.value in rel_types
    assert LineageRelationshipType.COMMITTEE_REVIEW_AGGREGATED_TO_CRO.value in rel_types
    assert LineageEntityType.GOVERNANCE_RESEARCH_REPORT.value in entity_types
    assert LineageEntityType.RANKING_RESULT.value in entity_types
