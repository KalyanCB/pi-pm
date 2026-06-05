"""Recommendation Service — orchestrates engine run, persistence, and packet enrichment."""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

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
from app.models.recommendation import RecommendationResult, RecommendationRun
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
    "max_buy_slots": 5,
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
        regime_posture = self._resolve_regime_posture(ranking_run)
        factor_ic = self._resolve_factor_ic(ranking_run)
        return EngineConfig(
            config_version=CONVICTION_ENGINE_VERSION,
            conviction_config_version=CONVICTION_CONFIG_VERSION,
            regime_posture=regime_posture,
            factor_ic_median=factor_ic,
            rank_v2_promoted=False,
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

    def _load_exit_signals(self, ranking_run: RankingRun) -> dict[UUID, ExitSignal]:
        """Build per-stock exit signals from exit research policy metrics and
        alpha decay data for the current regime.

        Called for active positions only; for new entries the engine ignores
        the exit_signals dict entirely.
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
                # If cumulative mean return is negative at or before the threshold day → decay
                early_points = [
                    p for p in decay_points
                    if p.trading_day <= _ALPHA_DECAY_NEGATIVE_DAY_THRESHOLD
                    and p.cumulative_mean_return is not None
                    and float(p.cumulative_mean_return) < 0
                ]
                alpha_decayed = bool(early_points)

            # Policy metrics: check if current regime signals poor exit conditions
            policy_metrics = self.exit_metric_repo.list_policy_metrics_covering_as_of(
                strategy_name=ranking_run.strategy_name,
                strategy_version=ranking_run.strategy_version,
                universe_code=ranking_run.universe_code,
                as_of_date=ranking_run.as_of_date,
                regime_labels=regime_labels,
            )

            # Regime turning defensive flags all active positions with regime_turned_defensive
            regime_turned_defensive = self._resolve_regime_posture(ranking_run) == "defensive"

            # Return a single shared signal (stock-level exit research not yet per-symbol)
            # When portfolio engine lands in M2 this becomes per-position
            shared_signal = ExitSignal(
                rank_deteriorated=False,  # evaluated per-stock in engine via rank threshold
                alpha_decayed=alpha_decayed,
                holding_days=0,           # populated from portfolio_positions in M2
                regime_turned_defensive=regime_turned_defensive,
            )
            return {"__shared__": shared_signal}  # type: ignore[return-value]
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
