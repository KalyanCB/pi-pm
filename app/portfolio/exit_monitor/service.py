"""Exit Monitor Service — evaluates ACTIVE positions daily for exit triggers.

Generates ExitRecommendation rows. Never auto-executes. Human confirms.
"""
from __future__ import annotations

from datetime import date, datetime, UTC
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

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
        """Evaluate all ACTIVE positions and generate ExitRecommendation rows."""
        as_of = as_of_date or date.today()
        cfg = self._get_config()
        positions = self._get_open_positions()
        regime_posture = self._resolve_regime_posture(as_of)

        results: list[ExitRecommendation] = []

        for pos in positions:
            # Skip if PENDING exit already exists for today
            existing = self.db.scalar(
                select(ExitRecommendation).where(
                    ExitRecommendation.portfolio_position_id == pos.id,
                    ExitRecommendation.as_of_date == as_of,
                    ExitRecommendation.status == "PENDING",
                )
            )
            if existing:
                results.append(existing)
                continue

            context = self._build_position_context(pos, as_of)
            fired_triggers = self._evaluate_triggers(pos, context, cfg, regime_posture)

            if not fired_triggers:
                continue

            trigger_codes = [t.trigger_code for t in fired_triggers]
            trigger_details = {t.trigger_code: t.details for t in fired_triggers}
            urgency = max(
                fired_triggers,
                key=lambda t: ["LOW", "NORMAL", "HIGH", "CRITICAL"].index(t.urgency)
            ).urgency

            unrealized_pct = None
            if pos.avg_cost and context.get("last_price"):
                unrealized_pct = (context["last_price"] - float(pos.avg_cost)) / float(pos.avg_cost) * 100

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
        return list(self.db.scalars(
            select(PortfolioPosition).where(
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.position_status == "OPEN",
            )
        ).all())

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

    def _build_position_context(self, pos: PortfolioPosition, as_of: date) -> dict:
        ctx: dict = {}

        # Days held
        if pos.entry_date:
            ctx["days_held"] = (as_of - pos.entry_date).days

        # Latest price
        latest = self.market_data_repo.get_latest_market_data(pos.stock_id)
        if latest:
            ctx["last_price"] = float(latest.close)
            ctx["avg_daily_volume"] = float(latest.volume) if latest.volume else None

        # Current rank from latest ranking run
        ctx["current_rank"] = self._get_current_rank(pos.stock_id, as_of)

        # Unrealized P&L pct
        if pos.avg_cost and ctx.get("last_price"):
            ctx["unrealized_pnl_pct"] = (ctx["last_price"] - float(pos.avg_cost)) / float(pos.avg_cost) * 100

        # Max gain (from RecommendationOutcome if available)
        ctx["max_gain_pct"] = self._get_max_gain(pos)

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
    ) -> list:
        single_cap = float(cfg.single_name_cap_pct * 100) if cfg else 18.0
        stop_loss = -8.0  # PO default; could be in config
        trailing = 5.0

        results = [
            check_rank_drop(ctx.get("current_rank"), None),
            check_alpha_decay(ctx.get("unrealized_pnl_pct"), ctx.get("days_held", 0)),
            check_regime_change(regime_posture, None),
            check_time_stop(ctx.get("days_held", 0)),
            check_stop_loss(ctx.get("unrealized_pnl_pct"), stop_loss),
            check_trailing_stop(ctx.get("unrealized_pnl_pct"), ctx.get("max_gain_pct"), trailing),
            check_concentration(float(pos.weight_pct) if pos.weight_pct else None, single_cap),
            check_liquidity(
                ctx.get("avg_daily_volume"),
                float(pos.market_value) if pos.market_value else None,
            ),
        ]
        return [r for r in results if r.fired]
