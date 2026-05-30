from datetime import UTC, date, datetime

import pytest

from app.core.config import Settings
from app.core.constants import RankingRunStatus
from app.core.exceptions import RankingError
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.models.ranking_run import RankingRun
from app.ranking.registry import RankingStrategyRegistry
from app.schemas.ranking import RankingRunRequest
from app.services.ranking_service import RankingService
from app.services.universe_filter_service import UniverseFilterService
from tests.integration.api.test_rankings_api import seed_ranking_universe


@pytest.fixture
def ranking_service(db_session) -> RankingService:
    market_data_repo = MarketDataRepository(db_session)
    return RankingService(
        db_session,
        Settings(),
        UniverseFilterService(UniverseRepository(db_session), market_data_repo),
        RankingRunRepository(db_session),
        RankingResultRepository(db_session),
        RankingPerformanceRepository(db_session),
        StockRepository(db_session),
        UniverseRepository(db_session),
        RankingStrategyRegistry(),
    )


def test_find_completed_by_inputs_hash_ignores_failed_runs(db_session):
    repo = RankingRunRepository(db_session)
    completed = RankingRun(
        strategy_name="momentum_v1",
        strategy_version="1.0.0",
        as_of_date=date(2025, 6, 1),
        inputs_hash="abc123",
        universe_code="PI_PM_CORE",
        benchmark_symbol="^NSEI",
        filter_config_hash="filter123",
        normalization_method="percentile",
        status=RankingRunStatus.COMPLETED.value,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    failed = RankingRun(
        strategy_name="momentum_v1",
        strategy_version="1.0.0",
        as_of_date=date(2025, 6, 1),
        inputs_hash=None,
        universe_code="PI_PM_CORE",
        benchmark_symbol="^NSEI",
        filter_config_hash="filter123",
        normalization_method="percentile",
        status=RankingRunStatus.FAILED.value,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        error_message="persist failed",
    )
    db_session.add_all([completed, failed])
    db_session.commit()

    found = repo.find_completed_by_inputs_hash("abc123")
    assert found is not None
    assert found.status == RankingRunStatus.COMPLETED.value


def test_failed_run_persists_null_inputs_hash(ranking_service, db_session, monkeypatch):
    as_of = date(2025, 6, 1)
    seed_ranking_universe(db_session, as_of)

    def _raise(*_args, **_kwargs):
        raise RuntimeError("persist failed")

    monkeypatch.setattr(ranking_service.ranking_result_repo, "save_results", _raise)

    with pytest.raises(RankingError):
        ranking_service.run_ranking(
            RankingRunRequest(
                universe_code="PI_PM_CORE",
                as_of_date=as_of,
                strategy_name="momentum_v1",
                strategy_version="1.0.0",
            )
        )

    failed = (
        db_session.query(RankingRun)
        .filter(RankingRun.status == RankingRunStatus.FAILED.value)
        .one()
    )
    assert failed.inputs_hash is None
    assert failed.error_message == "persist failed"


def test_failed_run_does_not_block_recompute(ranking_service, db_session, monkeypatch):
    as_of = date(2025, 6, 1)
    seed_ranking_universe(db_session, as_of)

    calls = {"count": 0}
    original_save = ranking_service.ranking_result_repo.save_results

    def _fail_once(run_id, ranked_stocks):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("first attempt failed")
        return original_save(run_id, ranked_stocks)

    monkeypatch.setattr(ranking_service.ranking_result_repo, "save_results", _fail_once)

    with pytest.raises(RankingError):
        ranking_service.run_ranking(
            RankingRunRequest(
                universe_code="PI_PM_CORE",
                as_of_date=as_of,
                strategy_name="momentum_v1",
                strategy_version="1.0.0",
            )
        )

    success = ranking_service.run_ranking(
        RankingRunRequest(
            universe_code="PI_PM_CORE",
            as_of_date=as_of,
            strategy_name="momentum_v1",
            strategy_version="1.0.0",
        )
    )
    assert success.status == RankingRunStatus.COMPLETED.value
    assert success.inputs_hash is not None


def test_idempotent_reuse_returns_completed_run(ranking_service, db_session):
    as_of = date(2025, 6, 1)
    seed_ranking_universe(db_session, as_of)

    first = ranking_service.run_ranking(
        RankingRunRequest(
            universe_code="PI_PM_CORE",
            as_of_date=as_of,
            strategy_name="momentum_v1",
            strategy_version="1.0.0",
        )
    )
    second = ranking_service.run_ranking(
        RankingRunRequest(
            universe_code="PI_PM_CORE",
            as_of_date=as_of,
            strategy_name="momentum_v1",
            strategy_version="1.0.0",
        )
    )
    assert second.id == first.id
    assert second.inputs_hash == first.inputs_hash


def test_api_defaults_from_settings(ranking_service, db_session):
    as_of = date(2025, 6, 1)
    seed_ranking_universe(db_session, as_of)

    run = ranking_service.run_ranking(RankingRunRequest(as_of_date=as_of))
    assert run.universe_code == "PI_PM_CORE"
    assert run.strategy_name == "momentum_v1"
    assert run.strategy_version == "1.0.0"
