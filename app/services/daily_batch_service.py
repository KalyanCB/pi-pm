from __future__ import annotations

import hashlib
import json
import time
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.constants import (
    DailyBatchPhase,
    DailyBatchRunStatus,
    IngestPeriod,
    IngestionMode,
)
from app.core.exceptions import NotFoundError, PiPMError
from app.db.repositories.daily_batch_artifact_repository import DailyBatchArtifactRepository
from app.db.repositories.daily_batch_run_repository import DailyBatchRunRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.ops.daily_batch.batch_planner import DailyBatchPlanner, StrategySpec
from app.ops.daily_batch.traceability import DailyBatchTraceabilityRecorder
from app.ops.daily_batch.trading_day_resolver import TradingDayResolver
from app.schemas.backtest import GenerateRankingsRequest
from app.schemas.daily_batch import (
    DailyBatchPlanSnapshot,
    DailyBatchRunCreateRequest,
    DailyBatchRunCreateResponse,
    DailyBatchRunStatusResponse,
    DailyBatchRunSummary,
    DailyBatchTraceResponse,
)
from app.services.backtest_service import BacktestService
from app.ops.daily_batch.evidence_windows import DEFAULT_REGIME_PERFORMANCE_HORIZON
from app.services.exit_research_service import ExitResearchService
from app.services.factor_predictive_power_service import FactorPredictivePowerService
from app.services.market_data_service import MarketDataService
from app.services.regime_analytics_service import RegimeAnalyticsService
from app.services.research_intelligence_service import ResearchIntelligenceService
from app.services.signal_validation_service import SignalValidationService
from app.services.recommendation_service import RecommendationService


class DailyBatchService:
    _PHASE_WEIGHTS = {
        DailyBatchPhase.INGEST: 12.0,
        DailyBatchPhase.RANKINGS: 20.0,
        DailyBatchPhase.VALIDATION: 10.0,
        DailyBatchPhase.RECOMMENDATIONS: 6.0,
        DailyBatchPhase.REGIME_HISTORY: 5.0,
        DailyBatchPhase.REGIME_PERFORMANCE: 7.0,
        DailyBatchPhase.FACTOR_IC: 17.0,
        DailyBatchPhase.RESEARCH_INTELLIGENCE: 9.0,
        DailyBatchPhase.EXIT_RESEARCH: 14.0,
    }

    def __init__(
        self,
        db: Session,
        *,
        market_data_service: MarketDataService,
        backtest_service: BacktestService,
        validation_service: SignalValidationService,
        factor_service: FactorPredictivePowerService,
        exit_service: ExitResearchService,
        regime_service: RegimeAnalyticsService,
        research_intelligence_service: ResearchIntelligenceService,
        ranking_run_repo: RankingRunRepository,
        run_repo: DailyBatchRunRepository | None = None,
        artifact_repo: DailyBatchArtifactRepository | None = None,
        recommendation_service: RecommendationService | None = None,
    ) -> None:
        self.db = db
        self.market_data_service = market_data_service
        self.backtest_service = backtest_service
        self.validation_service = validation_service
        self.factor_service = factor_service
        self.exit_service = exit_service
        self.regime_service = regime_service
        self.research_intelligence_service = research_intelligence_service
        self.ranking_run_repo = ranking_run_repo
        self.run_repo = run_repo or DailyBatchRunRepository(db)
        self.artifact_repo = artifact_repo or DailyBatchArtifactRepository(db)
        self.recommendation_service = recommendation_service or RecommendationService(db)

    def create_and_execute(self, request: DailyBatchRunCreateRequest) -> DailyBatchRunCreateResponse:
        if request.idempotency_key and not request.force_from_date:
            existing = self.run_repo.get_by_idempotency_key(request.idempotency_key)
            if existing is not None and existing.status == DailyBatchRunStatus.COMPLETED.value:
                return self._response_from_run(existing, idempotent_replay=True)

        effective_from = request.from_date
        if request.force_from_date and effective_from is None:
            raise PiPMError("from_date is required when force_from_date is true")

        started = time.perf_counter()
        run = self.run_repo.create_running(
            universe_code=request.universe_code,
            benchmark_symbol=request.benchmark_symbol,
            parameter_set=request.model_dump(mode="json"),
            idempotency_key=request.idempotency_key,
            dry_run=request.dry_run,
        )
        run.force_from_date = request.force_from_date
        run.force_recompute = request.force_recompute
        run.force_regenerate_rankings = request.force_regenerate_rankings
        self.db.flush()

        resolver = TradingDayResolver(self.db, benchmark_symbol=request.benchmark_symbol)
        resolution = resolver.resolve(
            target_date=request.target_date,
            assume_session_done=request.assume_session_done,
            force=request.force,
        )

        planner = DailyBatchPlanner(
            self.db,
            universe_code=request.universe_code,
            benchmark_symbol=request.benchmark_symbol,
            strategies=[
                StrategySpec(s.strategy_name, s.strategy_version) for s in request.strategies
            ],
            holdout_start_date=request.holdout_start_date,
        )
        plan = planner.build_plan(
            resolution,
            from_date=effective_from,
            force_from_date=request.force_from_date,
        )
        self.run_repo.update_plan(
            run,
            target_trading_day=plan.target_trading_day,
            from_date=plan.from_date,
            plan_snapshot=plan.to_dict(),
        )
        self.db.commit()

        plan_snapshot = DailyBatchPlanSnapshot(
            needs_ingest=plan.needs_ingest,
            ranking_gaps={k: [d.isoformat() for d in v] for k, v in plan.ranking_gaps.items()},
            validation_gap_count=plan.validation_gap_count,
            factor_ic_needed=plan.factor_ic_needed,
            regime_history_needed=plan.regime_history_needed,
            regime_performance_needed=plan.regime_performance_needed,
            exit_research_needed=plan.exit_research_needed,
            research_intelligence_needed=plan.research_intelligence_needed,
            factor_ic_window_start=plan.factor_ic_window_start,
            factor_ic_window_end=plan.factor_ic_window_end,
            already_current=plan.already_current,
        )

        if request.dry_run:
            self.db.commit()
            return DailyBatchRunCreateResponse(
                run_id=str(run.id),
                status=run.status,
                target_trading_day=plan.target_trading_day,
                from_date=plan.from_date,
                resolution_reason=resolution.resolution_reason,
                already_current=plan.already_current,
                plan=plan_snapshot,
                phases=None,
                started_at=run.started_at,
                completed_at=run.completed_at,
                duration_seconds=float(run.duration_seconds) if run.duration_seconds else None,
            )

        if plan.already_current and not request.force_from_date:
            self.run_repo.complete(run, duration_seconds=time.perf_counter() - started)
            self.db.commit()
            return DailyBatchRunCreateResponse(
                run_id=str(run.id),
                status=run.status,
                target_trading_day=plan.target_trading_day,
                from_date=plan.from_date,
                resolution_reason=resolution.resolution_reason,
                already_current=True,
                plan=plan_snapshot,
                phases={},
                started_at=run.started_at,
                completed_at=run.completed_at,
                duration_seconds=float(run.duration_seconds) if run.duration_seconds else None,
            )

        trace = DailyBatchTraceabilityRecorder(self.db)
        phase_results: dict = {}
        base_pct = 0.0

        try:
            if request.phases.ingest and plan.needs_ingest:
                self._set_phase(run, DailyBatchPhase.INGEST, base_pct)
                phase_results["ingest"] = self._run_ingest(
                    run.id,
                    request,
                    trace,
                )
                base_pct += self._PHASE_WEIGHTS[DailyBatchPhase.INGEST]

            if request.phases.rankings and any(plan.ranking_gaps.values()):
                self._set_phase(run, DailyBatchPhase.RANKINGS, base_pct)
                phase_results["rankings"] = self._run_rankings(
                    run.id,
                    request,
                    plan,
                    trace,
                )
                base_pct += self._PHASE_WEIGHTS[DailyBatchPhase.RANKINGS]

            if request.phases.validation and (
                plan.validation_gap_count > 0
                or request.force_recompute
                or request.force_from_date
            ):
                self._set_phase(run, DailyBatchPhase.VALIDATION, base_pct)
                result = self.validation_service.backfill(
                    plan.from_date,
                    plan.target_trading_day,
                    universe_code=request.universe_code,
                    force_recompute=request.force_recompute or request.force_from_date,
                )
                phase_results["validation"] = {
                    "runs_found": result.runs_found,
                    "validated": result.validated,
                    "reused": result.reused,
                    "failed": result.failed,
                }
                for spec in request.strategies:
                    reports = self.validation_service.validation_repo.list_completed_with_runs(
                        universe_code=request.universe_code,
                        strategy_name=spec.strategy_name,
                        strategy_version=spec.strategy_version,
                        start_date=plan.from_date,
                        end_date=plan.target_trading_day,
                    )
                    for report in reports:
                        trace.record_validation_report(run.id, report.id, status=report.status)
                base_pct += self._PHASE_WEIGHTS[DailyBatchPhase.VALIDATION]

            if request.phases.recommendations:
                self._set_phase(run, DailyBatchPhase.RECOMMENDATIONS, base_pct)
                phase_results["recommendations"] = {}
                for spec in request.strategies:
                    ranking_runs = self.ranking_run_repo.list_completed_in_range(
                        universe_code=request.universe_code,
                        strategy_name=spec.strategy_name,
                        strategy_version=spec.strategy_version,
                        start_date=plan.from_date,
                        end_date=plan.target_trading_day,
                    )
                    for rr in ranking_runs:
                        try:
                            rec_run = self.recommendation_service.run_for_ranking_run(rr.id)
                            trace.record_recommendation_run(
                                run.id,
                                rec_run.id,
                                strategy_name=spec.strategy_name,
                                status=rec_run.status,
                            )
                            phase_results["recommendations"].setdefault(spec.strategy_name, []).append(
                                {
                                    "ranking_run_id": str(rr.id),
                                    "recommendation_run_id": str(rec_run.id),
                                    "status": rec_run.status,
                                }
                            )
                        except Exception as exc:
                            phase_results["recommendations"].setdefault(spec.strategy_name, []).append(
                                {
                                    "ranking_run_id": str(rr.id),
                                    "status": "failed",
                                    "error": str(exc),
                                }
                            )
                base_pct += self._PHASE_WEIGHTS[DailyBatchPhase.RECOMMENDATIONS]

            # Cross-strategy deduplication: if same symbol gets BUY from multiple
            # strategies on the same day, keep the higher-conviction one.
            if request.phases.recommendations:
                self._dedup_cross_strategy_buys(
                    strategies=request.strategies,
                    as_of_date=plan.target_trading_day,
                )
                self.db.commit()

            # ── HITL Gate ────────────────────────────────────────────────────
            # When HITL_ENABLED=false (paper trading mode), auto-approve all
            # CANDIDATE BUYs for today with actor=hitl_auto. Full audit trail
            # preserved. Committee remains advisory-only regardless of flag.
            if request.phases.recommendations:
                from app.ops.hitl.gate import HITLGate
                hitl = HITLGate.from_settings()
                hitl.log_status()
                if hitl.auto_approve:
                    self._set_phase(run, "hitl_auto_approve", base_pct)
                    hitl_result = hitl.auto_approve_buys(
                        self.db,
                        as_of_date=plan.target_trading_day,
                        max_slots=5,
                    )
                    phase_results["hitl_auto_approve"] = hitl_result
                    self.db.commit()

            # ── T2 Daily Exit Monitor (ADR-033) ──────────────────────────────
            # Runs whenever phases.portfolio=true, independent of paper pilot
            # and HITL gate. This closes the gap where HITL_ENABLED=true
            # silently skipped exit monitoring (ADR-033 implementation gap #3).
            if request.phases.portfolio and request.portfolio_phases.exit_monitor:
                self._set_phase(run, "exit_monitor", base_pct)
                from app.portfolio.exit_monitor.service import ExitMonitorService
                t2_monitor = ExitMonitorService(self.db)
                t2_recs = t2_monitor.run(plan.target_trading_day)
                phase_results["exit_monitor"] = {
                    "candidates": len(t2_recs),
                    "ids": [str(r.id) for r in t2_recs],
                    "monitor_tier": "DAILY",
                }
                self.db.commit()

            # ── Paper Trading ─────────────────────────────────────────────────
            # Execute paper fills only when both HITL_ENABLED=false and
            # PAPER_TRADING_ENABLED=true. Requires phases.portfolio=true in
            # the request (so caller opts in explicitly).
            # ADR-033: exit_monitor=False here — T2 already ran above for all modes.
            if request.phases.recommendations and request.phases.portfolio:
                from app.ops.hitl.gate import HITLGate
                _hitl = HITLGate.from_settings()
                if _hitl.should_execute_paper_trades:
                    self._set_phase(run, "paper_trading", base_pct)
                    from app.ops.daily_batch.paper_pilot_ops import PaperPilotOps
                    pilot = PaperPilotOps(self.db)
                    paper_result = pilot.run(
                        as_of_date=plan.target_trading_day,
                        recompute=request.portfolio_phases.recompute,
                        exit_monitor=False,      # ADR-033: T2 already ran above
                        paper_trading=request.portfolio_phases.paper_trading,
                        nav_snapshot=request.portfolio_phases.nav_snapshot,
                        reconcile=request.portfolio_phases.reconcile,
                        pilot_auto_approve=True,
                        pilot_auto_execute=True,
                    )
                    phase_results["paper_trading"] = paper_result
                    self.db.commit()

            regime_history_start = max(
                request.holdout_start_date,
                plan.from_date,
            )
            if request.phases.regime_history and plan.regime_history_needed:
                self._set_phase(run, DailyBatchPhase.REGIME_HISTORY, base_pct)
                history_result = self.regime_service.backfill_regime_history(
                    start_date=regime_history_start,
                    end_date=plan.target_trading_day,
                    benchmark_symbol=request.benchmark_symbol,
                )
                trace.record_regime_history_backfill(
                    run.id,
                    run.id,
                    rows_written=history_result.rows_written,
                )
                phase_results["regime_history"] = {
                    "trading_days_attempted": history_result.trading_days_attempted,
                    "rows_written": history_result.rows_written,
                    "rows_skipped": history_result.rows_skipped,
                    "start_date": regime_history_start.isoformat(),
                    "end_date": plan.target_trading_day.isoformat(),
                }
                self.db.commit()
                base_pct += self._PHASE_WEIGHTS[DailyBatchPhase.REGIME_HISTORY]

            if request.phases.regime_performance and plan.regime_performance_needed:
                self._set_phase(run, DailyBatchPhase.REGIME_PERFORMANCE, base_pct)
                phase_results["regime_performance"] = {}
                for spec in request.strategies:
                    rows = self.regime_service.refresh_strategy_regime_performance(
                        strategy_name=spec.strategy_name,
                        strategy_version=spec.strategy_version,
                        horizon=DEFAULT_REGIME_PERFORMANCE_HORIZON,
                    )
                    artifact_id = rows[0].id if rows else run.id
                    trace.record_regime_performance_refresh(
                        run.id,
                        artifact_id,
                        strategy_name=spec.strategy_name,
                    )
                    phase_results["regime_performance"][spec.strategy_name] = {
                        "rows_written": len(rows),
                        "horizon": DEFAULT_REGIME_PERFORMANCE_HORIZON,
                    }
                self.db.commit()
                base_pct += self._PHASE_WEIGHTS[DailyBatchPhase.REGIME_PERFORMANCE]

            factor_start = plan.factor_ic_window_start or plan.from_date
            factor_end = plan.factor_ic_window_end or plan.target_trading_day
            if request.force_from_date:
                factor_start = max(request.holdout_start_date, plan.from_date)
                factor_end = plan.target_trading_day

            if request.phases.factor_ic and plan.factor_ic_needed:
                if factor_start is None or factor_end is None:
                    phase_results["factor_ic"] = {
                        "skipped": True,
                        "reason": "no_completed_validation_window",
                    }
                else:
                    self._set_phase(run, DailyBatchPhase.FACTOR_IC, base_pct)
                    phase_results["factor_ic"] = {}
                    for spec in request.strategies:
                        self.run_repo.update_progress(
                            run,
                            current_load={
                                "phase": DailyBatchPhase.FACTOR_IC.value,
                                "strategy": spec.strategy_name,
                            },
                        )
                        self.db.commit()
                        fic_run = self.factor_service.backfill(
                            strategy_name=spec.strategy_name,
                            strategy_version=spec.strategy_version,
                            universe_code=request.universe_code,
                            start_date=factor_start,
                            end_date=factor_end,
                            holdout_start_date=request.holdout_start_date,
                            force_recompute=request.force_recompute or request.force_from_date,
                        )
                        trace.record_factor_run(
                            run.id,
                            fic_run.id,
                            strategy_name=spec.strategy_name,
                            status=fic_run.status,
                        )
                        phase_results["factor_ic"][spec.strategy_name] = {
                            "run_id": str(fic_run.id),
                            "status": fic_run.status,
                            "metrics_written": fic_run.metrics_written,
                            "window_start": factor_start.isoformat(),
                            "window_end": factor_end.isoformat(),
                        }
                    base_pct += self._PHASE_WEIGHTS[DailyBatchPhase.FACTOR_IC]

            if request.phases.research_intelligence and plan.research_intelligence_needed:
                if factor_start is None or factor_end is None:
                    phase_results["research_intelligence"] = {
                        "skipped": True,
                        "reason": "no_completed_validation_window",
                    }
                else:
                    self._set_phase(run, DailyBatchPhase.RESEARCH_INTELLIGENCE, base_pct)
                    intel = self.research_intelligence_service.generate_executive_pack(
                        universe_code=request.universe_code,
                        start_date=factor_start,
                        end_date=factor_end,
                        holdout_start_date=request.holdout_start_date,
                        persist=True,
                    )
                    trace.record_research_intelligence_run(
                        run.id,
                        UUID(intel["run_id"]),
                        status=intel.get("status", "completed"),
                    )
                    phase_results["research_intelligence"] = {
                        "run_id": intel["run_id"],
                        "status": intel.get("status"),
                        "window_start": factor_start.isoformat(),
                        "window_end": factor_end.isoformat(),
                    }
                    base_pct += self._PHASE_WEIGHTS[DailyBatchPhase.RESEARCH_INTELLIGENCE]

            if request.phases.exit_research and plan.exit_research_needed:
                if factor_start is None or factor_end is None:
                    phase_results["exit_research"] = {
                        "skipped": True,
                        "reason": "no_completed_validation_window",
                    }
                else:
                    self._set_phase(run, DailyBatchPhase.EXIT_RESEARCH, base_pct)
                    phase_results["exit_research"] = {}
                    for spec in request.strategies:
                        self.run_repo.update_progress(
                            run,
                            current_load={
                                "phase": DailyBatchPhase.EXIT_RESEARCH.value,
                                "strategy": spec.strategy_name,
                            },
                        )
                        self.db.commit()
                        exit_run = self.exit_service.backfill(
                            strategy_name=spec.strategy_name,
                            strategy_version=spec.strategy_version,
                            universe_code=request.universe_code,
                            start_date=factor_start,
                            end_date=factor_end,
                            holdout_start_date=request.holdout_start_date,
                            force_recompute=request.force_recompute or request.force_from_date,
                        )
                        trace.record_exit_research_run(
                            run.id,
                            exit_run.id,
                            strategy_name=spec.strategy_name,
                            status=exit_run.status,
                        )
                        phase_results["exit_research"][spec.strategy_name] = {
                            "run_id": str(exit_run.id),
                            "status": exit_run.status,
                            "metrics_written": exit_run.metrics_written,
                            "window_start": factor_start.isoformat(),
                            "window_end": factor_end.isoformat(),
                        }
                    base_pct += self._PHASE_WEIGHTS[DailyBatchPhase.EXIT_RESEARCH]

            self.run_repo.set_phase_results(run, phase_results)
            duration = time.perf_counter() - started
            self.run_repo.complete(run, duration_seconds=duration)
            self.db.commit()
            return DailyBatchRunCreateResponse(
                run_id=str(run.id),
                status=run.status,
                target_trading_day=plan.target_trading_day,
                from_date=plan.from_date,
                resolution_reason=resolution.resolution_reason,
                already_current=False,
                plan=plan_snapshot,
                phases=phase_results,
                started_at=run.started_at,
                completed_at=run.completed_at,
                duration_seconds=float(run.duration_seconds) if run.duration_seconds else None,
            )
        except Exception as exc:
            self.db.rollback()
            run = self.run_repo.get_by_id(run.id) or run
            self.run_repo.fail(run, str(exc))
            self.db.commit()
            raise

    def _dedup_cross_strategy_buys(
        self,
        strategies: list,
        as_of_date: date,
    ) -> None:
        """If the same symbol receives BUY from multiple strategies on the same day,
        keep only the highest-conviction BUY. Downgrade others to WATCH with
        reason code CROSS_STRATEGY_DUPLICATE.

        Rationale: deploying 2 slots (one per strategy) into the same stock doubles
        concentration without adding diversification.
        """
        from collections import defaultdict

        from sqlalchemy import select

        from app.core.constants import REC_REASON_CROSS_STRATEGY_DUPLICATE, RecommendationAction
        from app.models.ranking_run import RankingRun
        from app.models.recommendation import RecommendationResult, RecommendationRun

        strategy_names = [s.strategy_name for s in strategies]

        buys = self.db.execute(
            select(
                RecommendationResult.id,
                RecommendationResult.stock_id,
                RecommendationResult.conviction_score,
                RecommendationRun.strategy_name,
            )
            .join(RecommendationRun, RecommendationRun.id == RecommendationResult.recommendation_run_id)
            .join(RankingRun, RankingRun.id == RecommendationRun.ranking_run_id)
            .where(
                RecommendationResult.action == RecommendationAction.BUY,
                RankingRun.as_of_date == as_of_date,
                RecommendationRun.strategy_name.in_(strategy_names),
            )
        ).all()

        by_stock: dict = defaultdict(list)
        for row in buys:
            by_stock[row.stock_id].append(row)

        ids_to_downgrade = []
        for stock_id, rows in by_stock.items():
            if len(rows) <= 1:
                continue
            sorted_rows = sorted(rows, key=lambda r: r.conviction_score, reverse=True)
            for row in sorted_rows[1:]:
                ids_to_downgrade.append(row.id)

        if ids_to_downgrade:
            # Downgrade duplicates via the ORM. The previous raw-SQL UPDATE used
            # `::jsonb`/`::text` casts which psycopg3 rejects ("syntax error at
            # or near ':'"). Re-fetch the (freshly-inserted) rows and mutate them
            # in place — JSONB reason_codes is a Python list at the ORM layer.
            rows_to_fix = (
                self.db.execute(
                    select(RecommendationResult).where(
                        RecommendationResult.id.in_(ids_to_downgrade)
                    )
                )
                .scalars()
                .all()
            )
            for rec in rows_to_fix:
                rec.action = "WATCH"
                codes = list(rec.reason_codes or [])
                if REC_REASON_CROSS_STRATEGY_DUPLICATE not in codes:
                    codes.append(REC_REASON_CROSS_STRATEGY_DUPLICATE)
                    rec.reason_codes = codes
            self.db.flush()

    def get_run(self, run_id: UUID) -> DailyBatchRunStatusResponse:
        run = self.run_repo.get_by_id(run_id)
        if run is None:
            raise NotFoundError(f"Daily batch run not found: {run_id}")
        return DailyBatchRunStatusResponse(
            run_id=str(run.id),
            status=run.status,
            current_phase=run.current_phase,
            target_trading_day=run.target_trading_day,
            from_date=run.from_date,
            percent_complete=float(run.percent_complete) if run.percent_complete is not None else None,
            phase_progress=run.phase_results,
            plan_snapshot=run.plan_snapshot,
            phase_results=run.phase_results,
            error_message=run.error_message,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_seconds=float(run.duration_seconds) if run.duration_seconds else None,
        )

    def list_runs(self, *, limit: int = 50) -> list[DailyBatchRunSummary]:
        return [
            DailyBatchRunSummary(
                run_id=str(r.id),
                status=r.status,
                universe_code=r.universe_code,
                target_trading_day=r.target_trading_day,
                started_at=r.started_at,
                completed_at=r.completed_at,
                duration_seconds=float(r.duration_seconds) if r.duration_seconds else None,
            )
            for r in self.run_repo.list_runs(limit=limit)
        ]

    def get_trace(self, run_id: UUID) -> DailyBatchTraceResponse:
        run = self.run_repo.get_by_id(run_id)
        if run is None:
            raise NotFoundError(f"Daily batch run not found: {run_id}")
        grouped = self.artifact_repo.group_ids_by_type(run_id)
        artifacts = [
            {
                "artifact_type": a.artifact_type,
                "artifact_id": str(a.artifact_id),
                "strategy_name": a.strategy_name,
                "as_of_date": a.as_of_date.isoformat() if a.as_of_date else None,
                "status": a.status,
            }
            for a in self.artifact_repo.list_by_run(run_id)
        ]
        return DailyBatchTraceResponse(
            run_id=str(run.id),
            status=run.status,
            current_phase=run.current_phase,
            target_trading_day=run.target_trading_day,
            from_date=run.from_date,
            lineage={
                "ingestion_batch_ids": grouped.get("ingestion_batch", []),
                "ranking_run_ids": grouped.get("ranking_run", []),
                "validation_report_ids": grouped.get("validation_report", []),
                "factor_performance_run_ids": grouped.get("factor_performance_run", []),
                "regime_history_backfill_ids": grouped.get("regime_history_backfill", []),
                "regime_performance_refresh_ids": grouped.get("regime_performance_refresh", []),
                "exit_research_run_ids": grouped.get("exit_research_run", []),
                "research_intelligence_run_ids": grouped.get("research_intelligence_run", []),
            },
            current_load=run.current_load,
            artifacts=artifacts,
        )

    def _set_phase(self, run, phase: "DailyBatchPhase | str", base_pct: float) -> None:
        phase_str = phase.value if hasattr(phase, "value") else str(phase)
        self.run_repo.update_progress(
            run,
            current_phase=phase_str,
            percent_complete=base_pct,
            current_load={"phase": phase_str},
        )
        self.db.commit()

    def _run_ingest(
        self,
        run_id: UUID,
        request: DailyBatchRunCreateRequest,
        trace: DailyBatchTraceabilityRecorder,
    ) -> dict:
        universe = self.backtest_service.universe_repo.list_stocks_in_universe(request.universe_code)
        symbols = sorted({s.symbol for s in universe})
        totals = {
            "batches": 0,
            "symbols_succeeded": 0,
            "symbols_failed": 0,
            "rows_inserted": 0,
            "rows_updated": 0,
        }
        # On a fresh DB (no existing market data), always do a full pull so
        # ranking strategies have enough price history (breakout_v1 needs 252d,
        # momentum_v1 needs 63d). since_date is only applied when data already
        # exists and we are doing an incremental top-up.
        has_existing_data = self.market_data_service.has_historical_data()
        if not has_existing_data:
            ingestion_mode = IngestionMode.FULL_REFRESH
            since_date = None
        else:
            ingestion_mode = IngestionMode.INCREMENTAL
            since_date = request.from_date if (request.force_from_date or request.force_ingest) else None

        batch_size = request.ingest_batch_size
        for offset in range(0, len(symbols), batch_size):
            batch_symbols = symbols[offset : offset + batch_size]
            response = self.market_data_service.ingest(
                batch_symbols,
                IngestPeriod.ONE_YEAR,
                ingestion_mode=ingestion_mode,
                since_date=since_date,
            )
            totals["batches"] += 1
            totals["symbols_succeeded"] += response.symbols_processed
            totals["symbols_failed"] += response.symbols_failed
            totals["rows_inserted"] += response.rows_inserted
            totals["rows_updated"] += response.rows_updated
            if response.batch_id is not None:
                trace.record_ingestion_batch(
                    run_id,
                    response.batch_id,
                    status=response.status.value,
                )
            if response.symbols_failed and not request.allow_partial_ingest:
                raise PiPMError(
                    f"Ingest failed for {response.symbols_failed} symbols in batch {response.batch_id}"
                )
        return totals

    def _run_rankings(
        self,
        run_id: UUID,
        request: DailyBatchRunCreateRequest,
        plan,
        trace: DailyBatchTraceabilityRecorder,
    ) -> dict:
        results: dict = {}
        force = request.force_regenerate_rankings or request.force_from_date
        for spec in request.strategies:
            key = f"{spec.strategy_name}:{spec.strategy_version}"
            gaps = plan.ranking_gaps.get(key, [])
            if not gaps and not force:
                continue
            start = min(gaps) if gaps else plan.from_date
            end = max(gaps) if gaps else plan.target_trading_day
            gen_request = GenerateRankingsRequest(
                universe_code=request.universe_code,
                start_date=start,
                end_date=end,
                strategy_name=spec.strategy_name,
                strategy_version=spec.strategy_version,
                benchmark_symbol=request.benchmark_symbol,
                force_regenerate=force,
            )
            outcome = self.backtest_service.generate_rankings(gen_request)
            results[spec.strategy_name] = {
                "runs_created": outcome.runs_created,
                "runs_reused": outcome.runs_reused,
                "runs_failed": outcome.runs_failed,
                "failed_dates": [d.isoformat() for d in outcome.failed_dates],
            }
            runs = self.ranking_run_repo.list_completed_in_range(
                start,
                end,
                universe_code=request.universe_code,
                strategy_name=spec.strategy_name,
                strategy_version=spec.strategy_version,
            )
            for ranking_run in runs:
                trace.record_ranking_run(
                    run_id,
                    ranking_run.id,
                    strategy_name=spec.strategy_name,
                    as_of_date=ranking_run.as_of_date,
                    status=ranking_run.status,
                )
        return results

    def _response_from_run(self, run, *, idempotent_replay: bool) -> DailyBatchRunCreateResponse:
        plan = None
        if run.plan_snapshot:
            plan = DailyBatchPlanSnapshot(
                needs_ingest=run.plan_snapshot.get("needs_ingest", False),
                ranking_gaps=run.plan_snapshot.get("ranking_gaps", {}),
                validation_gap_count=run.plan_snapshot.get("validation_gap_count", 0),
                factor_ic_needed=run.plan_snapshot.get("factor_ic_needed", False),
                regime_history_needed=run.plan_snapshot.get("regime_history_needed", False),
                regime_performance_needed=run.plan_snapshot.get("regime_performance_needed", False),
                exit_research_needed=run.plan_snapshot.get("exit_research_needed", False),
                research_intelligence_needed=run.plan_snapshot.get(
                    "research_intelligence_needed", False
                ),
                already_current=run.plan_snapshot.get("already_current", False),
            )
        return DailyBatchRunCreateResponse(
            run_id=str(run.id),
            status=run.status,
            target_trading_day=run.target_trading_day,
            from_date=run.from_date,
            already_current=run.plan_snapshot.get("already_current", False) if run.plan_snapshot else False,
            plan=plan,
            phases=run.phase_results,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_seconds=float(run.duration_seconds) if run.duration_seconds else None,
            idempotent_replay=idempotent_replay,
        )


def build_idempotency_key(target: date, universe_code: str) -> str:
    payload = json.dumps({"target": target.isoformat(), "universe": universe_code}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:32]
