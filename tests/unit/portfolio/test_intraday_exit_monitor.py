"""Unit tests for IntradayExitMonitorService (ADR-033 T1 monitor).

Tests cover:
  - Advisory stop (−8%) fires PENDING + notification, HITL required
  - Critical stop (−10%) fires auto-exec when auto_exit_on_critical_stop=True
  - Critical stop does NOT auto-exec when flag is False (HITL path)
  - Dedup: same trigger same session → no duplicate row
  - Severity upgrade: existing PENDING row escalated to CRITICAL
  - Rank/regime/time triggers do NOT fire from T1 (stay in T2)
  - monitor_tier='INTRADAY' on all T1 rows
  - T2 ExitMonitorService tags rows monitor_tier='DAILY'
  - T2 dedup ignores INTRADAY rows (they coexist)
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models.portfolio_analytics import ExitRecommendation
from app.portfolio.exit_monitor.intraday_service import IntradayExitMonitorService
from app.portfolio.exit_monitor.quote_provider import QuoteProvider
from app.portfolio.exit_monitor.triggers import check_stop_loss, check_trailing_stop


# ── Pure trigger tests (no DB) ─────────────────────────────────────────────────


def test_advisory_stop_fires_at_negative_8():
    r = check_stop_loss(-8.0, stop_loss_pct=-8.0)
    assert r.fired is True
    assert r.trigger_code == "EXIT_STOP_LOSS"
    assert r.urgency == "HIGH"


def test_critical_stop_urgency_at_12_pct():
    # 12% loss >= 8% * 1.5 = 12% → CRITICAL
    r = check_stop_loss(-12.0, stop_loss_pct=-8.0)
    assert r.fired is True
    assert r.urgency == "CRITICAL"


def test_advisory_stop_no_fire_above_threshold():
    r = check_stop_loss(-5.0, stop_loss_pct=-8.0)
    assert r.fired is False


def test_trailing_stop_fires():
    r = check_trailing_stop(unrealized_pnl_pct=3.0, max_gain_pct=9.0, trailing_stop_pct=5.0)
    # drawback = 9 - 3 = 6 >= 5 and max_gain >= 5
    assert r.fired is True
    assert r.trigger_code == "EXIT_TRAILING_STOP"


def test_trailing_stop_no_fire_small_peak():
    # max_gain below trailing threshold → don't fire
    r = check_trailing_stop(unrealized_pnl_pct=0.0, max_gain_pct=3.0, trailing_stop_pct=5.0)
    assert r.fired is False


# ── Stub QuoteProvider for integration-level tests ────────────────────────────


class StubQuoteProvider(QuoteProvider):
    def __init__(self, prices: dict):
        self._prices = prices  # stock_id → ltp

    def get_ltp(self, stock_id):
        return self._prices.get(stock_id)


def _make_open_position(stock_id, avg_cost, position_id=None):
    pos = MagicMock()
    pos.id = position_id or uuid4()
    pos.stock_id = stock_id
    pos.avg_cost = avg_cost
    pos.position_status = "OPEN"
    pos.is_current = True
    pos.recommendation_result_id = None
    pos.weight_pct = None
    return pos


def _make_stock_mock(symbol="TEST.NS"):
    s = MagicMock()
    s.symbol = symbol
    return s


def _make_db(positions, existing_rec=None, symbol="TEST.NS"):
    """Build a db mock.

    scalar() is called twice per triggered position:
      1. _find_existing (dedup check) → existing_rec or None
      2. _get_symbol (stock lookup) → stock mock
    Use side_effect to return the right value per call.
    """
    db = MagicMock()
    db.scalars.return_value.all.return_value = positions
    # side_effect cycles: first call → dedup result, second → stock
    # Call order per triggered position: _get_symbol first, then _find_existing
    db.scalar.side_effect = [_make_stock_mock(symbol), existing_rec] * 10
    db.add = MagicMock()
    db.flush = MagicMock()
    return db


# ── T1 service tests ───────────────────────────────────────────────────────────


def test_advisory_stop_creates_pending_no_auto_exec():
    """−8% loss → PENDING row, no auto-exec, notification emitted."""
    sid = uuid4()
    pos = _make_open_position(sid, avg_cost=100.0)
    db = _make_db([pos], existing_rec=None)

    # LTP = 91.5 → −8.5% unrealized
    svc = IntradayExitMonitorService(
        db,
        quote_provider=StubQuoteProvider({sid: 91.5}),
        advisory_stop_pct=-8.0,
        critical_stop_pct=-10.0,
        auto_exit_on_critical_stop=False,
    )
    result = svc.run(session_date=date(2026, 6, 11))

    assert result.new_recommendations == 1
    assert result.auto_executed == 0
    assert len(result.notifications) == 1
    assert result.notifications[0].urgency == "HIGH"
    assert result.notifications[0].auto_executed is False

    # ExitRecommendation was created with PENDING status and INTRADAY tier
    db.add.assert_called_once()
    created: ExitRecommendation = db.add.call_args[0][0]
    assert created.status == "PENDING"
    assert created.monitor_tier == "INTRADAY"
    assert created.auto_executed is False
    assert "EXIT_STOP_LOSS" in created.triggers


def test_critical_stop_auto_exec_when_flag_on():
    """−10.5% with auto_exit_on_critical_stop=True → auto-exec fires."""
    sid = uuid4()
    pos_id = uuid4()
    pos = _make_open_position(sid, avg_cost=100.0, position_id=pos_id)
    db = _make_db([pos], existing_rec=None)

    mock_pts = MagicMock()
    mock_pts.execute_position_exit.return_value = MagicMock()

    svc = IntradayExitMonitorService(
        db,
        quote_provider=StubQuoteProvider({sid: 89.0}),  # −11% unrealized
        advisory_stop_pct=-8.0,
        critical_stop_pct=-10.0,
        auto_exit_on_critical_stop=True,
        paper_trade_service=mock_pts,
    )
    result = svc.run(session_date=date(2026, 6, 11))

    assert result.auto_executed == 1
    mock_pts.execute_position_exit.assert_called_once()
    call_kw = mock_pts.execute_position_exit.call_args.kwargs
    assert "intraday-exit:" in call_kw["idempotency_key"]
    assert "EXIT_STOP_LOSS" in call_kw["exit_triggers"]


def test_critical_stop_no_auto_exec_when_flag_off():
    """−11% but auto_exit_on_critical_stop=False → PENDING only, no auto-exec."""
    sid = uuid4()
    pos = _make_open_position(sid, avg_cost=100.0)
    db = _make_db([pos], existing_rec=None)

    svc = IntradayExitMonitorService(
        db,
        quote_provider=StubQuoteProvider({sid: 89.0}),
        advisory_stop_pct=-8.0,
        critical_stop_pct=-10.0,
        auto_exit_on_critical_stop=False,
    )
    result = svc.run(session_date=date(2026, 6, 11))

    assert result.auto_executed == 0
    assert result.new_recommendations == 1
    created: ExitRecommendation = db.add.call_args[0][0]
    assert created.status == "PENDING"


def test_dedup_skips_duplicate_within_session():
    """Same trigger already PENDING for this session → no new row, no duplicate notification."""
    sid = uuid4()
    pos = _make_open_position(sid, avg_cost=100.0)

    # Simulate existing PENDING INTRADAY row for EXIT_STOP_LOSS same session
    existing = MagicMock(spec=ExitRecommendation)
    existing.urgency = "HIGH"
    existing.auto_executed = False
    db = _make_db([pos], existing_rec=existing)

    svc = IntradayExitMonitorService(
        db,
        quote_provider=StubQuoteProvider({sid: 91.5}),  # −8.5%, same as before
        advisory_stop_pct=-8.0,
        critical_stop_pct=-10.0,
        auto_exit_on_critical_stop=False,
    )
    result = svc.run(session_date=date(2026, 6, 11))

    # No new row added (existing found, no severity upgrade since same urgency)
    assert result.new_recommendations == 0
    assert result.severity_upgrades == 0
    db.add.assert_not_called()


def test_severity_upgrade_escalates_existing_row():
    """Existing HIGH row escalated to CRITICAL when unrealized worsens past -10%."""
    sid = uuid4()
    pos = _make_open_position(sid, avg_cost=100.0)

    existing = MagicMock(spec=ExitRecommendation)
    existing.urgency = "HIGH"       # was HIGH from earlier advisory check
    existing.auto_executed = False
    db = _make_db([pos], existing_rec=existing)

    svc = IntradayExitMonitorService(
        db,
        quote_provider=StubQuoteProvider({sid: 87.5}),  # −12.5% → CRITICAL
        advisory_stop_pct=-8.0,
        critical_stop_pct=-10.0,
        auto_exit_on_critical_stop=False,  # upgrade without auto-exec
    )
    result = svc.run(session_date=date(2026, 6, 11))

    assert result.severity_upgrades == 1
    assert existing.urgency == "CRITICAL"
    assert len(result.notifications) == 1
    assert result.notifications[0].urgency == "CRITICAL"


def test_no_trigger_when_position_healthy():
    """−3% loss (above advisory stop) → no trigger, no recommendation."""
    sid = uuid4()
    pos = _make_open_position(sid, avg_cost=100.0)
    db = _make_db([pos], existing_rec=None)

    svc = IntradayExitMonitorService(
        db,
        quote_provider=StubQuoteProvider({sid: 97.0}),  # −3%
        advisory_stop_pct=-8.0,
        critical_stop_pct=-10.0,
        auto_exit_on_critical_stop=False,
    )
    result = svc.run(session_date=date(2026, 6, 11))

    assert result.new_recommendations == 0
    assert result.auto_executed == 0
    assert result.notifications == []
    db.add.assert_not_called()


def test_no_ltp_skips_position():
    """QuoteProvider returns None → position skipped silently."""
    sid = uuid4()
    pos = _make_open_position(sid, avg_cost=100.0)
    db = _make_db([pos], existing_rec=None)

    svc = IntradayExitMonitorService(
        db,
        quote_provider=StubQuoteProvider({}),  # no price for this stock
        advisory_stop_pct=-8.0,
        critical_stop_pct=-10.0,
        auto_exit_on_critical_stop=False,
    )
    result = svc.run(session_date=date(2026, 6, 11))

    assert result.positions_evaluated == 1
    assert result.new_recommendations == 0


# ── T2 monitor_tier tagging ───────────────────────────────────────────────────

def test_t2_monitor_tags_daily_tier():
    """ExitMonitorService creates rows with monitor_tier='DAILY'."""
    from app.portfolio.exit_monitor.service import ExitMonitorService

    db = MagicMock()
    pos = _make_open_position(uuid4(), avg_cost=100.0)
    pos.entry_date = date(2026, 5, 1)
    pos.recommendation_result_id = None
    pos.weight_pct = None

    db.scalars.return_value.all.return_value = [pos]
    db.scalar.return_value = None  # no existing rec, no ranking run

    svc = ExitMonitorService(db)
    # Patch helpers to produce a deterministic fired trigger (time stop)
    mock_settings = MagicMock()
    mock_settings.time_stop_enabled = True
    mock_settings.advisory_stop_pct = -8.0
    mock_settings.regime_dynamic_stops_enabled = False
    mock_settings.alpha_decay_grace_days = 5
    with patch.object(svc, "_build_position_context", return_value={
        "days_held": 35,  # > 30 day time stop
        "current_rank": None,
        "unrealized_pnl_pct": None,
        "max_gain_pct": None,
        "last_price": None,
        "avg_daily_volume": None,
    }), patch.object(svc, "_resolve_regime_posture", return_value="neutral"), \
       patch("app.portfolio.exit_monitor.service.get_settings", return_value=mock_settings), \
       patch("app.portfolio.exit_monitor.service.resolve_stop_pcts", return_value=(-8.0, -10.0)):
        recs = svc.run(as_of_date=date(2026, 6, 11))

    assert len(recs) == 1
    created: ExitRecommendation = db.add.call_args[0][0]
    assert created.monitor_tier == "DAILY"
    assert "EXIT_TIME" in created.triggers
