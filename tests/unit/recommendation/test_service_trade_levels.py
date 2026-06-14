"""ADR-034: recommendation-service trade-level enrichment (BUY vs WATCH vs REJECT)."""

from dataclasses import dataclass
from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

from app.core.config import Settings
from app.core.constants import RecommendationAction
from app.services.recommendation_service import RecommendationService


@dataclass
class _Bar:
    date: date
    high: float | None
    low: float | None
    close: float | None


def _bars():
    return [
        _Bar(date(2026, 6, d), high=105.0, low=95.0, close=100.0) for d in range(1, 8)
    ]


def _row(action: RecommendationAction):
    r = MagicMock()
    r.action = action
    r.stock_id = uuid4()
    return r


def _svc(*, bars=None, enabled=True):
    repo = MagicMock()
    repo.get_by_stock_and_date_range.return_value = bars if bars is not None else _bars()
    settings = Settings(recommendation_trade_levels_enabled=enabled)
    return RecommendationService(MagicMock(), market_data_repo=repo, settings=settings)


def test_buy_is_actionable():
    svc = _svc()
    levels = svc._compute_trade_levels(_row(RecommendationAction.BUY), date(2026, 6, 7))
    assert levels is not None
    assert levels.basis == "actionable"
    assert levels.entry_low < levels.reference_close < levels.entry_high
    assert levels.stop_critical < levels.stop_advisory < levels.reference_close


def test_watch_is_indicative():
    svc = _svc()
    levels = svc._compute_trade_levels(_row(RecommendationAction.WATCH), date(2026, 6, 7))
    assert levels is not None
    assert levels.basis == "indicative"


def test_reject_gets_no_levels():
    svc = _svc()
    assert svc._compute_trade_levels(_row(RecommendationAction.REJECT), date(2026, 6, 7)) is None


def test_disabled_flag_skips_levels():
    svc = _svc(enabled=False)
    assert svc._compute_trade_levels(_row(RecommendationAction.BUY), date(2026, 6, 7)) is None


def test_no_market_data_returns_none():
    svc = _svc(bars=[])
    assert svc._compute_trade_levels(_row(RecommendationAction.BUY), date(2026, 6, 7)) is None
