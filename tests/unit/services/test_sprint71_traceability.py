"""Sprint 7.1 traceability operationalization tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.core.constants import RankingRunStatus
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_factor_contribution_repository import (
    RankingFactorContributionRepository,
)
from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.db.repositories.validation_metrics_repository import ValidationMetricsRepository
from app.models.platform_traceability import (
    RankingFactorContribution,
    ValidationDecileMetric,
    ValidationHorizonMetric,
)
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.ranking.registry import RankingStrategyRegistry
from app.ranking.weight_hashing import hash_weight_config
from app.services.ranking_service import RankingService
from app.services.signal_validation_service import SignalValidationService
from app.services.universe_filter_service import UniverseFilterService
from app.validation.constants import VALIDATION_STATUS_COMPLETED


@pytest.fixture
def ranking_service(db_session, traceability_service) -> RankingService:
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
        traceability_service,
    )


@pytest.fixture
def validation_service(db_session, traceability_service) -> SignalValidationService:
    return SignalValidationService(
        db_session,
        Settings(),
        RankingRunRepository(db_session),
        RankingResultRepository(db_session),
        RankingPerformanceRepository(db_session),
        RankingValidationRepository(db_session),
        StockRepository(db_session),
        MarketDataRepository(db_session),
        traceability_service,
    )


def _completed_run(
    db_session, *, as_of: date | None = None, metadata: dict | None = None
) -> RankingRun:
    run = RankingRun(
        strategy_name="breakout_v1",
        strategy_version="1.0.0",
        as_of_date=as_of or date(2025, 5, 1),
        inputs_hash=f"hash-{uuid4()}",
        universe_code="NIFTY_500",
        benchmark_symbol="^NSEI",
        filter_config_hash="filter123",
        normalization_method="percentile",
        status=RankingRunStatus.COMPLETED.value,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        metadata_=metadata,
    )
    db_session.add(run)
    db_session.flush()
    return run


def _add_result(db_session, run: RankingRun, stock_id=None) -> RankingResult:
    stock_id = stock_id or uuid4()
    row = RankingResult(
        ranking_run_id=run.id,
        stock_id=stock_id,
        rank=1,
        score=Decimal("0.75"),
        score_components={
            "breakout": {"raw": "1.2", "normalized": "0.8", "weighted": "0.48"},
            "volume_surge": {"raw": "2.0", "normalized": "0.9", "weighted": "0.27"},
        },
        created_at=datetime.now(UTC),
    )
    db_session.add(row)
    db_session.flush()
    return row


def _completed_report(db_session, run: RankingRun) -> RankingValidationReport:
    report = RankingValidationReport(
        ranking_run_id=run.id,
        status=VALIDATION_STATUS_COMPLETED,
        regime_label="BULL_LOW_VOL",
        trend_regime="BULL",
        vol_regime="LOW_VOL",
        horizon_metrics={
            "20": {
                "status": "ok",
                "ic_spearman": "0.05",
                "top_minus_bottom_spread": "0.02",
                "sample_size": 100,
                "deciles": [
                    {
                        "decile": 1,
                        "count": 10,
                        "mean_return": "0.03",
                        "median_return": "0.02",
                    }
                ],
                "hit_rates": {"top_vs_median_hit_rate": "0.55"},
            }
        },
        sample_summary={"ranked_stock_count": 100},
        computed_at=datetime.now(UTC),
    )
    db_session.add(report)
    db_session.flush()
    return report


def test_ensure_ranking_traceability_from_score_components(db_session, traceability_service):
    metadata = {
        "ranked_stock_count": 1,
        "universe_stock_count": 5,
        "effective_weights": {"breakout": "0.6", "volume_surge": "0.4"},
    }
    run = _completed_run(db_session, metadata=metadata)
    _add_result(db_session, run)

    assert traceability_service.ensure_ranking_traceability(run) is True

    db_session.refresh(run)
    assert run.weight_config_hash == hash_weight_config(metadata["effective_weights"])
    assert run.ranked_stock_count == 1
    assert run.excluded_stock_count == 4
    assert RankingFactorContributionRepository(db_session).has_for_run(run.id)


def test_ensure_ranking_traceability_is_idempotent(db_session, traceability_service):
    run = _completed_run(
        db_session,
        metadata={
            "ranked_stock_count": 1,
            "universe_stock_count": 1,
            "effective_weights": {"breakout": "1.0"},
        },
    )
    _add_result(db_session, run)

    assert traceability_service.ensure_ranking_traceability(run) is True
    first_count = db_session.scalar(
        select(func.count())
        .select_from(RankingFactorContribution)
        .where(RankingFactorContribution.ranking_run_id == run.id)
    )
    assert traceability_service.ensure_ranking_traceability(run) is False
    second_count = db_session.scalar(
        select(func.count())
        .select_from(RankingFactorContribution)
        .where(RankingFactorContribution.ranking_run_id == run.id)
    )
    assert first_count == second_count


def test_ensure_validation_traceability_from_horizon_metrics(db_session, traceability_service):
    run = _completed_run(db_session)
    report = _completed_report(db_session, run)

    assert traceability_service.ensure_validation_traceability(report, run) is True
    assert ValidationMetricsRepository(db_session).has_for_report(report.id)

    horizon_rows = db_session.scalars(
        select(ValidationHorizonMetric).where(
            ValidationHorizonMetric.validation_report_id == report.id
        )
    ).all()
    decile_rows = db_session.scalars(
        select(ValidationDecileMetric).where(
            ValidationDecileMetric.validation_report_id == report.id
        )
    ).all()
    assert len(horizon_rows) == 1
    assert len(decile_rows) == 1


def test_ensure_validation_traceability_is_idempotent(db_session, traceability_service):
    run = _completed_run(db_session)
    report = _completed_report(db_session, run)

    assert traceability_service.ensure_validation_traceability(report, run) is True
    assert traceability_service.ensure_validation_traceability(report, run) is False


def test_ranking_reuse_path_invokes_ensure(ranking_service, db_session, monkeypatch):
    universe = ranking_service.universe_repo.get_by_code("NIFTY_500")
    if universe is None:
        from app.models.stock_universe import StockUniverse

        db_session.add(StockUniverse(code="NIFTY_500", name="NIFTY 500", description="test"))
        db_session.commit()

    run = _completed_run(
        db_session,
        as_of=date(2025, 6, 1),
        metadata={"ranked_stock_count": 1, "effective_weights": {"breakout": "1.0"}},
    )
    _add_result(db_session, run)
    db_session.commit()

    ensure_mock = MagicMock(return_value=False)
    monkeypatch.setattr(
        ranking_service.traceability_service, "ensure_ranking_traceability", ensure_mock
    )
    monkeypatch.setattr(ranking_service, "_resolve_regime_label", lambda *args, **kwargs: None)

    from app.ranking.models import RankingOutput
    from app.universe.models import TradableUniverse, UniverseFilterConfig

    fake_output = RankingOutput(
        strategy_name="breakout_v1",
        strategy_version="1.0.0",
        as_of_date=date(2025, 6, 1),
        universe_code="NIFTY_500",
        benchmark_symbol="^NSEI",
        normalization_method="percentile",
        inputs_hash=run.inputs_hash,
        filter_config_hash="filter123",
        ranked_stocks=(),
        ranking_exclusions=(),
        exclusion_summary={},
        metadata={"ranked_stock_count": 1},
    )

    filter_config = UniverseFilterConfig(universe_code="NIFTY_500")

    with (
        patch.object(
            ranking_service.ranking_run_repo,
            "find_completed_by_inputs_hash",
            return_value=run,
        ),
        patch.object(
            ranking_service.universe_filter_service,
            "build_tradable_universe",
            return_value=TradableUniverse(
                universe_code="NIFTY_500",
                as_of_date=date(2025, 6, 1),
                filter_config=filter_config,
                filter_config_hash="filter123",
                included=(),
                excluded=(),
                exclusion_summary={},
            ),
        ),
        patch.object(
            ranking_service.strategy_registry,
            "get",
            return_value=MagicMock(name="breakout_v1", version="1.0.0"),
        ),
        patch("app.services.ranking_service.RankingEngine") as engine_cls,
    ):
        engine_cls.return_value.run.return_value = fake_output

        from app.schemas.ranking import RankingRunRequest

        outcome = ranking_service.run_ranking_with_outcome(
            RankingRunRequest(
                universe_code="NIFTY_500",
                as_of_date=date(2025, 6, 1),
                strategy_name="breakout_v1",
                strategy_version="1.0.0",
            )
        )

    assert outcome.reused is True
    ensure_mock.assert_called_once_with(run)


def test_validation_reuse_path_invokes_ensure(validation_service, db_session, monkeypatch):
    run = _completed_run(db_session, as_of=date(2025, 6, 2))
    validation_repo = validation_service.validation_repo
    report = validation_repo.create_pending(run.id)
    validation_repo.complete(
        report,
        validation_hash="abc123",
        regime_label="BULL_LOW_VOL",
        trend_regime="BULL",
        vol_regime="LOW_VOL",
        status=VALIDATION_STATUS_COMPLETED,
        horizon_metrics={"20": {"status": "ok", "sample_size": 1, "deciles": []}},
        sample_summary={"ranked_stock_count": 1},
    )
    db_session.commit()

    ensure_mock = MagicMock(return_value=False)
    monkeypatch.setattr(
        validation_service.traceability_service,
        "ensure_validation_traceability",
        ensure_mock,
    )

    result = validation_service.validate_run(run.id, force_recompute=False)

    assert result.status == VALIDATION_STATUS_COMPLETED
    ensure_mock.assert_called_once()


def test_backfill_ranking_from_script(db_session):
    run = _completed_run(
        db_session,
        metadata={"ranked_stock_count": 1, "effective_weights": {"breakout": "1.0"}},
    )
    _add_result(db_session, run)
    db_session.commit()

    from scripts.backfill_sprint7_traceability import _build_traceability_service, backfill_ranking

    service = _build_traceability_service(db_session)
    stats = backfill_ranking(db_session, service, limit=None, dry_run=True)
    assert stats.ranking_runs_processed >= 1

    stats = backfill_ranking(db_session, service, limit=None, dry_run=False)
    assert stats.ranking_runs_updated >= 1
    db_session.refresh(run)
    assert run.weight_config_hash is not None


def test_backfill_validation_from_script(db_session):
    run = _completed_run(db_session)
    report = _completed_report(db_session, run)
    db_session.commit()

    from scripts.backfill_sprint7_traceability import (
        _build_traceability_service,
        backfill_validation,
    )

    service = _build_traceability_service(db_session)
    stats = backfill_validation(db_session, service, limit=None, dry_run=True)
    assert stats.validation_reports_processed >= 1

    stats = backfill_validation(db_session, service, limit=None, dry_run=False)
    assert stats.validation_reports_updated >= 1
    assert ValidationMetricsRepository(db_session).has_for_report(report.id)
