from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from app.ops.daily_batch.batch_planner import DailyBatchPlanner, StrategySpec
from app.ops.daily_batch.models import TradingDayResolution


def test_planner_detects_ranking_gaps():
    db = MagicMock()
    planner = DailyBatchPlanner(
        db,
        universe_code="NIFTY_500",
        benchmark_symbol="^NSEI",
        strategies=[StrategySpec("breakout_v1", "1.0.0")],
    )
    resolution = TradingDayResolution(
        target_trading_day=date(2026, 5, 30),
        calendar_today=date(2026, 5, 30),
        session_complete=True,
        latest_benchmark_date=date(2026, 5, 29),
        resolution_reason="test",
    )

    with (
        patch.object(planner.universe_repo, "list_stocks_in_universe", return_value=[]),
        patch.object(planner.stock_repo, "get_by_symbol", return_value=None),
        patch.object(
            planner.calendar,
            "trading_days_in_range",
            return_value=[date(2026, 5, 30)],
        ),
        patch.object(planner.ranking_run_repo, "list_completed_in_range", return_value=[]),
        patch.object(planner.validation_repo, "get_by_ranking_run_id", return_value=None),
    ):
        plan = planner.build_plan(resolution)

    assert plan.needs_ingest is True
    assert plan.ranking_gaps["breakout_v1:1.0.0"] == [date(2026, 5, 30)]
