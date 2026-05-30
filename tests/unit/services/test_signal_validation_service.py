from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.core.constants import RankingRunStatus
from app.core.exceptions import ValidationError
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.stock_repository import StockRepository
from app.models.ranking_run import RankingRun
from app.services.signal_validation_service import SignalValidationService
from app.validation.constants import VALIDATION_STATUS_COMPLETED, VALIDATION_STATUS_INSUFFICIENT_DATA


@pytest.fixture
def validation_service(db_session) -> SignalValidationService:
    return SignalValidationService(
        db_session,
        Settings(),
        RankingRunRepository(db_session),
        RankingResultRepository(db_session),
        RankingPerformanceRepository(db_session),
        RankingValidationRepository(db_session),
        StockRepository(db_session),
        MarketDataRepository(db_session),
    )


def _completed_run(db_session, as_of: date) -> RankingRun:
    run = RankingRun(
        strategy_name="momentum_v1",
        strategy_version="1.0.0",
        as_of_date=as_of,
        inputs_hash=f"hash-{as_of.isoformat()}",
        universe_code="PI_PM_CORE",
        benchmark_symbol="^NSEI",
        filter_config_hash="filter123",
        normalization_method="percentile",
        status=RankingRunStatus.COMPLETED.value,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()
    return run


def test_backfill_empty_range(validation_service: SignalValidationService) -> None:
    result = validation_service.backfill(date(2024, 1, 1), date(2024, 3, 31))
    assert result.runs_found == 0
    assert result.validated == 0
    assert result.reused == 0
    assert result.failed == 0


def test_backfill_invalid_date_range(validation_service: SignalValidationService) -> None:
    with pytest.raises(ValidationError, match="end_date must be on or after start_date"):
        validation_service.backfill(date(2024, 3, 31), date(2024, 1, 1))


def test_backfill_reuses_insufficient_data_report(
    validation_service: SignalValidationService, db_session
) -> None:
    run = _completed_run(db_session, date(2024, 2, 1))
    validation_repo = RankingValidationRepository(db_session)
    report = validation_repo.create_pending(run.id)
    validation_repo.complete(
        report,
        validation_hash=None,
        regime_label=None,
        trend_regime=None,
        vol_regime=None,
        status=VALIDATION_STATUS_INSUFFICIENT_DATA,
        horizon_metrics={},
        sample_summary={"reason": "test"},
    )
    db_session.commit()

    result = validation_service.backfill(date(2024, 1, 1), date(2024, 3, 31))
    assert result.runs_found == 1
    assert result.reused == 1
    assert result.validated == 0


def test_backfill_reuses_completed_validation(
    validation_service: SignalValidationService, db_session
) -> None:
    run = _completed_run(db_session, date(2024, 2, 15))
    validation_repo = RankingValidationRepository(db_session)
    report = validation_repo.create_pending(run.id)
    validation_repo.complete(
        report,
        validation_hash="abc123",
        regime_label="BULL_LOW_VOL",
        trend_regime="BULL",
        vol_regime="LOW_VOL",
        status=VALIDATION_STATUS_COMPLETED,
        horizon_metrics={"20": {"status": "ok"}},
        sample_summary={"ranked_stock_count": 3},
    )
    db_session.commit()

    result = validation_service.backfill(date(2024, 1, 1), date(2024, 3, 31))
    assert result.runs_found == 1
    assert result.reused == 1
    assert result.validated == 0
    assert result.failed == 0


def test_backfill_validates_runs_without_reports(
    validation_service: SignalValidationService, db_session, monkeypatch
) -> None:
    _completed_run(db_session, date(2024, 2, 1))
    _completed_run(db_session, date(2024, 2, 15))
    db_session.commit()

    calls: list = []

    def _validate(run_id, *, force_recompute=False):
        calls.append(run_id)
        return MagicMock()

    monkeypatch.setattr(validation_service, "validate_run", _validate)

    result = validation_service.backfill(date(2024, 1, 1), date(2024, 3, 31))
    assert result.runs_found == 2
    assert result.validated == 2
    assert result.reused == 0
    assert result.failed == 0
    assert len(calls) == 2


def test_backfill_idempotent_second_call_reuses_all(
    validation_service: SignalValidationService, db_session, monkeypatch
) -> None:
    _completed_run(db_session, date(2024, 2, 1))
    db_session.commit()

    monkeypatch.setattr(
        validation_service,
        "validate_run",
        lambda run_id, *, force_recompute=False: validation_service.validation_repo.complete(
            validation_service.validation_repo.create_pending(run_id),
            validation_hash="hash",
            regime_label=None,
            trend_regime=None,
            vol_regime=None,
            status=VALIDATION_STATUS_COMPLETED,
            horizon_metrics={},
            sample_summary={},
        ),
    )

    first = validation_service.backfill(date(2024, 1, 1), date(2024, 3, 31))
    assert first.validated == 1
    assert first.reused == 0

    second = validation_service.backfill(date(2024, 1, 1), date(2024, 3, 31))
    assert second.runs_found == 1
    assert second.validated == 0
    assert second.reused == 1
    assert second.failed == 0


def test_backfill_force_recompute_revalidates(
    validation_service: SignalValidationService, db_session, monkeypatch
) -> None:
    run = _completed_run(db_session, date(2024, 2, 1))
    validation_repo = RankingValidationRepository(db_session)
    report = validation_repo.create_pending(run.id)
    validation_repo.complete(
        report,
        validation_hash="abc123",
        regime_label="BULL_LOW_VOL",
        trend_regime="BULL",
        vol_regime="LOW_VOL",
        status=VALIDATION_STATUS_COMPLETED,
        horizon_metrics={"20": {"status": "ok"}},
        sample_summary={"ranked_stock_count": 3},
    )
    db_session.commit()

    calls: list = []

    def _validate(run_id, *, force_recompute=False):
        calls.append((run_id, force_recompute))
        return report

    monkeypatch.setattr(validation_service, "validate_run", _validate)

    result = validation_service.backfill(
        date(2024, 1, 1),
        date(2024, 3, 31),
        force_recompute=True,
    )
    assert result.runs_found == 1
    assert result.validated == 1
    assert result.reused == 0
    assert calls == [(run.id, True)]


def test_backfill_counts_failures(
    validation_service: SignalValidationService, db_session, monkeypatch
) -> None:
    _completed_run(db_session, date(2024, 2, 1))
    bad = _completed_run(db_session, date(2024, 2, 15))
    db_session.commit()

    def _validate(run_id, *, force_recompute=False):
        if run_id == bad.id:
            raise ValidationError("validation failed")
        return MagicMock()

    monkeypatch.setattr(validation_service, "validate_run", _validate)

    result = validation_service.backfill(date(2024, 1, 1), date(2024, 3, 31))
    assert result.runs_found == 2
    assert result.validated == 1
    assert result.failed == 1


def test_backfill_excludes_non_completed_ranking_runs(
    validation_service: SignalValidationService, db_session, monkeypatch
) -> None:
    _completed_run(db_session, date(2024, 2, 1))
    failed = RankingRun(
        strategy_name="momentum_v1",
        strategy_version="1.0.0",
        as_of_date=date(2024, 2, 10),
        inputs_hash=None,
        universe_code="PI_PM_CORE",
        benchmark_symbol="^NSEI",
        filter_config_hash="filter123",
        normalization_method="percentile",
        status=RankingRunStatus.FAILED.value,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        error_message="failed",
    )
    db_session.add(failed)
    db_session.commit()

    monkeypatch.setattr(
        validation_service,
        "validate_run",
        lambda run_id, *, force_recompute=False: MagicMock(),
    )

    result = validation_service.backfill(date(2024, 1, 1), date(2024, 3, 31))
    assert result.runs_found == 1
    assert result.validated == 1
