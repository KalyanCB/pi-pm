from __future__ import annotations

from datetime import date

from app.ops.daily_batch.evidence_windows import resolve_quant_evidence_window


def test_resolve_quant_evidence_window_uses_completed_dates_in_lookback():
    completed = [date(2025, 6, 1), date(2025, 8, 15), date(2026, 5, 20)]
    window = resolve_quant_evidence_window(
        plan_from_date=date(2026, 6, 1),
        target_trading_day=date(2026, 6, 1),
        holdout_start_date=date(2025, 1, 1),
        completed_validation_dates=completed,
    )
    assert window is not None
    start, end = window
    assert end == date(2026, 5, 20)
    assert start <= end
    assert start in completed


def test_resolve_quant_evidence_window_when_plan_from_after_last_completed():
    completed = [date(2025, 6, 1), date(2026, 5, 20), date(2026, 5, 22)]
    window = resolve_quant_evidence_window(
        plan_from_date=date(2026, 6, 1),
        target_trading_day=date(2026, 6, 1),
        holdout_start_date=date(2025, 1, 1),
        completed_validation_dates=completed,
    )
    assert window is not None
    start, end = window
    assert end == date(2026, 5, 22)
    assert start < end or start == date(2025, 6, 1)


def test_resolve_quant_evidence_window_none_when_no_completed():
    assert (
        resolve_quant_evidence_window(
            plan_from_date=date(2026, 6, 1),
            target_trading_day=date(2026, 6, 1),
            holdout_start_date=date(2025, 1, 1),
            completed_validation_dates=[],
        )
        is None
    )
