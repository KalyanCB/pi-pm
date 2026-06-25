"""Exit Monitor Service — T2 daily swing monitor (ADR-033).

Evaluates OPEN positions post-close for swing triggers:
  EXIT_RANK_DROP, EXIT_ALPHA_DECAY, EXIT_REGIME, EXIT_TIME,
  EXIT_STOP_LOSS (EOD close), EXIT_TRAILING_STOP, concentration, liquidity.

Generates ExitRecommendation rows with monitor_tier='DAILY'.
Never auto-executes. Human confirms (or paper pilot in HITL_ENABLED=false mode).

ADR-033 change: stop thresholds now sourced from Settings
(advisory_stop_pct / critical_stop_pct) instead of hardcoded -8%.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import DEFAULT_BENCHMARK_SYMBOL
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.models.portfolio_analytics import ExitRecommendation
from app.models.portfolio_position import PortfolioConfig, PortfolioPosition
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.portfolio.exit_monitor.triggers import (
    check_alpha_decay,
    check_concentration,
    check_liquidity,
    check_rank_drop,
    check_regime_change,
    check_stop_loss,
    check_time_stop,
    check_trailing_stop,
)
from app.portfolio.regime_stops import resolve_stop_pcts


class ExitMonitorService:
    def __init__(
        self,
        db: Session,
        *,
        market_data_repo: MarketDataRepository | None = None,
        ranking_run_repo: RankingRunRepository | None = None,
        regime_repo: RegimeAnalyticsRepository | None = None,
    ) -> None:
        self.db = db
        self.market_data_repo = market_data_repo or MarketDataRepository(db)
        self.ranking_run_repo = ranking_run_repo or RankingRunRepository(db)
        self.regime_repo = regime_repo or RegimeAnalyticsRepository(db)

    def run(self, as_of_date: date | None = None) -> list[ExitRecommendation]:
        """Evaluate all OPEN positions and generate T2 DAILY ExitRecommendation rows.

        ADR-033: skip if a DAILY PENDING row already exists for this position today.
        All market data and rank lookups are batched upfront — one query per data
        type across all positions, not one query per position.
        """
        as_of = as_of_date or date.today()
        cfg = self._get_config()
        positions = self._get_open_positions()
        regime_posture = self._resolve_regime_posture(as_of)

        if not positions:
            return []

        # ── Batch prefetch: prices for all positions in one query ─────────────
        from app.models.market_data import MarketData as MarketDataModel
        stock_ids = [pos.stock_id for pos in positions]
        price_rows = self.db.execute(
            select(
                MarketDataModel.stock_id,
                MarketDataModel.close,
                MarketDataModel.low,
                MarketDataModel.volume,
            )
            .where(
                MarketDataModel.stock_id.in_(stock_ids),
                MarketDataModel.date <= as_of,
            )
            .distinct(MarketDataModel.stock_id)
            .order_by(MarketDataModel.stock_id, MarketDataModel.date.desc())
        ).all()
        # price_map: stock_id → (close, day_low, volume)
        price_map = {
            row.stock_id: (
                float(row.close),
                float(row.low) if row.low else None,
                float(row.volume) if row.volume else None,
            )
            for row in price_rows
        }

        # ── Batch prefetch: latest ranking run + all ranks in one query ───────
        latest_run = self.db.scalar(
            select(RankingRun)
            .where(RankingRun.status == "completed", RankingRun.as_of_date <= as_of)
            .order_by(RankingRun.as_of_date.desc(), RankingRun.completed_at.desc())
            .limit(1)
        )
        rank_map: dict = {}
        if latest_run:
            rank_rows = self.db.execute(
                select(RankingResult.stock_id, RankingResult.rank)
                .where(
                    RankingResult.ranking_run_id == latest_run.id,
                    RankingResult.stock_id.in_(stock_ids),
                )
            ).all()
            rank_map = {row.stock_id: row.rank for row in rank_rows}

        # ── Batch prefetch: per-stock own-trend (hybrid regime exit, flag-gated) ──
        # own_trend_intact = last close above its OWN fast & slow SMA. Computed in
        # one bounded window query (≤ slow bars × positions). Skipped entirely when
        # the flag is off so default behaviour pays no query cost.
        settings = get_settings()
        trend_map: dict = {}
        if settings.regime_exit_per_stock_trend_enabled:
            fast = settings.regime_exit_trend_sma_fast
            slow = settings.regime_exit_trend_sma_slow
            ranked = (
                select(
                    MarketDataModel.stock_id,
                    MarketDataModel.close,
                    func.row_number()
                    .over(
                        partition_by=MarketDataModel.stock_id,
                        order_by=MarketDataModel.date.desc(),
                    )
                    .label("rn"),
                )
                .where(
                    MarketDataModel.stock_id.in_(stock_ids),
                    MarketDataModel.date <= as_of,
                )
                .subquery()
            )
            trend_rows = self.db.execute(
                select(
                    ranked.c.stock_id,
                    func.avg(ranked.c.close).filter(ranked.c.rn <= fast).label("sma_fast"),
                    func.avg(ranked.c.close).filter(ranked.c.rn <= slow).label("sma_slow"),
                    func.max(ranked.c.close).filter(ranked.c.rn == 1).label("last_close"),
                    func.count().filter(ranked.c.rn <= slow).label("n"),
                )
                .where(ranked.c.rn <= slow)
                .group_by(ranked.c.stock_id)
            ).all()
            for r in trend_rows:
                if r.n and r.n >= slow and r.last_close and r.sma_fast and r.sma_slow:
                    trend_map[r.stock_id] = (
                        float(r.last_close) > float(r.sma_fast)
                        and float(r.last_close) > float(r.sma_slow)
                    )

        results: list[ExitRecommendation] = []

        for pos in positions:
            # Gold-rotation sleeve is managed entirely by _gold_rotation (buy once
            # in bear, hold, sell on regime flip). It must NOT be evaluated by the
            # equity exit monitor — otherwise EXIT_REGIME liquidates it every bear
            # day and _gold_rotation re-buys it, churning the sleeve.
            if getattr(pos, "strategy_name", None) == "gold_rotation":
                continue
            # Skip if a DAILY PENDING exit already exists for today.
            existing = self.db.scalar(
                select(ExitRecommendation).where(
                    ExitRecommendation.portfolio_position_id == pos.id,
                    ExitRecommendation.as_of_date == as_of,
                    ExitRecommendation.status == "PENDING",
                    ExitRecommendation.monitor_tier == "DAILY",
                )
            )
            if existing:
                results.append(existing)
                continue

            context = self._build_position_context(
                pos, as_of, price_map=price_map, rank_map=rank_map, trend_map=trend_map
            )
            fired_triggers = self._evaluate_triggers(pos, context, cfg, regime_posture, as_of)

            if not fired_triggers:
                continue

            trigger_codes = [t.trigger_code for t in fired_triggers]
            trigger_details = {t.trigger_code: t.details for t in fired_triggers}
            urgency = max(
                fired_triggers, key=lambda t: ["LOW", "NORMAL", "HIGH", "CRITICAL"].index(t.urgency)
            ).urgency

            unrealized_pct = None
            if pos.avg_cost and context.get("last_price"):
                unrealized_pct = (
                    (context["last_price"] - float(pos.avg_cost)) / float(pos.avg_cost) * 100
                )

            exit_rec = ExitRecommendation(
                portfolio_position_id=pos.id,
                stock_id=pos.stock_id,
                as_of_date=as_of,
                status="PENDING",
                triggers=trigger_codes,
                trigger_details=trigger_details,
                current_rank=context.get("current_rank"),
                days_held=context.get("days_held"),
                unrealized_pnl_pct=round(unrealized_pct, 4) if unrealized_pct is not None else None,
                urgency=urgency,
                monitor_tier="DAILY",   # ADR-033: tag tier for audit
            )
            self.db.add(exit_rec)
            results.append(exit_rec)

        self.db.flush()
        return results

    def get_pending(self, as_of_date: date | None = None) -> list[ExitRecommendation]:
        q = select(ExitRecommendation).where(ExitRecommendation.status == "PENDING")
        if as_of_date:
            q = q.where(ExitRecommendation.as_of_date == as_of_date)
        return list(self.db.scalars(q.order_by(ExitRecommendation.urgency.desc())).all())

    def list_for_date(self, as_of_date: date) -> list[ExitRecommendation]:
        """All exit monitor rows for a day (pending, confirmed, rejected)."""
        return list(
            self.db.scalars(
                select(ExitRecommendation)
                .where(ExitRecommendation.as_of_date == as_of_date)
                .order_by(ExitRecommendation.urgency.desc(), ExitRecommendation.created_at.desc())
            ).all()
        )

    def confirm(self, exit_rec_id: UUID) -> ExitRecommendation:
        rec = self.db.get(ExitRecommendation, exit_rec_id)
        if rec is None:
            raise ValueError(f"ExitRecommendation {exit_rec_id} not found")
        rec.status = "CONFIRMED"
        rec.confirmed_at = datetime.now(UTC)
        self.db.flush()
        return rec

    def reject(self, exit_rec_id: UUID, reason: str | None = None) -> ExitRecommendation:
        rec = self.db.get(ExitRecommendation, exit_rec_id)
        if rec is None:
            raise ValueError(f"ExitRecommendation {exit_rec_id} not found")
        rec.status = "REJECTED"
        rec.rejected_at = datetime.now(UTC)
        rec.rejection_reason = reason
        self.db.flush()
        return rec

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_open_positions(self) -> list[PortfolioPosition]:
        return list(
            self.db.scalars(
                select(PortfolioPosition).where(
                    PortfolioPosition.is_current.is_(True),
                    PortfolioPosition.position_status == "OPEN",
                )
            ).all()
        )

    def _get_config(self) -> PortfolioConfig | None:
        return self.db.scalar(
            select(PortfolioConfig)
            .where(PortfolioConfig.is_active.is_(True))
            .order_by(PortfolioConfig.created_at.desc())
            .limit(1)
        )

    def _resolve_regime_posture(self, as_of: date) -> str:
        try:
            regime = self.regime_repo.get_current(
                benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL, as_of_date=as_of
            )
            if regime is None:
                return "neutral"
            label = (regime.regime_label or "").upper()
            if "BEAR" in label or "HIGH_VOL" in label:
                return "defensive"
            if "BULL" in label and "LOW_VOL" in label:
                return "risk_on"
            return "neutral"
        except Exception:
            return "neutral"

    def _build_position_context(
        self,
        pos: PortfolioPosition,
        as_of: date,
        price_map: dict | None = None,
        rank_map: dict | None = None,
        trend_map: dict | None = None,
    ) -> dict:
        ctx: dict = {}

        # Per-stock own-trend flag (hybrid regime exit). None when the flag is off
        # or insufficient history → check_regime_change falls back to default logic.
        if trend_map:
            ctx["own_trend_intact"] = trend_map.get(pos.stock_id)

        if pos.entry_date:
            ctx["days_held"] = (as_of - pos.entry_date).days

        # Use pre-fetched price map if available, else fall back to single query
        if price_map is not None:
            entry = price_map.get(pos.stock_id)
            if entry:
                ctx["last_price"] = entry[0]
                ctx["day_low"] = entry[1]
                ctx["avg_daily_volume"] = entry[2]
        else:
            latest = self.market_data_repo.get_latest_market_data(pos.stock_id)
            if latest:
                ctx["last_price"] = float(latest.close)
                ctx["day_low"] = float(latest.low) if latest.low else None
                ctx["avg_daily_volume"] = float(latest.volume) if latest.volume else None

        # Use pre-fetched rank map if available, else fall back to single query
        if rank_map is not None:
            ctx["current_rank"] = rank_map.get(pos.stock_id)
        else:
            ctx["current_rank"] = self._get_current_rank(pos.stock_id, as_of)

        if pos.avg_cost and ctx.get("last_price"):
            avg_cost = float(pos.avg_cost)
            close = ctx["last_price"]
            day_low = ctx.get("day_low")
            ctx["unrealized_pnl_pct"] = (close - avg_cost) / avg_cost * 100
            # Intraday stop only fires if day_low breached the stop threshold
            # AND the close also confirms weakness (stock didn't recover by EOD).
            # If close > stop_price the stock recovered — don't exit.
            # We store the day_low-based pnl so _evaluate_triggers can apply
            # the dual-condition check (low breach + close confirmation).
            ctx["intraday_pnl_pct"] = (day_low - avg_cost) / avg_cost * 100 if day_low else ctx["unrealized_pnl_pct"]

        ctx["max_gain_pct"] = self._get_max_gain(pos)

        # P-07: entry_rank for relative deterioration check
        ctx["entry_rank"] = self._get_entry_rank(pos)

        return ctx

    def _get_current_rank(self, stock_id: UUID, as_of: date) -> int | None:
        try:
            latest_run = self.db.scalar(
                select(RankingRun)
                .where(
                    RankingRun.status == "completed",
                    RankingRun.as_of_date <= as_of,
                )
                .order_by(RankingRun.as_of_date.desc(), RankingRun.completed_at.desc())
                .limit(1)
            )
            if latest_run is None:
                return None
            result = self.db.scalar(
                select(RankingResult).where(
                    RankingResult.ranking_run_id == latest_run.id,
                    RankingResult.stock_id == stock_id,
                )
            )
            return result.rank if result else None
        except Exception:
            return None

    def _get_entry_rank(self, pos: PortfolioPosition) -> int | None:
        try:
            if pos.recommendation_result_id is None:
                return None
            from app.models.recommendation import RecommendationResult as _RR
            result = self.db.get(_RR, pos.recommendation_result_id)
            return int(result.rank) if result and result.rank else None
        except Exception:
            return None

    def _get_max_gain(self, pos: PortfolioPosition) -> float | None:
        try:
            if pos.recommendation_result_id is None:
                return None
            from app.models.recommendation import RecommendationOutcome

            outcome = self.db.scalar(
                select(RecommendationOutcome).where(
                    RecommendationOutcome.recommendation_result_id == pos.recommendation_result_id
                )
            )
            return float(outcome.max_gain_pct) if outcome and outcome.max_gain_pct else None
        except Exception:
            return None

    def _evaluate_triggers(
        self,
        pos: PortfolioPosition,
        ctx: dict,
        cfg: PortfolioConfig | None,
        regime_posture: str,
        as_of: date | None = None,
    ) -> list:
        from datetime import timedelta

        settings = get_settings()
        single_cap = float(cfg.single_name_cap_pct * 100) if cfg else 18.0
        days_held = ctx.get("days_held", 0)

        # ADR-037 P-15: suppress analytical exits (rank drop, alpha decay) for
        # first 5 days. 48% of losers recover +14.7% avg within 10 days —
        # premature exits destroy that recovery potential.
        _analytical_exits_suppressed = days_held < 5

        # ADR-037 P-16: 3-day cooldown after EXIT_ALPHA_DECAY to prevent churn.
        # Check if the last closed exit for this position was EXIT_ALPHA_DECAY
        # within the past 3 days.
        _in_alpha_decay_cooldown = False
        if pos.exit_reason == "EXIT_ALPHA_DECAY" and pos.exit_date and as_of:
            cooldown_end = pos.exit_date + timedelta(days=3)
            _in_alpha_decay_cooldown = as_of <= cooldown_end

        # ADR-037 P-17: progressive stop floor tightens as position ages.
        # Day 1-5: -6% (initial stop), Day 6-10: -4%, Day 11-15: breakeven (-0%),
        # Day 16+: breakeven +0.5% (lock in small gain).
        if days_held <= 5:
            _progressive_stop = -6.0
        elif days_held <= 10:
            _progressive_stop = -4.0
        elif days_held <= 15:
            _progressive_stop = 0.0
        else:
            _progressive_stop = 0.5

        # ADR-033: advisory stop from Settings; ADR-035: regime-resolved when the
        # regime_dynamic_stops_enabled flag is on (static otherwise).
        stop_loss, _critical = resolve_stop_pcts(
            self.regime_repo, as_of=as_of, settings=settings
        )
        # P-17: use the tighter of progressive stop vs regime stop (after day 10)
        if days_held > 10:
            stop_loss = max(stop_loss, _progressive_stop)

        trailing = 5.0

        # ── ADR-037 v18 Tier-1: day-5 graduation + runner tier (flag-gated) ──────
        # After the 5-day noise window, tier each surviving position:
        #   winner-track (green AND ranked) → loosen the leash (wide trail, suppress
        #     analytical exits) so winners run to 12-20 days.
        #   loser-track  (red OR rank-dropped) → let analytical exits cut it now.
        #   runner (winner + top-N rank + large gain) → very loose trail, ride for
        #     months (the multibagger capture).
        _grad_suppress_analytical = False
        _is_runner = False
        if settings.graduation_enabled and days_held >= 5:
            _pnl = ctx.get("unrealized_pnl_pct")
            _rank = ctx.get("current_rank")
            _pool = ctx.get("entry_pool_size") or 20
            _green = _pnl is not None and _pnl > 0
            _ranked = _rank is not None and _rank <= _pool
            if _green and _ranked:
                # winner-track: hold it; replace tight analytical exits with a wide trail
                _grad_suppress_analytical = True
                trailing = settings.graduation_winner_trail_pct
                if (settings.runner_tier_enabled
                        and _rank is not None and _rank <= settings.runner_max_rank
                        and (ctx.get("max_gain_pct") or 0) >= settings.runner_min_gain_pct):
                    _is_runner = True
                    trailing = settings.runner_trail_pct  # let the monster ride

        # EOD confirmation: stop only fires if day_low breached the level AND
        # the close also confirms (stock didn't recover by EOD). This prevents
        # intraday dips from killing positions that close back above the stop.
        eod_pnl = ctx.get("unrealized_pnl_pct")
        intraday_pnl = ctx.get("intraday_pnl_pct", eod_pnl)
        stop_pnl = intraday_pnl if (intraday_pnl is not None and eod_pnl is not None and eod_pnl <= stop_loss) else eod_pnl

        results = []

        # Analytical exits gated by P-15 minimum hold AND (v18) graduation winner-track
        # suppression — a green, still-ranked winner is held on a wide trail instead of
        # being cut by rank-drop/alpha-decay.
        if (not _analytical_exits_suppressed and not _in_alpha_decay_cooldown
                and not _grad_suppress_analytical):
            results.append(check_rank_drop(ctx.get("current_rank"), ctx.get("entry_rank")))
            results.append(check_alpha_decay(ctx.get("unrealized_pnl_pct"), days_held))

        # Hard exits always fire regardless of hold period — EXCEPT a runner, which is
        # deliberately held through regime flips to ride a confirmed multibagger.
        if not _is_runner:
            results.append(check_regime_change(
                regime_posture,
                None,
                ctx.get("unrealized_pnl_pct"),
                ctx.get("current_rank"),
                own_trend_intact=ctx.get("own_trend_intact"),
                per_stock_trend_hold=settings.regime_exit_per_stock_trend_enabled,
            ))
        results += [
            check_stop_loss(stop_pnl, stop_loss),
            check_trailing_stop(ctx.get("unrealized_pnl_pct"), ctx.get("max_gain_pct"), trailing),
            check_liquidity(
                ctx.get("avg_daily_volume"),
                float(pos.market_value) if pos.market_value else None,
                ctx.get("last_price"),
            ),
        ]
        # ADR-035 D2: the 30-day time stop is policy-gated (PRD §5 amendment).
        if settings.time_stop_enabled:
            results.append(check_time_stop(days_held))
        return [r for r in results if r.fired]
