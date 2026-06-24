"""Replay Day Processor — simulates one trading day end-to-end.

Design:
- Reads from DB (read-only, as_of_date gated)
- Reuses production exit triggers and position sizer
- No DB writes
"""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.portfolio.exit_monitor.triggers import (
    TriggerResult,
    check_alpha_decay,
    check_rank_drop,
    check_regime_change,
    check_time_stop,
)
from app.portfolio.position_sizing import SizingInputs, size_position
from app.recommendation.regime_edge_engine import EdgeState
from app.replay.config.experiment_config import ExperimentMode, ReplayExperimentConfig
from app.replay.models import ReplayContext, ReplayDailySnapshot, ReplayPosition, ReplayTrade
from app.replay.pitm_rcee import PointInTimeRCEECache
from app.replay.portfolio_manager import ReplayPortfolioManager

logger = logging.getLogger(__name__)

# Regime label → posture mapping
_REGIME_POSTURE: dict[str, str] = {
    "BULL_LOW_VOL": "risk_on",
    "BULL_HIGH_VOL": "neutral",
    "BEAR_LOW_VOL": "defensive",
    "BEAR_HIGH_VOL": "defensive",
}


def derive_regime_posture(regime_label: str | None) -> str:
    if regime_label is None:
        return "neutral"
    return _REGIME_POSTURE.get(regime_label, "neutral")


class _BuyRec:
    """Lightweight BUY recommendation row."""

    __slots__ = ("recommendation_result_id", "stock_id", "symbol", "rank",
                 "conviction_band", "conviction_score", "strategy_name")

    def __init__(
        self,
        recommendation_result_id: UUID,
        stock_id: UUID,
        symbol: str,
        rank: int,
        conviction_band: str,
        conviction_score: int,
        strategy_name: str,
    ) -> None:
        self.recommendation_result_id = recommendation_result_id
        self.stock_id = stock_id
        self.symbol = symbol
        self.rank = rank
        self.conviction_band = conviction_band
        self.conviction_score = conviction_score
        self.strategy_name = strategy_name


class ReplayDayProcessor:
    """Processes one trading day in the replay simulation."""

    def __init__(self) -> None:
        self._hitl_buffer: list[_BuyRec] = []

    def process_day(
        self,
        context: ReplayContext,
        db: Session,
        config: ReplayExperimentConfig,
        portfolio: ReplayPortfolioManager,
        pitm_cache: PointInTimeRCEECache | None = None,
    ) -> tuple[list[ReplayTrade], list[ReplayTrade]]:
        """Process one trading day.

        Returns:
            (entries, exits) — lists of trades executed today
        """
        as_of_date = context.as_of_date
        mode = ExperimentMode(config.mode)

        # --- 1. Load close prices for all stocks active today ---
        price_map = self._load_price_map(db, as_of_date)

        # --- 2. EXIT PHASE (process before entries to free up slots) ---
        exits: list[ReplayTrade] = []
        for pos in list(portfolio.open_positions):
            current_rank = self._get_current_rank(db, pos.stock_id, as_of_date, config.strategies)
            cum_alpha = pos.unrealized_pct  # use unrealized % as proxy for alpha

            triggers = [
                check_rank_drop(current_rank, pos.rank_at_entry),
                # Alpha decay: only fire after min 5 days held AND loss exceeds -5%
                # (production trigger uses 0% threshold which is too sensitive for replay)
                check_alpha_decay(cum_alpha, pos.holding_days,
                                  decay_threshold_day=15, decay_min_alpha=-5.0),
                # Regime change: only fire when regime posture CHANGED from entry posture
                # (not just "is currently defensive" — that would exit everything on day 1 of bear)
                check_regime_change(context.regime_posture, derive_regime_posture(pos.regime_at_entry))
                if context.regime_posture != derive_regime_posture(pos.regime_at_entry)
                else TriggerResult(False, "EXIT_REGIME", {}),
                check_time_stop(pos.holding_days),
            ]

            fired = [t for t in triggers if t.fired]
            if fired:
                exit_price = price_map.get(pos.stock_id)
                if exit_price is None:
                    logger.warning("No price for %s on exit day %s — holding", pos.symbol, as_of_date)
                    continue
                # Most-severe trigger wins the label (e.g. stop-loss over rank-drop on
                # a gap-down day) — see _primary_exit_reason in paper_trade_service.
                from app.services.paper_trade_service import _primary_exit_reason
                exit_reason = _primary_exit_reason([t.trigger_code for t in fired])
                trade = portfolio.close_position(
                    pos.stock_id,
                    exit_date=as_of_date,
                    exit_price=exit_price,
                    exit_reason=exit_reason,
                    slippage_bps=config.execution.slippage_bps,
                    fee=config.execution.fee_per_leg,
                )
                exits.append(trade)

        # --- 3. Load BUY recommendations (mode-dependent) ---
        if mode == ExperimentMode.HITL_SIMULATION:
            # Use previous day's buffer; reload today's for tomorrow
            buy_recs = self._hitl_buffer
            self._hitl_buffer = self._load_buy_recs(db, as_of_date, config.strategies)
        else:
            buy_recs = self._load_buy_recs(db, as_of_date, config.strategies)

            if mode == ExperimentMode.AUTONOMOUS_NO_RCEE:
                # Only allow recs not blocked by regime (exclude RCEE-blocked)
                buy_recs = [r for r in buy_recs if r.conviction_band not in ("BLOCKED",)]

        # --- Point-in-time RCEE gate (anti-lookahead fix) ---
        # The stored recommendation_results used full-history strategy_regime_performance.
        # Re-gate using only data available as of this replay day (as_of_date - 30 days).
        if pitm_cache is not None and mode not in (
            ExperimentMode.AUTONOMOUS_FORCE_EDGE,
            ExperimentMode.AUTONOMOUS_NO_RCEE,
        ):
            filtered_recs = []
            for rec in buy_recs:
                pit_edge = pitm_cache.get_edge_state(
                    as_of_date, rec.strategy_name, context.regime_label
                )
                if pit_edge in (EdgeState.EDGE_PRESENT, EdgeState.EDGE_WEAK):
                    filtered_recs.append(rec)
                else:
                    logger.debug(
                        "PIT-RCEE blocked %s on %s: %s edge=%s",
                        rec.symbol, as_of_date, rec.strategy_name, pit_edge.value
                    )
            buy_recs = filtered_recs

        # --- 4. ENTRY PHASE ---
        entries: list[ReplayTrade] = []
        buys_today = 0

        for rec in sorted(buy_recs, key=lambda r: r.rank):
            if buys_today >= config.portfolio.max_buy_slots:
                break
            if not portfolio.can_open_position(config):
                break
            if rec.stock_id in portfolio.held_stock_ids:
                continue

            fill_price_raw = price_map.get(rec.stock_id)
            if fill_price_raw is None:
                logger.debug("No price for %s on %s — skipping", rec.symbol, as_of_date)
                continue

            # Apply BUY slippage (worse fill = higher price)
            slippage_amt = fill_price_raw * (config.execution.slippage_bps / 10_000)
            fill_price = fill_price_raw + slippage_amt

            slot_budget = portfolio.get_slot_budget(config.portfolio.max_positions)
            if slot_budget <= 0:
                break

            sizing = size_position(
                SizingInputs(
                    conviction_band=rec.conviction_band,
                    slot_budget=slot_budget,
                    last_price=fill_price,
                )
            )

            if sizing.quantity <= 0:
                continue

            cost = fill_price * sizing.quantity + config.execution.fee_per_leg
            if cost > portfolio.get_available_cash():
                logger.debug("Insufficient cash for %s (need %.0f)", rec.symbol, cost)
                continue

            pos = ReplayPosition(
                stock_id=rec.stock_id,
                symbol=rec.symbol,
                strategy_name=rec.strategy_name,
                entry_date=as_of_date,
                entry_price=fill_price,
                quantity=sizing.quantity,
                conviction_band=rec.conviction_band,
                regime_at_entry=context.regime_label,
                recommendation_result_id=rec.recommendation_result_id,
                rank_at_entry=rec.rank,
                holding_days=0,
                current_price=fill_price,
            )

            if portfolio.open_position(pos):
                notional = fill_price * sizing.quantity
                trade = ReplayTrade(
                    stock_id=rec.stock_id,
                    symbol=rec.symbol,
                    strategy_name=rec.strategy_name,
                    side="BUY",
                    trade_date=as_of_date,
                    price=fill_price,
                    quantity=sizing.quantity,
                    notional=notional,
                    fee=config.execution.fee_per_leg,
                    slippage=slippage_amt * sizing.quantity,
                    conviction_band=rec.conviction_band,
                    regime_label=context.regime_label,
                )
                portfolio.record_buy_trade(trade)
                entries.append(trade)
                buys_today += 1

        # --- 5. Mark to market ---
        portfolio.mark_to_market(price_map, as_of_date)

        return entries, exits

    # ------------------------------------------------------------------
    # DB queries (all as_of_date gated — no future leakage)
    # ------------------------------------------------------------------

    def _load_price_map(self, db: Session, as_of_date: date) -> dict[UUID, float]:
        """Load close prices for all stocks on as_of_date."""
        rows = db.execute(
            text(
                """
                SELECT md.stock_id, md.close
                FROM market_data md
                WHERE md.date = :d
                """
            ),
            {"d": as_of_date},
        ).fetchall()
        return {row.stock_id: float(row.close) for row in rows}

    def _get_current_rank(
        self,
        db: Session,
        stock_id: UUID,
        as_of_date: date,
        strategies: list[str],
    ) -> int | None:
        """Get the stock's current rank from the most recent ranking run on as_of_date."""
        row = db.execute(
            text(
                """
                SELECT rr.rank
                FROM ranking_results rr
                JOIN ranking_runs rnk ON rnk.id = rr.ranking_run_id
                WHERE rnk.as_of_date = :d
                  AND rnk.strategy_name = ANY(:strategies)
                  AND rr.stock_id = :stock_id
                ORDER BY rr.rank
                LIMIT 1
                """
            ),
            {"d": as_of_date, "strategies": strategies, "stock_id": str(stock_id)},
        ).fetchone()
        return row.rank if row else None

    def _load_buy_recs(
        self,
        db: Session,
        as_of_date: date,
        strategies: list[str],
    ) -> list[_BuyRec]:
        """Load BUY recommendations for as_of_date from pre-computed pipeline data."""
        rows = db.execute(
            text(
                """
                SELECT
                    res.id                  AS recommendation_result_id,
                    res.stock_id,
                    s.symbol,
                    res.rank,
                    res.conviction_band,
                    res.conviction_score,
                    rec.strategy_name
                FROM recommendation_results res
                JOIN recommendation_runs rec ON rec.id = res.recommendation_run_id
                JOIN ranking_runs rnk ON rnk.id = rec.ranking_run_id
                JOIN stocks s ON s.id = res.stock_id
                WHERE rnk.as_of_date = :d
                  AND rec.strategy_name = ANY(:strategies)
                  AND res.action = 'BUY'
                  AND rec.status = 'completed'
                ORDER BY res.rank ASC NULLS LAST
                """
            ),
            {"d": as_of_date, "strategies": strategies},
        ).fetchall()

        return [
            _BuyRec(
                recommendation_result_id=row.recommendation_result_id,
                stock_id=row.stock_id,
                symbol=row.symbol,
                rank=row.rank or 999,
                conviction_band=row.conviction_band,
                conviction_score=row.conviction_score or 0,
                strategy_name=row.strategy_name,
            )
            for row in rows
        ]

    @staticmethod
    def resolve_context(
        db: Session,
        as_of_date: date,
        strategies: list[str],
        trading_day_index: int,
        prev_month_first_day: date | None,
    ) -> ReplayContext | None:
        """Build a ReplayContext for as_of_date. Returns None if no data available."""
        row = db.execute(
            text(
                """
                SELECT regime_label
                FROM ranking_runs
                WHERE as_of_date = :d
                  AND strategy_name = ANY(:strategies)
                  AND status = 'completed'
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"d": as_of_date, "strategies": strategies},
        ).fetchone()

        if row is None:
            return None

        regime_label: str | None = row.regime_label
        regime_posture = derive_regime_posture(regime_label)

        # Determine if this is the first trading day of the month
        is_first_td_of_month = (
            prev_month_first_day is None
            or as_of_date.month != prev_month_first_day.month
        )

        return ReplayContext(
            as_of_date=as_of_date,
            regime_label=regime_label or "UNKNOWN",
            regime_posture=regime_posture,
            trading_day_index=trading_day_index,
            is_first_trading_day_of_month=is_first_td_of_month,
            is_sip_day=is_first_td_of_month,  # default: SIP on first trading day
        )
