"""Tests for recommendation_service holding_days wiring (Improvement 1)."""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.recommendation.engine import ExitSignal, EngineConfig, RankingResultRow, ValidationSummary, run


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_ranking_run(strategy_name: str = "momentum_v1", as_of_date: date = date(2026, 1, 31)):
    rr = MagicMock()
    rr.id = uuid.uuid4()
    rr.strategy_name = strategy_name
    rr.strategy_version = "1.0.0"
    rr.universe_code = "NIFTY_500"
    rr.as_of_date = as_of_date
    rr.regime_label = "BULL_LOW_VOL"
    rr.status = "completed"
    return rr


# ── Test: no open positions → engine receives empty exit_signals ──────────────

def test_holding_days_zero_when_no_open_positions():
    """When there are no open portfolio positions the service returns {} for
    exit_signals and set() for active_position_stock_ids.  The engine must
    produce no HOLD/EXIT actions (all stocks treated as entry candidates)."""
    from app.services.recommendation_service import RecommendationService

    ranking_run = _make_ranking_run()

    db = MagicMock()
    # scalars().all() returns empty list (no open positions)
    db.scalars.return_value.all.return_value = []

    svc = RecommendationService.__new__(RecommendationService)
    svc.db = db
    svc.exit_metric_repo = MagicMock()
    svc.exit_metric_repo.list_alpha_decay.return_value = []
    svc.exit_metric_repo.list_policy_metrics_covering_as_of.return_value = []

    signals = svc._load_exit_signals(ranking_run)
    active_ids = svc._load_active_position_stock_ids(ranking_run)

    assert signals == {}
    assert active_ids == set()


# ── Test: open position → holding_days computed from SQL count ───────────────

def test_holding_days_populated_from_open_position():
    """Mock an open position with entry_date 25 trading days ago.
    The service builds a signal with holding_days == 25 (the mocked SQL count).
    With max_holding_days=30, the engine must NOT yet fire TIME_STOP.
    With max_holding_days=20, holding_days > threshold → TIME_STOP fires."""
    from app.services.recommendation_service import RecommendationService

    stock_id = uuid.uuid4()
    ranking_run = _make_ranking_run(as_of_date=date(2026, 1, 31))

    pos = MagicMock()
    pos.stock_id = stock_id
    pos.entry_date = date(2025, 12, 26)  # ~25 trading days before 2026-01-31

    db = MagicMock()
    db.scalars.return_value.all.return_value = [pos]
    # Simulate SQL COUNT returning 25 trading days
    db.execute.return_value.scalar.return_value = 25

    svc = RecommendationService.__new__(RecommendationService)
    svc.db = db
    svc.exit_metric_repo = MagicMock()
    svc.exit_metric_repo.list_alpha_decay.return_value = []
    svc.exit_metric_repo.list_policy_metrics_covering_as_of.return_value = []
    svc.regime_repo = MagicMock()

    signals = svc._load_exit_signals(ranking_run)

    assert stock_id in signals
    sig = signals[stock_id]
    assert sig.holding_days == 25

    # Verify engine behaviour: holding_days=25 < max_holding_days=30 → no time stop
    row = RankingResultRow(stock_id=stock_id, rank=5, composite_score=0.75)
    cfg_no_stop = EngineConfig(
        regime_posture="risk_on",
        max_holding_days=30,
    )
    val = ValidationSummary(status="completed", ic_20d=0.07, top_decile_spread=0.03)
    results, _ = run(
        ranking_run_id=ranking_run.id,
        ranking_results=[row],
        validation=val,
        config=cfg_no_stop,
        active_position_stock_ids={stock_id},
        exit_signals=signals,
    )
    actions = {r.action for r in results}
    # Should be HOLD, not EXIT_APPROVED
    assert "EXIT_APPROVED" not in actions

    # Verify engine behaviour: holding_days=25 >= max_holding_days=20 → TIME_STOP fires
    cfg_with_stop = EngineConfig(
        regime_posture="risk_on",
        max_holding_days=20,
    )
    results2, _ = run(
        ranking_run_id=ranking_run.id,
        ranking_results=[row],
        validation=val,
        config=cfg_with_stop,
        active_position_stock_ids={stock_id},
        exit_signals=signals,
    )
    from app.core.constants import RecommendationAction
    exit_results = [r for r in results2 if r.stock_id == stock_id]
    assert len(exit_results) == 1
    assert exit_results[0].action == RecommendationAction.EXIT_APPROVED
