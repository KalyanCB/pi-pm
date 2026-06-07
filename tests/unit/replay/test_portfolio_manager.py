"""Unit tests for ReplayPortfolioManager."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.replay.config.experiment_config import (
    CapitalConfig,
    ExecutionConfig,
    PortfolioConfig,
    ReplayExperimentConfig,
)
from app.replay.models import ReplayPosition
from app.replay.portfolio_manager import ReplayPortfolioManager

TODAY = date(2025, 1, 15)
STOCK_A = uuid.uuid4()
STOCK_B = uuid.uuid4()
REC_ID = uuid.uuid4()


def _make_config(
    initial_cash: float = 1_000_000,
    max_positions: int = 10,
    single_name_cap_pct: float = 0.18,
    cash_floor_pct: float = 0.15,
    deploy_pct: float = 0.85,
) -> ReplayExperimentConfig:
    return ReplayExperimentConfig(
        experiment_id="test",
        name="test",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        capital=CapitalConfig(initial_cash=initial_cash),
        portfolio=PortfolioConfig(
            max_positions=max_positions,
            single_name_cap_pct=single_name_cap_pct,
            cash_floor_pct=cash_floor_pct,
            deploy_pct=deploy_pct,
        ),
    )


def _make_position(
    stock_id: uuid.UUID = None,
    entry_price: float = 100.0,
    quantity: float = 100.0,
) -> ReplayPosition:
    return ReplayPosition(
        stock_id=stock_id or STOCK_A,
        symbol="TEST",
        strategy_name="breakout_v1",
        entry_date=TODAY,
        entry_price=entry_price,
        quantity=quantity,
        conviction_band="HIGH",
        regime_at_entry="BULL_LOW_VOL",
        recommendation_result_id=REC_ID,
        rank_at_entry=5,
    )


def test_initial_cash_correct():
    config = _make_config(initial_cash=500_000)
    pm = ReplayPortfolioManager(config)
    # Total equity = cash before any trades
    assert pm.total_equity == 500_000
    assert pm._cash == 500_000


def test_sip_adds_cash():
    config = _make_config(initial_cash=1_000_000)
    pm = ReplayPortfolioManager(config)
    pm.add_sip(50_000, TODAY)
    assert pm._cash == 1_050_000
    assert pm.total_sip_contributed == 50_000


def test_position_cap_enforced():
    """Single-name cap trims quantity when notional exceeds 18% of equity."""
    config = _make_config(initial_cash=1_000_000, single_name_cap_pct=0.18)
    pm = ReplayPortfolioManager(config)

    # Attempt to buy 2000 shares @ 200 = 400,000 notional (40% of 1M — exceeds 18% cap)
    pos = _make_position(entry_price=200.0, quantity=2000.0)
    result = pm.open_position(pos)

    assert result is True
    # After cap: max notional = 1_000_000 * 0.18 = 180_000 → qty = 180_000 / 200 = 900
    assert pos.quantity <= 900.0 + 0.01  # allow float tolerance


def test_cash_never_negative():
    config = _make_config(initial_cash=10_000)
    pm = ReplayPortfolioManager(config)

    # Try to open a position that costs more than cash floor allows
    pos = _make_position(entry_price=1000.0, quantity=100.0)  # cost = 100,000 >> 10,000
    result = pm.open_position(pos)

    assert result is False
    assert pm._cash == 10_000  # unchanged


def test_max_positions_enforced():
    config = _make_config(initial_cash=10_000_000, max_positions=2)
    pm = ReplayPortfolioManager(config)

    pos_a = _make_position(stock_id=STOCK_A, entry_price=10.0, quantity=1.0)
    pos_b = _make_position(stock_id=STOCK_B, entry_price=10.0, quantity=1.0)
    pos_c = _make_position(stock_id=uuid.uuid4(), entry_price=10.0, quantity=1.0)

    assert pm.open_position(pos_a) is True
    assert pm.open_position(pos_b) is True
    assert pm.can_open_position(config) is False

    # can_open_position returns False — engine should check this before calling open_position
    assert pm.active_position_count == 2


def test_single_name_cap():
    """Buying same stock twice is rejected (duplicate position)."""
    config = _make_config(initial_cash=10_000_000)
    pm = ReplayPortfolioManager(config)

    pos1 = _make_position(stock_id=STOCK_A, entry_price=50.0, quantity=10.0)
    pos2 = _make_position(stock_id=STOCK_A, entry_price=55.0, quantity=10.0)

    assert pm.open_position(pos1) is True
    assert pm.open_position(pos2) is False  # duplicate rejected


def test_mark_to_market_updates_unrealized():
    config = _make_config(initial_cash=1_000_000)
    pm = ReplayPortfolioManager(config)

    pos = _make_position(entry_price=100.0, quantity=100.0)
    pm.open_position(pos)

    pm.mark_to_market({STOCK_A: 120.0}, TODAY)

    pos_after = pm._positions[STOCK_A]
    assert pos_after.current_price == 120.0
    assert abs(pos_after.unrealized_pnl - 2000.0) < 0.01  # (120-100)*100
    assert abs(pos_after.unrealized_pct - 20.0) < 0.01


def test_close_position_returns_trade():
    config = _make_config(initial_cash=1_000_000)
    pm = ReplayPortfolioManager(config)

    pos = _make_position(entry_price=100.0, quantity=100.0)
    pm.open_position(pos)

    trade = pm.close_position(
        STOCK_A,
        exit_date=TODAY,
        exit_price=110.0,
        exit_reason="EXIT_TIME",
        slippage_bps=5.0,
        fee=20.0,
    )

    assert trade.side == "SELL"
    assert trade.exit_reason == "EXIT_TIME"
    assert trade.pnl is not None
    assert STOCK_A not in pm._positions
