"""Unit tests for the realistic-fill pure math: market impact + session VWAP."""
from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest

from app.services.intraday_fill_service import market_impact_bps, vwap_from_bars


class TestMarketImpactBps:
    def test_no_order_value_is_half_spread(self):
        assert market_impact_bps(None, 1_000_000, spread_bps=8, coeff_bps=35) == 4.0
        assert market_impact_bps(0, 1_000_000, spread_bps=8, coeff_bps=35) == 4.0

    def test_unknown_adv_assumes_full_participation(self):
        # participation=1 → half_spread + coeff
        assert market_impact_bps(500_000, None, spread_bps=8, coeff_bps=35) == 4.0 + 35.0
        assert market_impact_bps(500_000, 0, spread_bps=8, coeff_bps=35) == 4.0 + 35.0

    def test_sqrt_scaling_with_participation(self):
        # order = 1% of ADV → impact = 4 + 35*sqrt(0.01) = 4 + 3.5
        got = market_impact_bps(10_000, 1_000_000, spread_bps=8, coeff_bps=35)
        assert got == pytest.approx(4.0 + 35.0 * math.sqrt(0.01))

    def test_bigger_order_costs_more(self):
        small = market_impact_bps(10_000, 1_000_000, 8, 35)
        big = market_impact_bps(200_000, 1_000_000, 8, 35)
        assert big > small

    def test_thinner_name_costs_more_for_same_order(self):
        liquid = market_impact_bps(100_000, 5_000_000, 8, 35)
        thin = market_impact_bps(100_000, 500_000, 8, 35)
        assert thin > liquid


class TestVwapFromBars:
    def _bars(self, start: datetime, prices_vols):
        return [
            (start + timedelta(minutes=15 * i), p, v) for i, (p, v) in enumerate(prices_vols)
        ]

    def test_empty_returns_none(self):
        assert vwap_from_bars([], 60) is None

    def test_volume_weighted(self):
        start = datetime(2026, 6, 24, 9, 15)
        # two bars within a 60-min window: prices 100 (vol 100) and 110 (vol 300)
        bars = self._bars(start, [(100.0, 100), (110.0, 300)])
        vwap, first_ts = vwap_from_bars(bars, 60)
        assert vwap == pytest.approx((100 * 100 + 110 * 300) / 400)
        assert first_ts == start

    def test_window_truncates_later_bars(self):
        start = datetime(2026, 6, 24, 9, 15)
        # third bar at +90min must be excluded by a 60-min window
        bars = self._bars(start, [(100.0, 100), (110.0, 100), (999.0, 100)])
        # i=0 at 9:15, i=1 at 9:30, i=2 at 9:45 → all < 60min; push the outlier far out
        bars[2] = (start + timedelta(minutes=90), 999.0, 100)
        vwap, _ = vwap_from_bars(bars, 60)
        assert vwap == pytest.approx(105.0)  # only first two

    def test_zero_volume_falls_back_to_simple_average(self):
        start = datetime(2026, 6, 24, 9, 15)
        bars = self._bars(start, [(100.0, 0), (120.0, None)])
        vwap, _ = vwap_from_bars(bars, 60)
        assert vwap == pytest.approx(110.0)


class TestMergeWindows:
    """Phase 1 backfill: decision dates expand to [d, d+buffer] and merge."""

    def _merge(self, dates, buffer):
        from datetime import date

        from scripts.backfill_intraday_fills import _merge_windows

        return _merge_windows({date(*d) for d in dates}, buffer)

    def test_empty(self):
        assert self._merge([], 5) == []

    def test_single_window(self):
        from datetime import date

        assert self._merge([(2026, 6, 1)], 5) == [(date(2026, 6, 1), date(2026, 6, 6))]

    def test_overlapping_merge(self):
        from datetime import date

        # 6/1+5=6/6 and 6/4 overlap → single span
        out = self._merge([(2026, 6, 1), (2026, 6, 4)], 5)
        assert out == [(date(2026, 6, 1), date(2026, 6, 9))]

    def test_disjoint_stay_separate(self):
        out = self._merge([(2026, 6, 1), (2026, 7, 1)], 5)
        assert len(out) == 2


class TestFillMetaCapture:
    """Phase 3: per-trade fill diagnostics — empty when no realistic quote (flag off)."""

    def _svc(self):
        from app.services.paper_trade_service import PaperTradeService

        return PaperTradeService.__new__(PaperTradeService)

    def test_no_quote_returns_empty(self):
        svc = self._svc()
        assert svc._fill_meta() == {}  # legacy path → metadata unchanged

    def test_quote_is_captured(self):
        from app.services.intraday_fill_service import FillQuote

        svc = self._svc()
        svc._last_fill_quote = FillQuote(
            fill_price=101.5,
            ref_price=101.0,
            impact_bps=15.0,
            participation=0.02,
            fill_ts=datetime(2026, 6, 24, 9, 15),
        )
        meta = svc._fill_meta()
        assert meta["fill_model"]["vwap"] == 101.0
        assert meta["fill_model"]["impact_bps"] == 15.0
        assert meta["fill_model"]["participation_pct"] == 2.0
