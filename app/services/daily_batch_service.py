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
from app.services.exit_research_service import ExitResearchService
from app.services.factor_predictive_power_service import FactorPredictivePowerService
from app.services.market_data_service import MarketDataService
from app.services.signal_validation_service import SignalValidationService


class DailyBatchService:
    _PHASE_WEIGHTS = {
        DailyBatchPhase.INGEST: 15.0,
        DailyBatchPhase.RANKINGS: 25.0,
        DailyBatchPhase.VALIDATION: 15.0,
        DailyBatchPhase.FACTOR_IC: 22.5,
        DailyBatchPhase.EXIT_RESEARCH: 22.5,
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
        ranking_run_repo: RankingRunRepository,
        run_repo: DailyBatchRunRepository | None = None,
        artifact_repo: DailyBatchArtifactRepository | None = None,
    ) -> None:
        self.db = db
        self.market_data_service = market_data_service
        self.backtest_service = backtest_service
        self.validation_service = validation_service
        self.factor_service = factor_service
        self.exit_service = exit_service
        self.ranking_run_repo = ranking_run_repo
        self.run_repo = run_repo or DailyBatchRunRepository(db)
        self.artifact_repo = artifact_repo or DailyBatchArtifactRepository(db)

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
            exit_research_needed=plan.exit_research_needed,
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
                plan.validation_gap_count > 0 or request.force_recompute
            ):
                self._set_phase(run, DailyBatchPhase.VALIDATION, base_pct)
                result = self.validation_service.backfill(
                    plan.from_date,
                    plan.target_trading_day,
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

            if request.phases.factor_ic and plan.factor_ic_needed:
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
                        start_date=plan.from_date,
                        end_date=plan.target_trading_day,
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
                    }
                base_pct += self._PHASE_WEIGHTS[DailyBatchPhase.FACTOR_IC]

            if request.phases.exit_research and plan.exit_research_needed:
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
                        start_date=plan.from_date,
                        end_date=plan.target_trading_day,
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
                "exit_research_run_ids": grouped.get("exit_research_run", []),
            },
            current_load=run.current_load,
            artifacts=artifacts,
        )

    def _set_phase(self, run, phase: DailyBatchPhase, base_pct: float) -> None:
        self.run_repo.update_progress(
            run,
            current_phase=phase.value,
            percent_complete=base_pct,
            current_load={"phase": phase.value},
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
        batch_size = request.ingest_batch_size
        for offset in range(0, len(symbols), batch_size):
            batch_symbols = symbols[offset : offset + batch_size]
            response = self.market_data_service.ingest(
                batch_symbols,
                IngestPeriod.FIVE_YEARS,
                ingestion_mode=IngestionMode.INCREMENTAL,
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
                exit_research_needed=run.plan_snapshot.get("exit_research_needed", False),
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
