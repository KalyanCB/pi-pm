"""Replay Metrics Collector — accumulates NAV series and computes final metrics."""

from __future__ import annotations

import math
from datetime import date

from app.replay.models import ReplayDailySnapshot, ReplayMetrics, ReplayTrade


class ReplayMetricsCollector:
    """Accumulates simulation state day by day and computes final performance metrics."""

    def __init__(self) -> None:
        self.snapshots: list[ReplayDailySnapshot] = []
        self.all_trades: list[ReplayTrade] = []
        self._initial_nav: float | None = None

    # ------------------------------------------------------------------
    # Accumulation
    # ------------------------------------------------------------------

    def record_day(self, snapshot: ReplayDailySnapshot) -> None:
        if self._initial_nav is None:
            self._initial_nav = snapshot.nav
        self.snapshots.append(snapshot)

    def record_entry(self, trade: ReplayTrade) -> None:
        # BUY trades are recorded via portfolio_manager.record_buy_trade
        # This method kept for potential future use / symmetry
        pass

    def record_exit(self, trade: ReplayTrade) -> None:
        # SELL trades are already appended by portfolio_manager.close_position
        # This method kept for potential future use / symmetry
        pass

    # ------------------------------------------------------------------
    # Final metrics
    # ------------------------------------------------------------------

    def compute_final_metrics(self, start_date: date, end_date: date) -> ReplayMetrics:
        """Compute all aggregate metrics from accumulated snapshots and trades."""
        all_trades = self.all_trades  # populated externally from portfolio.all_trades

        nav_series = [s.nav for s in self.snapshots]
        initial_nav = self._initial_nav or (nav_series[0] if nav_series else 1.0)
        final_nav = nav_series[-1] if nav_series else initial_nav

        total_return_pct = (final_nav / initial_nav - 1) * 100 if initial_nav > 0 else 0.0

        # CAGR
        days = (end_date - start_date).days
        years = days / 365.25
        if years > 0 and initial_nav > 0:
            cagr_pct = ((final_nav / initial_nav) ** (1 / years) - 1) * 100
        else:
            cagr_pct = 0.0

        # Daily returns for Sharpe
        sharpe = self._compute_sharpe(nav_series)

        # Max drawdown
        max_dd_pct = self._compute_max_drawdown(nav_series)

        # Calmar
        calmar = (cagr_pct / abs(max_dd_pct)) if max_dd_pct < 0 else None

        # Trade-level stats (SELL trades only)
        sell_trades = [t for t in all_trades if t.side == "SELL" and t.pnl is not None]
        buy_trades = [t for t in all_trades if t.side == "BUY"]

        total_trades = len(sell_trades)
        winning = [t for t in sell_trades if (t.pnl or 0) > 0]
        losing = [t for t in sell_trades if (t.pnl or 0) <= 0]
        winning_count = len(winning)
        losing_count = len(losing)
        win_rate_pct = (winning_count / total_trades * 100) if total_trades > 0 else 0.0

        gross_profit = sum(t.pnl for t in winning if t.pnl)
        gross_loss = abs(sum(t.pnl for t in losing if t.pnl))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

        avg_win_pct = (
            sum(t.pnl_pct for t in winning if t.pnl_pct is not None) / winning_count
            if winning_count > 0
            else None
        )
        avg_loss_pct = (
            sum(t.pnl_pct for t in losing if t.pnl_pct is not None) / losing_count
            if losing_count > 0
            else None
        )

        wr = win_rate_pct / 100
        if avg_win_pct is not None and avg_loss_pct is not None:
            expectancy = (wr * avg_win_pct) - ((1 - wr) * abs(avg_loss_pct))
        else:
            expectancy = None

        avg_holding = (
            sum(t.holding_days for t in sell_trades if t.holding_days is not None)
            / total_trades
            if total_trades > 0
            else None
        )

        total_sip = sum(s.sip_contributed for s in self.snapshots)

        # Regime breakdown
        regime_breakdown: dict[str, dict] = {}
        for t in sell_trades:
            lbl = t.regime_label or "UNKNOWN"
            if lbl not in regime_breakdown:
                regime_breakdown[lbl] = {"trades": 0, "pnl": 0.0}
            regime_breakdown[lbl]["trades"] += 1
            regime_breakdown[lbl]["pnl"] += t.pnl or 0.0

        # Strategy breakdown
        strategy_breakdown: dict[str, dict] = {}
        for t in sell_trades:
            s = t.strategy_name
            if s not in strategy_breakdown:
                strategy_breakdown[s] = {"trades": 0, "pnl": 0.0}
            strategy_breakdown[s]["trades"] += 1
            strategy_breakdown[s]["pnl"] += t.pnl or 0.0

        return ReplayMetrics(
            initial_nav=initial_nav,
            final_nav=final_nav,
            total_return_pct=total_return_pct,
            cagr_pct=cagr_pct,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd_pct,
            calmar_ratio=calmar,
            total_trades=total_trades,
            winning_trades=winning_count,
            losing_trades=losing_count,
            win_rate_pct=win_rate_pct,
            profit_factor=profit_factor,
            expectancy=expectancy,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            avg_holding_days=avg_holding,
            total_buys=len(buy_trades),
            total_exits=total_trades,
            total_sip_contributed=total_sip,
            regime_breakdown=regime_breakdown,
            strategy_breakdown=strategy_breakdown,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_sharpe(nav_series: list[float]) -> float | None:
        if len(nav_series) < 2:
            return None
        daily_returns = [
            (nav_series[i] / nav_series[i - 1] - 1)
            for i in range(1, len(nav_series))
        ]
        n = len(daily_returns)
        mean_r = sum(daily_returns) / n
        variance = sum((r - mean_r) ** 2 for r in daily_returns) / n
        std_r = math.sqrt(variance)
        if std_r == 0:
            return None
        return (mean_r / std_r) * math.sqrt(252)

    @staticmethod
    def _compute_max_drawdown(nav_series: list[float]) -> float:
        if len(nav_series) < 2:
            return 0.0
        peak = nav_series[0]
        max_dd = 0.0
        for nav in nav_series:
            if nav > peak:
                peak = nav
            dd = (nav - peak) / peak if peak > 0 else 0.0
            if dd < max_dd:
                max_dd = dd
        return max_dd * 100  # as percentage
