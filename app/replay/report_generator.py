"""Replay Report Generator — produces markdown reports to disk."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from app.replay.config.experiment_config import ReplayExperimentConfig
from app.replay.metrics_collector import ReplayMetricsCollector
from app.replay.models import ReplayMetrics


class ReplayReportGenerator:
    """Generates markdown reports for a completed replay experiment."""

    def __init__(self, config: ReplayExperimentConfig) -> None:
        self._config = config

    def generate(
        self,
        collector: ReplayMetricsCollector,
        metrics: ReplayMetrics,
    ) -> Path:
        """Generate all configured reports. Returns the output directory."""
        out_dir = (
            Path(self._config.outputs.output_dir) / self._config.experiment_id
        )
        out_dir.mkdir(parents=True, exist_ok=True)

        if self._config.outputs.generate_nav_curve:
            self._write_nav_curve(collector, metrics, out_dir)

        if self._config.outputs.generate_trade_report:
            self._write_trade_report(collector, metrics, out_dir)

        if self._config.outputs.generate_regime_report:
            self._write_regime_report(metrics, out_dir)

        if self._config.outputs.generate_strategy_report:
            self._write_strategy_report(metrics, out_dir)

        self._write_summary(metrics, out_dir)
        return out_dir

    # ------------------------------------------------------------------
    # Individual report writers
    # ------------------------------------------------------------------

    def _write_nav_curve(
        self,
        collector: ReplayMetricsCollector,
        metrics: ReplayMetrics,
        out_dir: Path,
    ) -> None:
        cfg = self._config
        lines = [
            f"# NAV Curve — {cfg.name}",
            f"Experiment: `{cfg.experiment_id}` | Mode: `{cfg.mode}`",
            f"Period: {cfg.start_date} → {cfg.end_date}",
            "",
            "## Monthly NAV Snapshots",
            "",
            "| Date | NAV | Cash | Market Value | Positions | Regime |",
            "|------|-----|------|--------------|-----------|--------|",
        ]

        # Monthly snapshots: keep last snapshot per month
        monthly: dict[tuple[int, int], object] = {}
        for snap in collector.snapshots:
            key = (snap.date.year, snap.date.month)
            monthly[key] = snap

        for (yr, mo), snap in sorted(monthly.items()):
            lines.append(
                f"| {snap.date} | {snap.nav:,.0f} | {snap.cash:,.0f} | "
                f"{snap.market_value:,.0f} | {snap.active_positions} | {snap.regime_label} |"
            )

        lines += [
            "",
            "## Summary",
            "",
            f"- Initial NAV: {metrics.initial_nav:,.0f}",
            f"- Final NAV:   {metrics.final_nav:,.0f}",
            f"- Total Return: {metrics.total_return_pct:.2f}%",
            f"- CAGR: {metrics.cagr_pct:.2f}%",
            f"- Sharpe: {metrics.sharpe_ratio:.2f}" if metrics.sharpe_ratio else "- Sharpe: n/a",
            f"- Max Drawdown: {metrics.max_drawdown_pct:.2f}%",
        ]

        (out_dir / "nav_curve.md").write_text("\n".join(lines))

    def _write_trade_report(
        self,
        collector: ReplayMetricsCollector,
        metrics: ReplayMetrics,
        out_dir: Path,
    ) -> None:
        cfg = self._config
        sell_trades = [t for t in collector.all_trades if t.side == "SELL"]

        lines = [
            f"# Trade Report — {cfg.name}",
            f"Experiment: `{cfg.experiment_id}`",
            "",
            f"Total closed trades: {metrics.total_trades}",
            f"Win rate: {metrics.win_rate_pct:.1f}%",
            f"Profit factor: {metrics.profit_factor:.2f}" if metrics.profit_factor else "Profit factor: n/a",
            "",
            "## Closed Trades",
            "",
            "| Symbol | Strategy | Entry | Exit | P&L | P&L% | Hold | Exit Reason | Conviction |",
            "|--------|----------|-------|------|-----|------|------|-------------|------------|",
        ]

        for t in sorted(sell_trades, key=lambda x: x.trade_date):
            lines.append(
                f"| {t.symbol} | {t.strategy_name} | — | {t.trade_date} | "
                f"{t.pnl:+,.0f} | {t.pnl_pct:+.1f}% | {t.holding_days}d | "
                f"{t.exit_reason} | {t.conviction_band} |"
            )

        (out_dir / "trade_report.md").write_text("\n".join(lines))

    def _write_regime_report(self, metrics: ReplayMetrics, out_dir: Path) -> None:
        cfg = self._config
        lines = [
            f"# Regime Breakdown — {cfg.name}",
            "",
            "| Regime | Trades | Total P&L | Avg P&L/Trade |",
            "|--------|--------|-----------|---------------|",
        ]
        for regime, data in sorted(metrics.regime_breakdown.items()):
            trades = data["trades"]
            pnl = data["pnl"]
            avg = pnl / trades if trades > 0 else 0
            lines.append(f"| {regime} | {trades} | {pnl:+,.0f} | {avg:+,.0f} |")

        (out_dir / "regime_report.md").write_text("\n".join(lines))

    def _write_strategy_report(self, metrics: ReplayMetrics, out_dir: Path) -> None:
        cfg = self._config
        lines = [
            f"# Strategy Breakdown — {cfg.name}",
            "",
            "| Strategy | Trades | Total P&L | Avg P&L/Trade |",
            "|----------|--------|-----------|---------------|",
        ]
        for strategy, data in sorted(metrics.strategy_breakdown.items()):
            trades = data["trades"]
            pnl = data["pnl"]
            avg = pnl / trades if trades > 0 else 0
            lines.append(f"| {strategy} | {trades} | {pnl:+,.0f} | {avg:+,.0f} |")

        (out_dir / "strategy_report.md").write_text("\n".join(lines))

    def _write_summary(self, metrics: ReplayMetrics, out_dir: Path) -> None:
        cfg = self._config
        lines = [
            f"# Experiment Summary — {cfg.name}",
            "",
            f"**ID**: `{cfg.experiment_id}`",
            f"**Mode**: `{cfg.mode}`",
            f"**Period**: {cfg.start_date} → {cfg.end_date}",
            f"**Strategies**: {', '.join(cfg.strategies)}",
            "",
            "## Performance Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Initial NAV | {metrics.initial_nav:,.0f} |",
            f"| Final NAV | {metrics.final_nav:,.0f} |",
            f"| Total Return | {metrics.total_return_pct:.2f}% |",
            f"| CAGR | {metrics.cagr_pct:.2f}% |",
            f"| Sharpe Ratio | {metrics.sharpe_ratio:.2f} |" if metrics.sharpe_ratio else "| Sharpe Ratio | n/a |",
            f"| Max Drawdown | {metrics.max_drawdown_pct:.2f}% |",
            f"| Calmar Ratio | {metrics.calmar_ratio:.2f} |" if metrics.calmar_ratio else "| Calmar Ratio | n/a |",
            "",
            "## Trade Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Closed Trades | {metrics.total_trades} |",
            f"| Win Rate | {metrics.win_rate_pct:.1f}% |",
            f"| Profit Factor | {metrics.profit_factor:.2f} |" if metrics.profit_factor else "| Profit Factor | n/a |",
            f"| Expectancy | {metrics.expectancy:.2f}% |" if metrics.expectancy else "| Expectancy | n/a |",
            f"| Avg Win | {metrics.avg_win_pct:.2f}% |" if metrics.avg_win_pct else "| Avg Win | n/a |",
            f"| Avg Loss | {metrics.avg_loss_pct:.2f}% |" if metrics.avg_loss_pct else "| Avg Loss | n/a |",
            f"| Avg Holding Days | {metrics.avg_holding_days:.1f} |" if metrics.avg_holding_days else "| Avg Holding Days | n/a |",
            f"| Total Buys | {metrics.total_buys} |",
            f"| Total SIP Contributed | {metrics.total_sip_contributed:,.0f} |",
        ]

        (out_dir / "summary.md").write_text("\n".join(lines))
