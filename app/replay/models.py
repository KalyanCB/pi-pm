"""In-memory data models for replay simulation — no DB persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID


@dataclass
class ReplayPosition:
    """In-memory position — NOT persisted to DB."""

    stock_id: UUID
    symbol: str
    strategy_name: str
    entry_date: date
    entry_price: float
    quantity: float
    conviction_band: str
    regime_at_entry: str
    recommendation_result_id: UUID
    rank_at_entry: int
    holding_days: int = 0
    # updated daily
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pct: float = 0.0

    @property
    def market_value(self) -> float:
        return self.current_price * self.quantity

    @property
    def cost_basis(self) -> float:
        return self.entry_price * self.quantity


@dataclass
class ReplayTrade:
    """Completed trade record."""

    stock_id: UUID
    symbol: str
    strategy_name: str
    side: str              # BUY | SELL
    trade_date: date
    price: float
    quantity: float
    notional: float
    fee: float
    slippage: float
    conviction_band: str
    regime_label: str
    holding_days: int | None = None   # populated on SELL
    pnl: float | None = None          # populated on SELL
    pnl_pct: float | None = None
    exit_reason: str | None = None


@dataclass
class ReplayDailySnapshot:
    """End-of-day portfolio snapshot."""

    date: date
    cash: float
    market_value: float
    total_equity: float        # cash + market_value
    regime_label: str
    active_positions: int
    buys_today: int
    exits_today: int
    sip_contributed: float
    nav: float                 # total_equity (alias for clarity)


@dataclass
class ReplayContext:
    """Immutable context for a single replay day."""

    as_of_date: date
    regime_label: str
    regime_posture: str        # risk_on | neutral | defensive
    trading_day_index: int     # 0-based
    is_first_trading_day_of_month: bool
    is_sip_day: bool


@dataclass
class ReplayMetrics:
    """Final aggregate metrics for a completed replay."""

    # Return metrics
    initial_nav: float
    final_nav: float
    total_return_pct: float
    cagr_pct: float
    sharpe_ratio: float | None
    max_drawdown_pct: float
    calmar_ratio: float | None

    # Trade metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float | None
    expectancy: float | None
    avg_win_pct: float | None
    avg_loss_pct: float | None
    avg_holding_days: float | None

    # Activity
    total_buys: int
    total_exits: int
    total_sip_contributed: float

    # Regime breakdown: {regime_label: {"trades": int, "pnl": float}}
    regime_breakdown: dict[str, dict] = field(default_factory=dict)
    # Strategy breakdown: {strategy_name: {"trades": int, "pnl": float}}
    strategy_breakdown: dict[str, dict] = field(default_factory=dict)
