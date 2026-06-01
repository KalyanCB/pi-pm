from datetime import date

from app.db.repositories.exit_research_run_repository import ExitResearchRunRepository


def test_exit_research_run_progress_tracking(db_session):
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
    repo.set_total_entries(run, 1000)
    assert run.total_entries == 1000
    assert run.processed_entries == 0

    repo.update_progress(
        run,
        processed_entries=100,
        percent_complete=10.0,
        elapsed_seconds=42.5,
    )
    assert run.processed_entries == 100
    assert float(run.percent_complete) == 10.0
    assert float(run.elapsed_seconds) == 42.5
    assert run.last_progress_at is not None

    completed = repo.complete(run, signals_processed=1000, metrics_written=50)
    assert completed.status == "completed"
    assert completed.signals_processed == 1000
