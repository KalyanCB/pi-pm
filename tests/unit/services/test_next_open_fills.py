"""Execution-realism: next_open_fills_enabled makes _fill_price use the NEXT
trading day's OPEN instead of the same-bar close (removes look-ahead)."""
from datetime import date
from types import SimpleNamespace

from app.services.paper_trade_service import PaperTradeService


class _Repo:
    def __init__(self, next_open=None, last_close=100.0):
        self._next = SimpleNamespace(open=next_open) if next_open is not None else None
        self._close = SimpleNamespace(close=last_close)
    def get_first_bar_after(self, stock_id, after_date, source=None):
        return self._next
    def get_by_stock_and_date_range(self, stock_id, end_date=None, limit=None):
        return [self._close]


def _svc(repo, next_open_enabled):
    s = PaperTradeService.__new__(PaperTradeService)
    s.market_data_repo = repo
    s.settings = SimpleNamespace(cost_slippage_bps=5.0, next_open_fills_enabled=next_open_enabled)
    return s


def test_next_open_fill_uses_next_bar_open():
    svc = _svc(_Repo(next_open=110.0, last_close=100.0), next_open_enabled=True)
    px, ref = svc._fill_price("sid", date(2024, 1, 1), side="BUY")
    assert ref == 110.0                       # next day's OPEN, not the 100 close
    assert px == round(110.0 * 1.0005, 4)     # + 5bps buy slippage


def test_same_bar_close_when_flag_off():
    svc = _svc(_Repo(next_open=110.0, last_close=100.0), next_open_enabled=False)
    px, ref = svc._fill_price("sid", date(2024, 1, 1), side="BUY")
    assert ref == 100.0                       # falls back to same-bar close


def test_next_open_falls_back_to_close_on_final_day():
    # No next bar (final day) → fall back to close fill, never crash.
    svc = _svc(_Repo(next_open=None, last_close=100.0), next_open_enabled=True)
    px, ref = svc._fill_price("sid", date(2024, 1, 1), side="SELL")
    assert ref == 100.0
    assert px == round(100.0 * 0.9995, 4)     # sell slippage on the close
