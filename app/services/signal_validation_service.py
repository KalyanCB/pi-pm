from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.constants import RankingRunStatus
from app.core.exceptions import NotFoundError, ValidationError
from app.core.structured_logging import log_event
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.stock_repository import StockRepository
from app.market_data.cache import MarketDataCache
from app.models.ranking_validation_report import RankingValidationReport
from app.services.traceability_service import TraceabilityService
from app.validation.constants import (
    MAX_FORWARD_TRADING_DAYS,
    VALIDATION_HORIZONS,
    VALIDATION_STATUS_COMPLETED,
    VALIDATION_STATUS_INSUFFICIENT_DATA,
)

_BACKFILL_REUSE_STATUSES = frozenset(
    {VALIDATION_STATUS_COMPLETED, VALIDATION_STATUS_INSUFFICIENT_DATA}
)
from app.validation.forward_returns import compute_forward_returns
from app.validation.models import StockForwardReturns
from app.validation.regimes import classify_regime
from app.validation.report_builder import build_validation_report, serialize_horizon_metrics
from app.validation.summary_aggregator import aggregate_cross_run_summary, cross_run_summary_to_dict

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationBackfillResult:
    runs_found: int
    validated: int
    reused: int
    failed: int


class SignalValidationService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        ranking_run_repo: RankingRunRepository,
        ranking_result_repo: RankingResultRepository,
        ranking_performance_repo: RankingPerformanceRepository,
        validation_repo: RankingValidationRepository,
        stock_repo: StockRepository,
        market_data_repo: MarketDataRepository,
        traceability_service: TraceabilityService,
    ) -> None:
        self.db = db
        self.settings = settings
        self.ranking_run_repo = ranking_run_repo
        self.ranking_result_repo = ranking_result_repo
        self.ranking_performance_repo = ranking_performance_repo
        self.validation_repo = validation_repo
        self.stock_repo = stock_repo
        self.market_data_repo = market_data_repo
        self.traceability_service = traceability_service

    def validate_run(
        self, run_id: UUID, *, force_recompute: bool = False
    ) -> RankingValidationReport:
        return self.compute_run(run_id, force_recompute=force_recompute)

    def backfill(
        self,
        start_date: date,
        end_date: date,
        *,
        universe_code: str | None = None,
        force_recompute: bool = False,
    ) -> ValidationBackfillResult:
        if end_date < start_date:
            raise ValidationError("end_date must be on or after start_date")

        runs = self.ranking_run_repo.list_completed_in_range(
            start_date,
            end_date,
            universe_code=universe_code,
        )
        validated = 0
        reused = 0
        failed = 0

        for run in runs:
            existing = self.validation_repo.get_by_ranking_run_id(run.id)
            if (
                existing is not None
                and existing.status in _BACKFILL_REUSE_STATUSES
                and not force_recompute
            ):
                self.traceability_service.ensure_validation_traceability(existing, run)
                reused += 1
                continue

            try:
                self.validate_run(run.id, force_recompute=force_recompute)
                validated += 1
            except ValidationError:
                failed += 1

        return ValidationBackfillResult(
            runs_found=len(runs),
            validated=validated,
            reused=reused,
            failed=failed,
        )

    def compute_run(
        self, run_id: UUID, *, force_recompute: bool = False
    ) -> RankingValidationReport:
        run = self.ranking_run_repo.get_by_id(run_id)
        if run is None:
            raise NotFoundError(f"Ranking run not found: {run_id}")
        if run.status != RankingRunStatus.COMPLETED.value:
            raise ValidationError(f"Ranking run is not completed: {run_id}")

        existing = self.validation_repo.get_by_ranking_run_id(run_id)
        if (
            existing is not None
            and existing.status == VALIDATION_STATUS_COMPLETED
            and not force_recompute
        ):
            self.traceability_service.ensure_validation_traceability(existing, run)
            return existing

        report = existing or self.validation_repo.create_pending(run_id)
        started = time.perf_counter()
        log_event(
            logger,
            "validation_started",
            ranking_run_id=run_id,
            strategy_name=run.strategy_name,
            strategy_version=run.strategy_version,
            as_of_date=run.as_of_date.isoformat(),
        )

        try:
            results = self.ranking_result_repo.list_by_run_id(run_id)
            if not results:
                return self._complete_insufficient(report, run.as_of_date, "No ranked stocks")

            stock_ids = [result.stock_id for result in results]
            snapshots = self.ranking_performance_repo.ensure_snapshots(run_id, stock_ids)
            snapshot_by_stock = {snap.stock_id: snap for snap in snapshots}

            through_date = run.as_of_date + timedelta(days=MAX_FORWARD_TRADING_DAYS * 3)
            cache = MarketDataCache(self.market_data_repo)
            high_vol_threshold = Decimal(str(self.settings.validation_high_vol_threshold))

            benchmark_stock = self.stock_repo.get_by_symbol(run.benchmark_symbol)
            regime = None
            if benchmark_stock is not None:
                bench_bars = cache.load_extended_series(benchmark_stock.id, through_date)
                regime = classify_regime(bench_bars, run.as_of_date, high_vol_threshold)

            stock_returns: list[StockForwardReturns] = []
            symbol_map = {result.stock_id: self._symbol(result.stock_id) for result in results}

            for result in results:
                bars = cache.load_extended_series(result.stock_id, through_date)
                returns = compute_forward_returns(bars, run.as_of_date, VALIDATION_HORIZONS)
                snapshot = snapshot_by_stock[result.stock_id]
                self.ranking_performance_repo.update_returns(snapshot, returns)
                stock_returns.append(
                    StockForwardReturns(
                        stock_id=result.stock_id,
                        symbol=symbol_map[result.stock_id] or str(result.stock_id),
                        score=Decimal(str(result.score)),
                        rank=result.rank,
                        returns=returns,
                    )
                )

            report_data = build_validation_report(
                run_id,
                run.inputs_hash,
                run.as_of_date,
                regime,
                stock_returns,
            )

            if report_data.validation_hash and not force_recompute:
                cached = self.validation_repo.find_completed_by_validation_hash(
                    report_data.validation_hash
                )
                if cached is not None and cached.ranking_run_id != run_id:
                    pass
                elif cached is not None:
                    self.traceability_service.ensure_validation_traceability(cached, run)
                    return cached

            completed = self.validation_repo.complete(
                report,
                validation_hash=report_data.validation_hash,
                regime_label=report_data.regime.regime_label if report_data.regime else None,
                trend_regime=report_data.regime.trend_regime if report_data.regime else None,
                vol_regime=report_data.regime.vol_regime if report_data.regime else None,
                status=report_data.status,
                horizon_metrics=serialize_horizon_metrics(report_data.horizon_metrics),
                sample_summary=report_data.sample_summary,
            )
            horizon_metrics = serialize_horizon_metrics(report_data.horizon_metrics)
            if completed.status == VALIDATION_STATUS_COMPLETED and horizon_metrics:
                self.traceability_service.record_validation_traceability(
                    completed, run, horizon_metrics
                )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            self.db.commit()
            log_event(
                logger,
                "validation_completed",
                validation_report_id=completed.id,
                ranking_run_id=run_id,
                status=completed.status,
                regime_label=completed.regime_label,
                execution_duration_ms=elapsed_ms,
            )
            return completed
        except ValidationError:
            raise
        except Exception as exc:
            self.validation_repo.fail(report, str(exc))
            self.db.commit()
            raise ValidationError(str(exc)) from exc

    def get_report(self, run_id: UUID) -> RankingValidationReport:
        report = self.validation_repo.get_by_ranking_run_id(run_id)
        if report is None:
            raise NotFoundError(f"Validation report not found for run: {run_id}")
        return report

    def get_snapshots(self, run_id: UUID):
        run = self.ranking_run_repo.get_by_id(run_id)
        if run is None:
            raise NotFoundError(f"Ranking run not found: {run_id}")
        return self.ranking_performance_repo.get_by_run_id(run_id)

    def get_summary(
        self,
        *,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        horizon: int = 20,
    ) -> dict:
        completed_reports = self.validation_repo.list_completed_with_runs(
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            start_date=start_date,
            end_date=end_date,
        )
        all_reports = self.validation_repo.list_reports_with_runs(
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            start_date=start_date,
            end_date=end_date,
        )
        summary = aggregate_cross_run_summary(
            completed_reports,
            horizon=horizon,
            all_reports=all_reports,
        )
        return cross_run_summary_to_dict(summary)

    def get_backtest_summary(
        self,
        *,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        if start_date is None or end_date is None:
            raise ValidationError("start_date and end_date are required for backtest summary")

        runs = self.ranking_run_repo.list_completed_in_range(
            start_date,
            end_date,
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
        )
        validated = self.validation_repo.list_completed_with_runs(
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            start_date=start_date,
            end_date=end_date,
        )
        return {
            "universe_code": universe_code,
            "strategy_name": strategy_name,
            "strategy_version": strategy_version,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "ranking_runs_total": len(runs),
            "validated_runs_total": len(validated),
            "pending_validation_runs": len(runs) - len(validated),
        }

    def _complete_insufficient(self, report, as_of_date, reason: str) -> RankingValidationReport:
        completed = self.validation_repo.complete(
            report,
            validation_hash=None,
            regime_label=None,
            trend_regime=None,
            vol_regime=None,
            status=VALIDATION_STATUS_INSUFFICIENT_DATA,
            horizon_metrics={},
            sample_summary={"reason": reason, "as_of_date": as_of_date.isoformat()},
        )
        self.db.commit()
        return completed

    def _symbol(self, stock_id: UUID) -> str | None:
        stock = self.stock_repo.get_by_id(stock_id)
        return stock.symbol if stock else None
