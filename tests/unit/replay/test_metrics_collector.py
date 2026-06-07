"""Unit tests for ReplayMetricsCollector."""

from __future__ import annotations

import math
import uuid
from datetime import date

import pytest

from app.replay.metrics_collector import ReplayMetricsCollector
from app.replay.models import ReplayDailySnapshot, ReplayTrade

TODAY = date(2025, 1, 2)


def _snap(d: date, nav: float, regime: str = "BULL_LOW_VOL") -> ReplayDailySnapshot:
    return ReplayDailySnapshot(
        date=d,
        cash=nav * 0.5,
        market_value=nav * 0.5,
        total_equity=nav,
        regime_label=regime,
        active_positions=2,
        buys_today=0,
        exits_today=0,
        sip_contributed=0.0,
        nav=nav,
    )


def _sell_trade(pnl: float, pnl_pct: float, holding_days: int = 10) -> ReplayTrade:
    return ReplayTrade(
        stock_id=uuid.uuid4(),
        symbol="TEST",
        strategy_name="breakout_v1",
        side="SELL",
        trade_date=TODAY,
        price=100.0,
        quantity=10.0,
        notional=1000.0,
        fee=20.0,
        slippage=5.0,
        conviction_band="HIGH",
        regime_label="BULL_LOW_VOL",
        holding_days=holding_days,
        pnl=pnl,
        pnl_pct=pnl_pct,
        exit_reason="EXIT_TIME",
    )


def test_cagr_calculation():
    collector = ReplayMetricsCollector()
    # 100% return over 1 year → CAGR = 100%
    collector.record_day(_snap(date(2024, 1, 2), 1_000_000))
    collector.record_day(_snap(date(2025, 1, 2), 2_000_000))
    collector.all_trades = []

    metrics = collector.compute_final_metrics(date(2024, 1, 2), date(2025, 1, 2))

    assert abs(metrics.total_return_pct - 100.0) < 0.1
    assert metrics.cagr_pct > 0


def test_sharpe_calculation():
    """Sharpe is positive for a noisy-but-upward NAV series."""
    import random

    random.seed(42)
    collector = ReplayMetricsCollector()
    nav = 1_000_000.0
    # Add variable daily returns so std != 0
    for i in range(60):
        # random daily return between +0.05% and +0.5%
        daily_return = 0.0005 + random.uniform(0, 0.0045)
        nav *= 1 + daily_return
        collector.record_day(_snap(date(2024, 1, 1), nav))
    collector.all_trades = []

    metrics = collector.compute_final_metrics(date(2024, 1, 1), date(2024, 3, 1))

    assert metrics.sharpe_ratio is not None
    assert metrics.sharpe_ratio > 0


def test_max_drawdown_calculation():
    collector = ReplayMetricsCollector()
    navs = [1_000_000, 1_100_000, 900_000, 950_000, 1_050_000]
    for i, nav in enumerate(navs):
        collector.record_day(_snap(date(2024, 1, i + 1), nav))
    collector.all_trades = []

    metrics = collector.compute_final_metrics(date(2024, 1, 1), date(2024, 1, 5))

    # Peak was 1.1M, trough was 0.9M → drawdown = (0.9-1.1)/1.1 ≈ -18.18%
    assert metrics.max_drawdown_pct < -18.0
    assert metrics.max_drawdown_pct > -19.0


def test_profit_factor():
    collector = ReplayMetricsCollector()
    collector.record_day(_snap(date(2024, 1, 1), 1_000_000))
    collector.all_trades = [
        _sell_trade(pnl=1000, pnl_pct=10.0),   # win
        _sell_trade(pnl=2000, pnl_pct=20.0),   # win
        _sell_trade(pnl=-500, pnl_pct=-5.0),   # loss
    ]

    metrics = collector.compute_final_metrics(date(2024, 1, 1), date(2024, 6, 1))

    # gross_profit=3000, gross_loss=500 → PF=6.0
    assert metrics.profit_factor is not None
    assert abs(metrics.profit_factor - 6.0) < 0.01


def test_win_rate():
    collector = ReplayMetricsCollector()
    collector.record_day(_snap(date(2024, 1, 1), 1_000_000))
    collector.all_trades = [
        _sell_trade(pnl=500, pnl_pct=5.0),
        _sell_trade(pnl=300, pnl_pct=3.0),
        _sell_trade(pnl=-200, pnl_pct=-2.0),
        _sell_trade(pnl=-100, pnl_pct=-1.0),
    ]

    metrics = collector.compute_final_metrics(date(2024, 1, 1), date(2024, 6, 1))

    assert metrics.total_trades == 4
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 2
    assert abs(metrics.win_rate_pct - 50.0) < 0.01


def test_empty_trades_handled():
    """No trades → graceful metrics with zero/None values."""
    collector = ReplayMetricsCollector()
    collector.record_day(_snap(date(2024, 1, 1), 1_000_000))
    collector.all_trades = []

    metrics = collector.compute_final_metrics(date(2024, 1, 1), date(2024, 6, 1))

    assert metrics.total_trades == 0
    assert metrics.win_rate_pct == 0.0
    assert metrics.profit_factor is None
    assert metrics.expectancy is None


def test_sharpe_flat_nav_returns_none():
    """All same NAV → zero std → Sharpe should be None."""
    collector = ReplayMetricsCollector()
    for i in range(5):
        collector.record_day(_snap(date(2024, 1, i + 1), 1_000_000))
    collector.all_trades = []

    metrics = collector.compute_final_metrics(date(2024, 1, 1), date(2024, 1, 5))
    assert metrics.sharpe_ratio is None
