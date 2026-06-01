from contextlib import ExitStack
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.constants import ExitResearchPhase, ExitResearchRunStatus
from app.db.repositories.exit_research_metric_repository import ExitResearchMetricRepository
from app.db.repositories.exit_research_run_repository import ExitResearchRunRepository
from app.models.exit_research import ExitResearchPolicyMetric
from app.services.exit_research_service import ExitResearchService
from app.workspace_exit_research.models import PolicyMetricResult


def test_phase_and_persistence_fields_on_run(db_session):
    repo = ExitResearchRunRepository(db_session)
    run = repo.create_running(
        strategy_name="breakout_v1",
        strategy_version="1.0.0",
        universe_code="NIFTY_500",
        as_of_date_start=date(2024, 1, 1),
        as_of_date_end=date(2024, 12, 31),
        holdout_start_date=date(2025, 1, 1),
        parameter_set={},
    )
    assert run.current_phase == ExitResearchPhase.COLLECTING_ENTRIES.value

    repo.set_phase(run, ExitResearchPhase.PERSISTING_POLICY_METRICS)
    repo.set_persistence_totals(run, persistence_items_total=300)
    repo.update_persistence_progress(
        run,
        persistence_items_processed=25,
        percent_complete=92.5,
        elapsed_seconds=100.0,
    )
    db_session.commit()

    refreshed = repo.get_by_id(run.id)
    assert refreshed is not None
    assert refreshed.current_phase == ExitResearchPhase.PERSISTING_POLICY_METRICS.value
    assert refreshed.persistence_items_total == 300
    assert refreshed.persistence_items_processed == 25
    assert float(refreshed.percent_complete) == 92.5


def _minimal_backfill_patches(service: ExitResearchService):
    fake_entry = MagicMock()
    fake_entry.stock_id = uuid4()
    fake_entry.ranking_run_id = uuid4()
    fake_entry.regime_label = "BULL_LOW_VOL"
    fake_entry.entry_date = date(2024, 6, 3)

    fake_result = PolicyMetricResult(
        "FIXED_HOLD",
        "FIXED_HOLD_20",
        "breakout_v1",
        "1.0.0",
        "PI_PM_CORE",
        "ALL",
        "HOLDOUT",
        20,
        50,
        0.05,
        0.04,
        0.01,
        0.6,
        20.0,
        0.01,
        0.09,
        "ok",
        date(2025, 1, 1),
        date(2024, 1, 1),
        date(2024, 12, 31),
    )

    return [
        patch.object(service.loader, "load_entries", return_value=[fake_entry]),
        patch("app.services.exit_research_service.ResearchBarCache"),
        patch("app.services.exit_research_service.RankPathCache"),
        patch("app.services.exit_research_service.RegimePathCache"),
        patch("app.services.exit_research_service.run_fixed_hold_batch", return_value=[]),
        patch("app.services.exit_research_service.run_rank_deterioration_batch", return_value=[]),
        patch("app.services.exit_research_service.run_regime_exit_batch", return_value=[]),
        patch("app.services.exit_research_service.run_trend_failure_batch", return_value=[]),
        patch("app.services.exit_research_service.alpha_decay_returns", return_value={}),
        patch(
            "app.services.exit_research_service.build_policy_metric_buckets",
            return_value={("FIXED_HOLD", "FIXED_HOLD_20", "ALL", "HOLDOUT"): [MagicMock()]},
        ),
        patch.object(service.engine, "aggregate_policy", return_value=fake_result),
        patch.object(service.engine, "aggregate_alpha_decay", return_value=[]),
    ]


def test_backfill_completes_with_phases_and_visible_metrics(db_session):
    run_repo = ExitResearchRunRepository(db_session)
    metric_repo = ExitResearchMetricRepository(db_session)
    service = ExitResearchService(db_session, run_repo, metric_repo, persist_commit_interval=1)

    with ExitStack() as stack:
        mocks = [stack.enter_context(p) for p in _minimal_backfill_patches(service)]
        mocks[1].return_value.get.return_value = [MagicMock()]
        completed = service.backfill(
            universe_code="PI_PM_CORE",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

    assert completed.status == ExitResearchRunStatus.COMPLETED.value
    assert completed.current_phase == ExitResearchPhase.COMPLETED.value
    assert float(completed.percent_complete) == 100.0

    count = db_session.scalar(select(func.count()).select_from(ExitResearchPolicyMetric))
    assert count == 1


def test_backfill_failure_during_persistence_marks_failed(db_session):
    run_repo = ExitResearchRunRepository(db_session)
    metric_repo = ExitResearchMetricRepository(db_session)
    service = ExitResearchService(db_session, run_repo, metric_repo, persist_commit_interval=25)

    with ExitStack() as stack:
        mocks = [stack.enter_context(p) for p in _minimal_backfill_patches(service)]
        stack.enter_context(
            patch.object(metric_repo, "upsert_policy_metric", side_effect=RuntimeError("disk full"))
        )
        mocks[1].return_value.get.return_value = [MagicMock()]
        with pytest.raises(RuntimeError, match="disk full"):
            service.backfill(
                universe_code="PI_PM_CORE",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )

    db_session.expire_all()
    run = run_repo.list_runs(limit=1)[0]
    assert run.status == ExitResearchRunStatus.FAILED.value
    assert run.current_phase == ExitResearchPhase.FAILED.value
