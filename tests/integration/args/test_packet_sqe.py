"""Integration tests: built packets include stock_quality_evidence."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.args.builders.investment_review_packet_builder import InvestmentReviewPacketBuilder
from app.core.constants import DataStatus, RankingRunStatus
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.models.stock import Stock
from app.validation.constants import VALIDATION_STATUS_INSUFFICIENT_DATA
from app.workspace_args.packet_schema import compute_packet_hash


def _seed(db_session):
    stock = Stock(
        symbol="SQE.NS",
        name="SQE Packet Test",
        exchange="NSE",
        data_status=DataStatus.ACTIVE.value,
        is_active=True,
    )
    db_session.add(stock)
    db_session.flush()
    as_of = date(2026, 6, 2)
    run = RankingRun(
        strategy_name="breakout_v1",
        strategy_version="1.0.0",
        as_of_date=as_of,
        inputs_hash="sqe-hash",
        universe_code="NIFTY_500",
        benchmark_symbol="^NSEI",
        filter_config_hash="fc",
        normalization_method="percentile",
        status=RankingRunStatus.COMPLETED.value,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        regime_label="BEAR_LOW_VOL",
    )
    db_session.add(run)
    db_session.flush()
    result = RankingResult(
        ranking_run_id=run.id,
        stock_id=stock.id,
        rank=1,
        score=0.88,
        score_components={
            "volatility_adjusted_momentum": {
                "raw": 1.0,
                "normalized": 0.95,
                "weight": 0.2,
                "weighted": 0.19,
            },
            "high_proximity": {
                "raw": 0.9,
                "normalized": 0.9,
                "weight": 0.15,
                "weighted": 0.135,
            },
        },
        created_at=datetime.now(UTC),
    )
    db_session.add(result)
    db_session.add(
        RankingValidationReport(
            ranking_run_id=run.id,
            status=VALIDATION_STATUS_INSUFFICIENT_DATA,
            regime_label="BEAR_LOW_VOL",
            computed_at=datetime.now(UTC),
        )
    )
    db_session.commit()
    return run, result, stock


def test_built_packet_contains_stock_quality_evidence(db_session):
    from app.db.repositories.ranking_validation_repository import RankingValidationRepository

    run, result, stock = _seed(db_session)
    builder = InvestmentReviewPacketBuilder(
        db_session, RankingValidationRepository(db_session)
    )
    packet = builder.build(ranking_run=run, result=result, stock=stock)
    payload = packet.payload

    assert "stock_quality_evidence" in payload
    sqe = payload["stock_quality_evidence"]
    for section in (
        "A_ranking_attribution",
        "B_factor_attribution",
        "C_regime_alignment",
        "D_historical_analog",
        "E_exit_profile",
        "F_validation_context",
    ):
        assert section in sqe

    lineage = payload.get("source_lineage") or {}
    assert lineage.get("stock_quality_evidence_schema_version") == "1.0.0"
    assert compute_packet_hash(payload) == packet.packet_hash
