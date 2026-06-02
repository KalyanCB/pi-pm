from datetime import UTC, date, datetime

from app.args.builders.investment_review_packet_builder import InvestmentReviewPacketBuilder
from app.core.constants import DataStatus, RankingRunStatus
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.models.stock import Stock
from app.validation.constants import VALIDATION_STATUS_COMPLETED
from app.workspace_args.packet_schema import compute_packet_hash


def _seed(db_session):
    stock = Stock(
        symbol="PKT.NS",
        name="Packet Test",
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
        inputs_hash="pkt-hash",
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
    result = RankingResult(
        ranking_run_id=run.id,
        stock_id=stock.id,
        rank=1,
        score=0.91,
        score_components={"momentum": {"raw": 1.0, "normalized": 0.8, "weight": 0.3, "weighted": 0.24}},
        created_at=datetime.now(UTC),
    )
    db_session.add(result)
    db_session.add(
        RankingValidationReport(
            ranking_run_id=run.id,
            status=VALIDATION_STATUS_COMPLETED,
            regime_label="BULL_LOW_VOL",
            computed_at=datetime.now(UTC),
        )
    )
    db_session.commit()
    return run, result, stock


def test_packet_builder_reproducible_hash(db_session):
    from app.db.repositories.ranking_validation_repository import RankingValidationRepository

    run, result, stock = _seed(db_session)
    builder = InvestmentReviewPacketBuilder(
        db_session, RankingValidationRepository(db_session)
    )
    p1 = builder.build(ranking_run=run, result=result, stock=stock)
    p2 = builder.build(ranking_run=run, result=result, stock=stock)
    assert p1.packet_hash == p2.packet_hash
    assert p1.payload["ranking"]["ranking_result_id"] == str(result.id)
    assert "quant_evidence" in p1.payload
    assert "historical_performance" in p1.payload
    assert compute_packet_hash(p1.payload) == p1.packet_hash
    assert "packet_built_at" in p1.payload
