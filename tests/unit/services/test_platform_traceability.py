"""Unit tests for Sprint 7 platform traceability."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.core.constants import IngestPeriod, IngestionMode
from app.db.repositories.ingestion_batch_repository import IngestionBatchRepository
from app.db.repositories.ranking_factor_contribution_repository import (
    RankingFactorContributionRepository,
)
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.providers.yahoo.models import YahooOHLCVBar, YahooStockMetadata
from app.ranking.weight_hashing import hash_weight_config


@pytest.fixture
def metadata_reliance() -> YahooStockMetadata:
    return YahooStockMetadata(
        symbol="RELIANCE.NS",
        name="Reliance Industries Ltd",
        exchange="NSE",
        sector="Energy",
        industry="Oil & Gas",
    )


def test_hash_weight_config_is_stable():
    weights = {"momentum": Decimal("0.4"), "volume": Decimal("0.6")}
    assert hash_weight_config(weights) == hash_weight_config(weights)


def test_ingestion_batch_tracking(market_data_service, db_session, metadata_reliance):
    bars = [
        YahooOHLCVBar(
            date=date(2025, 5, 1),
            open=Decimal("100"),
            high=Decimal("105"),
            low=Decimal("99"),
            close=Decimal("102"),
            volume=1000,
            adj_close=Decimal("102"),
        )
    ]
    with patch.object(
        market_data_service.provider,
        "fetch_metadata",
        return_value=metadata_reliance,
    ), patch.object(
        market_data_service.provider,
        "fetch_history",
        return_value=bars,
    ):
        result = market_data_service.ingest(
            ["RELIANCE.NS"],
            IngestPeriod.ONE_YEAR,
            ingestion_mode=IngestionMode.FULL_REFRESH,
        )

    assert result.batch_id is not None
    assert result.execution_duration_ms is not None
    batch = IngestionBatchRepository(db_session).get_by_id(result.batch_id)
    assert batch is not None
    assert batch.symbol_count_requested == 1
    assert batch.symbol_count_succeeded == 1
    assert result.runs[0].first_date_loaded == date(2025, 5, 1)
    assert result.runs[0].last_date_loaded == date(2025, 5, 1)


def test_factor_contributions_sync(db_session, traceability_service):
    run = RankingRun(
        strategy_name="breakout_v1",
        strategy_version="1.0.0",
        as_of_date=date(2025, 5, 1),
        universe_code="NIFTY_500",
        benchmark_symbol="^NSEI",
        filter_config_hash="abc",
        normalization_method="percentile",
        status="completed",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()

    stock_id = __import__("uuid").uuid4()
    db_session.add(
        RankingResult(
            ranking_run_id=run.id,
            stock_id=stock_id,
            rank=1,
            score=Decimal("0.75"),
            score_components={
                "breakout": {"raw": 1.2, "normalized": 0.8, "weighted": 0.48},
                "volume_surge": {"raw": 2.0, "normalized": 0.9, "weighted": 0.27},
            },
            created_at=datetime.now(UTC),
        )
    )
    db_session.flush()

    rows = traceability_service.record_ranking_traceability(
        run,
        weight_config_hash="weight123",
        regime_label="BULL_LOW_VOL",
        ranked_stock_count=1,
        excluded_stock_count=0,
        execution_duration_ms=100,
    )
    assert rows == 2

    repo = RankingFactorContributionRepository(db_session)
    saved = repo.list_by_run(run.id)
    assert len(saved) == 2

    reconstruction = traceability_service.reconstruct_score(run.id, stock_id)
    assert reconstruction["reconstructed_score"] == pytest.approx(0.75)
