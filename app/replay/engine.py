"""Replay Engine — main orchestrator for the Replay Simulation Framework."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy import text

from app.db.session import get_session_factory
from app.recommendation.regime_edge_engine import RCEEConfig
from app.replay.config.experiment_config import ReplayExperimentConfig
from app.replay.day_processor import ReplayDayProcessor
from app.replay.metrics_collector import ReplayMetricsCollector
from app.replay.models import ReplayMetrics, ReplayTrade
from app.replay.pitm_rcee import PointInTimeRCEECache
from app.replay.portfolio_manager import ReplayPortfolioManager
from app.replay.report_generator import ReplayReportGenerator

logger = logging.getLogger(__name__)


@dataclass
class ReplayResult:
    """Final output of a complete replay simulation."""

    config: ReplayExperimentConfig
    metrics: ReplayMetrics
    snapshots: list  # list[ReplayDailySnapshot]
    all_trades: list[ReplayTrade]
    output_dir: Path | None = None
    days_processed: int = 0
    days_skipped: int = 0


class ReplayEngine:
    """Orchestrates a full replay simulation from config to metrics + reports."""

    def __init__(self, verbose: bool = False) -> None:
        self._verbose = verbose

    def run(self, config: ReplayExperimentConfig) -> ReplayResult:
        """Execute full replay simulation.

        No DB writes. All state is in-memory. Reports written to disk only.
        """
        logger.info(
            "Starting replay: %s [%s → %s] mode=%s",
            config.experiment_id,
            config.start_date,
            config.end_date,
            config.mode,
        )

        SessionFactory = get_session_factory()
        portfolio = ReplayPortfolioManager(config)
        collector = ReplayMetricsCollector()
        day_processor = ReplayDayProcessor()

        days_processed = 0
        days_skipped = 0
        prev_snap_date: date | None = None

        with SessionFactory() as db:
            trading_days = self._resolve_trading_days(db, config)

            if not trading_days:
                logger.warning("No trading days found for %s → %s", config.start_date, config.end_date)
                metrics = collector.compute_final_metrics(config.start_date, config.end_date)
                return ReplayResult(
                    config=config,
                    metrics=metrics,
                    snapshots=collector.snapshots,
                    all_trades=[],
                )

            logger.info("Trading days resolved: %d", len(trading_days))

            # Build point-in-time RCEE cache — eliminates lookahead bias
            # Each replay day uses only IC evidence from as_of_date <= day - 30
            pitm_cache = PointInTimeRCEECache.build(
                db=db,
                trading_days=trading_days,
                strategies=config.strategies,
                start_date=config.start_date,
                end_date=config.end_date,
                rcee_config=RCEEConfig(),
            )

            for i, day in enumerate(trading_days):
                # Resolve context (checks for data availability)
                context = ReplayDayProcessor.resolve_context(
                    db=db,
                    as_of_date=day,
                    strategies=config.strategies,
                    trading_day_index=i,
                    prev_month_first_day=prev_snap_date,
                )

                if context is None:
                    logger.debug("No data for %s — skipping", day)
                    days_skipped += 1
                    continue

                # SIP contribution
                sip_today = 0.0
                if (
                    context.is_sip_day
                    and config.capital.monthly_contribution > 0
                    and i > 0  # skip SIP on very first day (initial_cash already set)
                ):
                    portfolio.add_sip(config.capital.monthly_contribution, day)
                    sip_today = config.capital.monthly_contribution

                # Process day: exits → entries → mark-to-market
                entries, exits = day_processor.process_day(
                    context=context,
                    db=db,
                    config=config,
                    portfolio=portfolio,
                    pitm_cache=pitm_cache,
                )

                # Snapshot
                snap = portfolio.snapshot(
                    as_of_date=day,
                    regime_label=context.regime_label,
                    buys_today=len(entries),
                    exits_today=len(exits),
                    sip_today=sip_today,
                )
                collector.record_day(snap)
                prev_snap_date = day
                days_processed += 1

                if self._verbose or (i % 50 == 0):
                    logger.info(
                        "[%d/%d] %s | NAV=%.0f | pos=%d | buys=%d | exits=%d | regime=%s",
                        i + 1,
                        len(trading_days),
                        day,
                        snap.nav,
                        snap.active_positions,
                        len(entries),
                        len(exits),
                        context.regime_label,
                    )

        # Sync all trades to collector
        collector.all_trades = portfolio.all_trades

        # Compute metrics
        metrics = collector.compute_final_metrics(config.start_date, config.end_date)

        logger.info(
            "Replay complete: %s | CAGR=%.2f%% | Sharpe=%.2f | MaxDD=%.2f%%",
            config.experiment_id,
            metrics.cagr_pct,
            metrics.sharpe_ratio if metrics.sharpe_ratio else 0.0,
            metrics.max_drawdown_pct,
        )

        # Generate reports
        output_dir: Path | None = None
        try:
            generator = ReplayReportGenerator(config)
            output_dir = generator.generate(collector, metrics)
            logger.info("Reports written to %s", output_dir)
        except Exception:
            logger.exception("Report generation failed — metrics still valid")

        return ReplayResult(
            config=config,
            metrics=metrics,
            snapshots=collector.snapshots,
            all_trades=portfolio.all_trades,
            output_dir=output_dir,
            days_processed=days_processed,
            days_skipped=days_skipped,
        )

    def _resolve_trading_days(
        self,
        db,
        config: ReplayExperimentConfig,
    ) -> list[date]:
        """Resolve all trading days in the experiment window from DB.

        Uses existing ranking_run dates as the trading calendar proxy.
        Falls back to TradingCalendar if available.
        """
        rows = db.execute(
            text(
                """
                SELECT DISTINCT as_of_date
                FROM ranking_runs
                WHERE as_of_date >= :start
                  AND as_of_date <= :end
                  AND strategy_name = ANY(:strategies)
                  AND status = 'completed'
                ORDER BY as_of_date
                """
            ),
            {
                "start": config.start_date,
                "end": config.end_date,
                "strategies": config.strategies,
            },
        ).fetchall()

        days = [row.as_of_date for row in rows]
        logger.debug("Resolved %d trading days from DB (ranking_runs)", len(days))
        return days
