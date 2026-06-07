"""Replay Portfolio Manager — in-memory cash and positions, no DB writes."""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from app.replay.config.experiment_config import ReplayExperimentConfig
from app.replay.models import ReplayDailySnapshot, ReplayPosition, ReplayTrade

logger = logging.getLogger(__name__)


class ReplayPortfolioManager:
    """Manages in-memory cash and positions for a replay simulation.

    Design constraints:
    - Cash never goes negative.
    - Single-name cap enforced (default 18% of total equity).
    - max_positions enforced.
    - No DB writes — all state is in-memory.
    """

    def __init__(self, config: ReplayExperimentConfig) -> None:
        self._cash: float = config.capital.initial_cash
        self._positions: dict[UUID, ReplayPosition] = {}
        self._trades: list[ReplayTrade] = []
        self._total_sip_contributed: float = 0.0
        self._config = config

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def open_positions(self) -> list[ReplayPosition]:
        return list(self._positions.values())

    @property
    def held_stock_ids(self) -> set[UUID]:
        return set(self._positions.keys())

    @property
    def active_position_count(self) -> int:
        return len(self._positions)

    @property
    def market_value(self) -> float:
        return sum(p.market_value for p in self._positions.values())

    @property
    def total_equity(self) -> float:
        return self._cash + self.market_value

    @property
    def all_trades(self) -> list[ReplayTrade]:
        return list(self._trades)

    @property
    def total_sip_contributed(self) -> float:
        return self._total_sip_contributed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_available_cash(self) -> float:
        """Cash available after reserving cash floor."""
        floor = self.total_equity * self._config.portfolio.cash_floor_pct
        return max(0.0, self._cash - floor)

    def get_slot_budget(self, max_positions: int) -> float:
        """Deployable cash per remaining slot.

        slot_budget = available_cash * deploy_pct / max(1, slots_remaining)
        """
        slots_remaining = max(1, max_positions - self.active_position_count)
        deployable = self.get_available_cash() * self._config.portfolio.deploy_pct
        return deployable / slots_remaining

    def can_open_position(self, config: ReplayExperimentConfig) -> bool:
        """Return True if portfolio has capacity for another position."""
        return self.active_position_count < config.portfolio.max_positions

    def add_sip(self, amount: float, as_of_date: date) -> None:
        """Inject SIP contribution into cash."""
        self._cash += amount
        self._total_sip_contributed += amount
        logger.debug("SIP +%.0f on %s → cash %.0f", amount, as_of_date, self._cash)

    def open_position(self, position: ReplayPosition) -> bool:
        """Open a new position after enforcing caps.

        Returns True if position was accepted, False if rejected.
        """
        if position.stock_id in self._positions:
            logger.debug("Rejected duplicate position for %s", position.symbol)
            return False

        cost = position.entry_price * position.quantity
        if cost > self._cash:
            logger.debug("Rejected %s — insufficient cash (need %.0f, have %.0f)",
                         position.symbol, cost, self._cash)
            return False

        # Single-name cap check
        total_equity = self.total_equity
        if total_equity > 0:
            new_notional = position.entry_price * position.quantity
            cap_limit = total_equity * self._config.portfolio.single_name_cap_pct
            if new_notional > cap_limit:
                # Trim to cap
                max_qty = cap_limit / position.entry_price
                if max_qty < 1:
                    logger.debug("Rejected %s — single-name cap too small", position.symbol)
                    return False
                position.quantity = max_qty
                cost = position.entry_price * position.quantity

        self._cash -= cost
        self._positions[position.stock_id] = position
        logger.debug("Opened %s qty=%.2f @ %.2f cash_remaining=%.0f",
                     position.symbol, position.quantity, position.entry_price, self._cash)
        return True

    def close_position(
        self,
        stock_id: UUID,
        exit_date: date,
        exit_price: float,
        exit_reason: str,
        slippage_bps: float = 5.0,
        fee: float = 20.0,
    ) -> ReplayTrade:
        """Close an open position and return the completed trade record."""
        pos = self._positions.pop(stock_id)
        slippage_amt = exit_price * (slippage_bps / 10_000)
        fill_price = exit_price - slippage_amt  # SELL: worse fill
        proceeds = fill_price * pos.quantity
        net_proceeds = proceeds - fee

        self._cash += net_proceeds

        pnl = net_proceeds - pos.cost_basis
        pnl_pct = pnl / pos.cost_basis if pos.cost_basis > 0 else 0.0

        trade = ReplayTrade(
            stock_id=pos.stock_id,
            symbol=pos.symbol,
            strategy_name=pos.strategy_name,
            side="SELL",
            trade_date=exit_date,
            price=fill_price,
            quantity=pos.quantity,
            notional=proceeds,
            fee=fee,
            slippage=slippage_amt * pos.quantity,
            conviction_band=pos.conviction_band,
            regime_label=pos.regime_at_entry,
            holding_days=pos.holding_days,
            pnl=pnl,
            pnl_pct=pnl_pct * 100,
            exit_reason=exit_reason,
        )
        self._trades.append(trade)
        logger.debug("Closed %s pnl=%.0f (%.1f%%) reason=%s",
                     pos.symbol, pnl, pnl_pct * 100, exit_reason)
        return trade

    def record_buy_trade(self, trade: ReplayTrade) -> None:
        """Record a BUY trade for reporting (position already opened via open_position)."""
        self._trades.append(trade)

    def mark_to_market(self, price_map: dict[UUID, float], as_of_date: date) -> None:
        """Update unrealized PnL for all open positions."""
        for pos in self._positions.values():
            price = price_map.get(pos.stock_id)
            if price is None:
                continue
            pos.current_price = price
            pos.holding_days += 1
            pos.unrealized_pnl = (price - pos.entry_price) * pos.quantity
            pos.unrealized_pct = (
                (price - pos.entry_price) / pos.entry_price * 100
                if pos.entry_price > 0
                else 0.0
            )

    def snapshot(self, as_of_date: date, regime_label: str,
                 buys_today: int = 0, exits_today: int = 0,
                 sip_today: float = 0.0) -> ReplayDailySnapshot:
        """Capture end-of-day portfolio state."""
        mv = self.market_value
        equity = self._cash + mv
        return ReplayDailySnapshot(
            date=as_of_date,
            cash=self._cash,
            market_value=mv,
            total_equity=equity,
            regime_label=regime_label,
            active_positions=self.active_position_count,
            buys_today=buys_today,
            exits_today=exits_today,
            sip_contributed=sip_today,
            nav=equity,
        )
