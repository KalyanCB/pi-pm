"""Recommendation Service — orchestrates engine run, persistence, and packet enrichment."""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session, joinedload

from app.core.constants import (
    CONVICTION_CONFIG_VERSION,
    CONVICTION_ENGINE_VERSION,
    DEFAULT_BENCHMARK_SYMBOL,
    RecommendationAction,
    RecommendationRunStatus,
)
from app.db.repositories.exit_research_metric_repository import ExitResearchMetricRepository
from app.db.repositories.factor_performance_metric_repository import (
    FactorPerformanceMetricRepository,
)
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.recommendation_repository import RecommendationRepository
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.models.paper_trade import PaperTrade
from app.models.portfolio_position import PortfolioPosition
from app.models.recommendation import (
    RecommendationApproval,
    RecommendationOutcome,
    RecommendationResult,
    RecommendationRun,
)
from app.models.ranking_run import RankingRun
from app.recommendation import engine as rec_engine
from app.recommendation.engine import (
    EngineConfig,
    ExitSignal,
    RankingResultRow,
    ValidationSummary,
)


_DEFAULT_CONFIG_BLOB: dict[str, Any] = {
    "engine_version": CONVICTION_ENGINE_VERSION,
    "conviction_config_version": CONVICTION_CONFIG_VERSION,
    "top_pool_size": 20,
    "max_buy_slots": 10,
    "exceptional_daily_cap": 3,
    "rank_v2_promoted": False,
}

# Alpha decay: cumulative return turns negative at or before this trading day → exit
_ALPHA_DECAY_NEGATIVE_DAY_THRESHOLD = 15


class RecommendationService:
    def __init__(
        self,
        db: Session,
        *,
        ranking_run_repo: RankingRunRepository | None = None,
        ranking_result_repo: RankingResultRepository | None = None,
        validation_repo: RankingValidationRepository | None = None,
        factor_metric_repo: FactorPerformanceMetricRepository | None = None,
        regime_repo: RegimeAnalyticsRepository | None = None,
        exit_metric_repo: ExitResearchMetricRepository | None = None,
        recommendation_repo: RecommendationRepository | None = None,
    ) -> None:
        self.db = db
        self.ranking_run_repo = ranking_run_repo or RankingRunRepository(db)
        self.ranking_result_repo = ranking_result_repo or RankingResultRepository(db)
        self.validation_repo = validation_repo or RankingValidationRepository(db)
        self.factor_metric_repo = factor_metric_repo or FactorPerformanceMetricRepository(db)
        self.regime_repo = regime_repo or RegimeAnalyticsRepository(db)
        self.exit_metric_repo = exit_metric_repo or ExitResearchMetricRepository(db)
        self.recommendation_repo = recommendation_repo or RecommendationRepository(db)

    # ── Public API ────────────────────────────────────────────────────────────

    def run_for_ranking_run(self, ranking_run_id: UUID) -> RecommendationRun:
        """Execute the recommendation engine for a completed ranking run."""
        ranking_run = self.ranking_run_repo.get_by_id(ranking_run_id)
        if ranking_run is None:
            raise ValueError(f"RankingRun {ranking_run_id} not found")
        if ranking_run.status != "completed":
            raise ValueError(
                f"RankingRun {ranking_run_id} is not completed (status={ranking_run.status})"
            )

        # Idempotency: return existing if already done
        existing = self.recommendation_repo.get_run_by_ranking_run_id(ranking_run_id)
        if existing and existing.status == RecommendationRunStatus.COMPLETED.value:
            return existing

        config = self._build_engine_config(ranking_run)
        regime_snapshot = self._build_regime_snapshot(ranking_run)
        validation = self._load_validation(ranking_run_id)
        ranking_rows = self._load_ranking_rows(ranking_run_id)
        exit_signals = self._load_exit_signals(ranking_run)
        active_position_stock_ids = self._load_active_position_stock_ids(ranking_run)

        input_hash = rec_engine._compute_input_hash(
            ranking_run_id,
            config.config_version,
            config.regime_posture,
            validation.status,
        )

        rec_run = self.recommendation_repo.create_run(
            ranking_run_id=ranking_run_id,
            strategy_name=ranking_run.strategy_name,
            universe_code=ranking_run.universe_code,
            as_of_date=ranking_run.as_of_date,
            config_version=config.config_version,
            config_snapshot=_DEFAULT_CONFIG_BLOB | {
                "regime_posture": config.regime_posture,
                "factor_ic_median": config.factor_ic_median,
            },
            regime_snapshot=regime_snapshot,
            input_hash=input_hash,
        )

        try:
            result_rows, _ = rec_engine.run(
                ranking_run_id=ranking_run_id,
                ranking_results=ranking_rows,
                validation=validation,
                config=config,
                active_position_stock_ids=active_position_stock_ids,
                exit_signals=exit_signals,
            )

            db_results = [
                RecommendationResult(
                    recommendation_run_id=rec_run.id,
                    stock_id=r.stock_id,
                    rank=r.rank,
                    composite_score=r.composite_score,
                    action=r.action,
                    lifecycle_state=r.lifecycle_state,
                    conviction_score=r.conviction_score,
                    conviction_band=r.conviction_band,
                    conviction_components=r.conviction_components,
                    reason_codes=r.reason_codes,
                )
                for r in result_rows
            ]
            self.recommendation_repo.bulk_insert_results(db_results)
            self.recommendation_repo.complete_run(rec_run)
        except Exception as exc:
            self.recommendation_repo.fail_run(rec_run, str(exc))
            raise

        return rec_run

    def get_latest(
        self, strategy_name: str, as_of_date: date | None = None
    ) -> RecommendationRun | None:
        return self.recommendation_repo.get_latest_run_by_strategy(strategy_name, as_of_date)

    def get_results(
        self,
        run_id: UUID,
        action_filter: list[str] | None = None,
    ) -> list[RecommendationResult]:
        return self.recommendation_repo.get_results(run_id, action_filter)

    def get_daily(
        self,
        as_of_date: date,
        action_filter: list[str] | None = None,
    ) -> dict[str, list[RecommendationResult]]:
        """Return all strategies' results for a given date keyed by strategy_name."""
        runs = self.recommendation_repo.get_runs_by_date(as_of_date)
        out: dict[str, list[RecommendationResult]] = {}
        for run in runs:
            results = self.recommendation_repo.get_results(run.id, action_filter)
            out[run.strategy_name] = results
        return out

    def list_available_dates(self, strategy_name: str | None = None) -> list[date]:
        return self.recommendation_repo.list_available_dates(strategy_name)

    def get_execution_context(self, result_ids: list[UUID]) -> dict[str, dict[str, Any]]:
        """Approvals, trades, positions, and outcomes keyed by recommendation result id."""
        if not result_ids:
            return {}

        id_set = set(result_ids)
        str_ids = {str(rid) for rid in id_set}

        approvals_by_result: dict[UUID, list[dict]] = {rid: [] for rid in id_set}
        for approval in self.db.scalars(
            select(RecommendationApproval).where(
                RecommendationApproval.recommendation_result_id.in_(id_set)
            )
        ).all():
            approvals_by_result[approval.recommendation_result_id].append(
                {
                    "approval_type": approval.approval_type,
                    "decision": approval.decision,
                    "decided_at": approval.decided_at.isoformat(),
                    "actor_id": approval.actor_id,
                }
            )

        positions_by_result: dict[UUID, PortfolioPosition] = {}
        for pos in self.db.scalars(
            select(PortfolioPosition)
            .options(joinedload(PortfolioPosition.stock))
            .where(PortfolioPosition.recommendation_result_id.in_(id_set))
        ).all():
            if pos.recommendation_result_id:
                positions_by_result[pos.recommendation_result_id] = pos

        outcomes_by_result: dict[UUID, RecommendationOutcome] = {}
        for outcome in self.db.scalars(
            select(RecommendationOutcome).where(
                RecommendationOutcome.recommendation_result_id.in_(id_set)
            )
        ).all():
            outcomes_by_result[outcome.recommendation_result_id] = outcome

        trades_by_result: dict[UUID, list[dict]] = {rid: [] for rid in id_set}
        trade_rows = self.db.scalars(
            select(PaperTrade).where(
                or_(
                    *[
                        PaperTrade.metadata_["recommendation_result_id"].as_string() == sid
                        for sid in str_ids
                    ]
                )
            )
        ).all()
        for trade in trade_rows:
            rec_id_str = (trade.metadata_ or {}).get("recommendation_result_id")
            if not rec_id_str:
                continue
            rec_id = UUID(rec_id_str)
            trades_by_result[rec_id].append(
                {
                    "side": trade.side,
                    "fill_price": float(trade.fill_price),
                    "fill_quantity": float(trade.fill_quantity),
                    "status": trade.status,
                    "filled_at": trade.filled_at.isoformat() if trade.filled_at else None,
                }
            )

        context: dict[str, dict[str, Any]] = {}
        for rid in id_set:
            pos = positions_by_result.get(rid)
            outcome = outcomes_by_result.get(rid)
            position_payload = None
            if pos is not None:
                stock = pos.stock
                position_payload = {
                    "id": str(pos.id),
                    "symbol": stock.symbol if stock else None,
                    "quantity": float(pos.quantity),
                    "avg_cost": float(pos.avg_cost),
                    "entry_price": float(pos.entry_price) if pos.entry_price else None,
                    "entry_date": pos.entry_date.isoformat() if pos.entry_date else None,
                    "exit_price": float(pos.exit_price) if pos.exit_price else None,
                    "exit_date": pos.exit_date.isoformat() if pos.exit_date else None,
                    "market_value": float(pos.market_value) if pos.market_value else None,
                    "unrealized_pnl": float(pos.unrealized_pnl) if pos.unrealized_pnl else None,
                    "realized_pnl": float(pos.realized_pnl) if pos.realized_pnl else None,
                    "weight_pct": float(pos.weight_pct) if pos.weight_pct else None,
                    "position_status": pos.position_status,
                    "strategy_name": pos.strategy_name,
                    "conviction_band": pos.conviction_band,
                    "sector": pos.sector,
                }
            outcome_payload = None
            if outcome is not None:
                outcome_payload = {
                    "outcome_status": outcome.outcome_status,
                    "entry_date": outcome.entry_date.isoformat(),
                    "exit_date": outcome.exit_date.isoformat() if outcome.exit_date else None,
                    "pnl_pct": float(outcome.pnl_pct) if outcome.pnl_pct is not None else None,
                    "days_held": outcome.days_held,
                    "exit_reason": outcome.exit_reason,
                }
            context[str(rid)] = {
                "approvals": approvals_by_result.get(rid, []),
                "trades": trades_by_result.get(rid, []),
                "position": position_payload,
                "outcome": outcome_payload,
            }
        return context

    def get_approval_queue(self) -> list[RecommendationResult]:
        return self.recommendation_repo.get_approval_queue()

    def approve(
        self,
        result_id: UUID,
        *,
        approval_type: str,
        decision: str,
        actor_id: str = "owner",
        note: str | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        result = self.db.get(RecommendationResult, result_id)
        if result is None:
            raise ValueError(f"RecommendationResult {result_id} not found")
        self.recommendation_repo.create_approval(
            recommendation_result_id=result_id,
            approval_type=approval_type,
            decision=decision,
            actor_id=actor_id,
            note=note,
            idempotency_key=idempotency_key,
        )
        if decision == "APPROVED" and result.action == RecommendationAction.BUY:
            result.lifecycle_state = "APPROVED"
            self.db.flush()
        elif decision == "REJECTED":
            result.lifecycle_state = "CLOSED"
            self.db.flush()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_engine_config(self, ranking_run: RankingRun) -> EngineConfig:
        from app.core.constants import (
            RANKING_STRATEGY_LOW_VOL_V1,
            RANKING_STRATEGY_REVERSAL_V1,
        )

        regime_posture = self._resolve_regime_posture(ranking_run)
        factor_ic = self._resolve_factor_ic(ranking_run)
        regime_fit = self._load_regime_fit(ranking_run)

        # Strategies designed for non-BULL regimes have validated rank ordering —
        # the rank inversion guard (which prevents EXCEPTIONAL for ranks 1–5) is
        # not appropriate for them.
        rank_v2_promoted = ranking_run.strategy_name in {
            RANKING_STRATEGY_REVERSAL_V1,
            RANKING_STRATEGY_LOW_VOL_V1,
        }

        return EngineConfig(
            config_version=CONVICTION_ENGINE_VERSION,
            conviction_config_version=CONVICTION_CONFIG_VERSION,
            max_buy_slots=10,  # 10 portfolio slots → up to 10 BUYs/day
            regime_posture=regime_posture,
            factor_ic_median=factor_ic,
            rank_v2_promoted=rank_v2_promoted,
            regime_fit=regime_fit,
        )

    def _resolve_regime_posture(self, ranking_run: RankingRun) -> str:
        """Derive regime posture from the ranking run's own regime_label first
        (already computed at ranking time), falling back to the history table."""
        label = (ranking_run.regime_label or "").upper()
        if not label:
            try:
                regime = self.regime_repo.get_current(
                    benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL,
                    as_of_date=ranking_run.as_of_date,
                )
                label = (regime.regime_label or "").upper() if regime else ""
            except Exception:
                pass
        if "BEAR" in label or "HIGH_VOL" in label:
            return "defensive"
        if "BULL" in label and "LOW_VOL" in label:
            return "risk_on"
        return "neutral"

    def _resolve_factor_ic(self, ranking_run: RankingRun) -> float | None:
        """Return median Spearman IC across all factors for the strategy's most
        recent factor-IC window covering as_of_date."""
        try:
            metrics = self.factor_metric_repo.list_metrics_covering_as_of(
                strategy_name=ranking_run.strategy_name,
                strategy_version=ranking_run.strategy_version,
                universe_code=ranking_run.universe_code,
                as_of_date=ranking_run.as_of_date,
            )
            if not metrics:
                return None
            ics = [float(m.ic_spearman) for m in metrics if m.ic_spearman is not None]
            if not ics:
                return None
            ics.sort()
            mid = len(ics) // 2
            return ics[mid] if len(ics) % 2 else (ics[mid - 1] + ics[mid]) / 2
        except Exception:
            return None

    def _load_regime_fit(self, ranking_run: RankingRun):
        """Load RCEE RegimeFit for the strategy × regime combination.

        Returns None (graceful fallback) if regime_label is missing or the
        regime_edge_engine import fails — the engine treats None as UNKNOWN
        and falls back to the legacy R-ENTRY-02 gate.
        """
        try:
            from app.recommendation.regime_edge_engine import RCEEConfig, load_regime_fit
            regime_label = (ranking_run.regime_label or "").upper() or None
            if not regime_label:
                return None
            config = RCEEConfig()
            return load_regime_fit(
                db=self.db,
                strategy_name=ranking_run.strategy_name,
                strategy_version=getattr(ranking_run, "strategy_version", "v1"),
                regime_label=regime_label,
                horizon=20,
                config=config,
            )
        except Exception:
            return None

    def _load_validation(self, ranking_run_id: UUID) -> ValidationSummary:
        report = self.validation_repo.get_by_ranking_run_id(ranking_run_id)
        if report is None:
            return ValidationSummary(status="insufficient_data")
        ic_20d: float | None = None
        spread: float | None = None
        try:
            hm = report.horizon_metrics or {}
            # horizon_metrics stored with int or str keys depending on serialiser
            h20 = hm.get("20") or hm.get(20) or {}
            ic_20d = h20.get("rank_ic_spearman")
            spread = h20.get("spread")
        except Exception:
            pass
        return ValidationSummary(
            status=report.status,
            ic_20d=float(ic_20d) if ic_20d is not None else None,
            top_decile_spread=float(spread) if spread is not None else None,
        )

    def _load_ranking_rows(self, ranking_run_id: UUID) -> list[RankingResultRow]:
        results = self.ranking_result_repo.list_by_run_id(ranking_run_id)
        return [
            RankingResultRow(
                stock_id=r.stock_id,
                rank=r.rank,
                composite_score=float(r.score),
                score_components=r.score_components,
            )
            for r in results
        ]

    def _load_active_position_stock_ids(self, ranking_run: RankingRun) -> set[UUID]:
        """Return set of stock_ids with OPEN positions for this strategy."""
        try:
            open_positions = self.db.scalars(
                select(PortfolioPosition).where(
                    PortfolioPosition.strategy_name == ranking_run.strategy_name,
                    PortfolioPosition.position_status == "OPEN",
                    PortfolioPosition.is_current.is_(True),
                )
            ).all()
            return {pos.stock_id for pos in open_positions}
        except Exception:
            return set()

    def _compute_holding_days(self, entry_date: date | None, as_of_date: date) -> int:
        """Count trading days between entry_date and as_of_date using market_data."""
        if entry_date is None:
            return 0
        try:
            result = self.db.execute(
                text("""
                    SELECT COUNT(*) FROM market_data md
                    JOIN stocks s ON s.id = md.stock_id
                    WHERE s.symbol = '^NSEI'
                      AND md.date > :entry_date AND md.date <= :as_of_date
                """),
                {"entry_date": entry_date, "as_of_date": as_of_date},
            ).scalar()
            return int(result or 0)
        except Exception:
            return 0

    def _load_exit_signals(self, ranking_run: RankingRun) -> dict[UUID, ExitSignal]:
        """Build per-stock exit signals from portfolio positions and exit research data.

        Returns a dict keyed by stock_id for each open position.
        If no open positions, returns {} (engine skips the exit path).
        """
        try:
            regime_label = (ranking_run.regime_label or "").strip() or None
            regime_labels = [regime_label] if regime_label else None

            # Alpha decay: find the peak cumulative return day then check if
            # it turns negative before _ALPHA_DECAY_NEGATIVE_DAY_THRESHOLD
            decay_points = self.exit_metric_repo.list_alpha_decay(
                regime_label=regime_label,
                universe_code=ranking_run.universe_code,
            )

            alpha_decayed = False
            if decay_points:
                early_points = [
                    p for p in decay_points
                    if p.trading_day <= _ALPHA_DECAY_NEGATIVE_DAY_THRESHOLD
                    and p.cumulative_mean_return is not None
                    and float(p.cumulative_mean_return) < 0
                ]
                alpha_decayed = bool(early_points)

            # Policy metrics: check if current regime signals poor exit conditions
            self.exit_metric_repo.list_policy_metrics_covering_as_of(
                strategy_name=ranking_run.strategy_name,
                strategy_version=ranking_run.strategy_version,
                universe_code=ranking_run.universe_code,
                as_of_date=ranking_run.as_of_date,
                regime_labels=regime_labels,
            )

            # Regime turning defensive flags all active positions with regime_turned_defensive
            regime_turned_defensive = self._resolve_regime_posture(ranking_run) == "defensive"

            # Build per-stock signals from open portfolio positions
            open_positions = self.db.scalars(
                select(PortfolioPosition).where(
                    PortfolioPosition.strategy_name == ranking_run.strategy_name,
                    PortfolioPosition.position_status == "OPEN",
                    PortfolioPosition.is_current.is_(True),
                )
            ).all()

            if not open_positions:
                return {}

            signals: dict[UUID, ExitSignal] = {}
            for pos in open_positions:
                holding_days = self._compute_holding_days(pos.entry_date, ranking_run.as_of_date)
                signals[pos.stock_id] = ExitSignal(
                    rank_deteriorated=False,  # engine evaluates this via rank threshold
                    alpha_decayed=alpha_decayed,
                    holding_days=holding_days,
                    regime_turned_defensive=regime_turned_defensive,
                )
            return signals
        except Exception:
            return {}

    def _build_regime_snapshot(self, ranking_run: RankingRun) -> dict[str, Any]:
        label = ranking_run.regime_label
        if not label:
            try:
                regime = self.regime_repo.get_current(
                    benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL,
                    as_of_date=ranking_run.as_of_date,
                )
                label = regime.regime_label if regime else None
            except Exception:
                label = None
        return {
            "regime_label": label,
            "regime_posture": self._resolve_regime_posture(ranking_run),
            "as_of_date": ranking_run.as_of_date.isoformat(),
        }

    # ── Recommendation block for ARGS packet ──────────────────────────────────

    def get_recommendation_block_for_packet(
        self,
        *,
        ranking_run_id: UUID,
        stock_id: UUID,
    ) -> dict[str, Any] | None:
        """Return the recommendation JSONB block to embed in an ARGS packet.

        ARGS committees are advisory; this block must not be mutated by any
        committee plugin (R-ARGS-04).
        """
        rec_run = self.recommendation_repo.get_run_by_ranking_run_id(ranking_run_id)
        if rec_run is None or rec_run.status != RecommendationRunStatus.COMPLETED.value:
            return None
        result = self.recommendation_repo.get_result_by_symbol(rec_run.id, stock_id)
        if result is None:
            return None
        return {
            "action": result.action,
            "conviction_score": result.conviction_score,
            "conviction_band": result.conviction_band,
            "reason_codes": result.reason_codes,
            "engine_version": CONVICTION_ENGINE_VERSION,
            "ranking_run_id": str(ranking_run_id),
        }
