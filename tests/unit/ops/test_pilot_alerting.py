"""Pilot alerting tests."""
from datetime import UTC, date, datetime

from app.ops.pilot.alerting import AlertCode, AlertSeverity, evaluate_alerts
from app.models.daily_batch import DailyBatchRun


def test_no_batch_alerts_critical(db_session):
    alerts = evaluate_alerts(db_session, as_of_date=date(2026, 6, 5))
    codes = [a.code for a in alerts]
    assert AlertCode.BATCH_STALE.value in codes


def test_batch_failed_alert(db_session):
    run = DailyBatchRun(
        status="failed",
        universe_code="NIFTY_500",
        benchmark_symbol="^NSEI",
        parameter_set={},
        dry_run=False,
        started_at=datetime(2026, 6, 5, 18, 0, tzinfo=UTC),
        error_message="ingest timeout",
        target_trading_day=date(2026, 6, 5),
    )
    db_session.add(run)
    db_session.flush()

    alerts = evaluate_alerts(db_session, as_of_date=date(2026, 6, 5))
    failed = [a for a in alerts if a.code == AlertCode.BATCH_FAILED.value]
    assert len(failed) == 1
    assert failed[0].severity == AlertSeverity.CRITICAL.value
