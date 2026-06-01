from __future__ import annotations

import time
from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V1_VERSION,
    ExitResearchPhase,
)
from app.db.repositories.exit_research_metric_repository import ExitResearchMetricRepository
from app.db.repositories.exit_research_run_repository import ExitResearchRunRepository
from app.factor_analytics.constants import DATASET_SPLITS, DEFAULT_HOLDOUT_START_DATE
from app.models.exit_research import ExitResearchRun
from app.workspace_exit_research.aggregation_index import (
    build_policy_metric_buckets,
    count_alpha_persist_items,
    count_policy_persist_items,
)
from app.workspace_exit_research.constants import (
    ALPHA_DECAY_MAX_DAYS,
    DEFAULT_RESEARCH_HORIZON,
    PERSIST_COMMIT_INTERVAL,
    POLICY_FAMILY_ALPHA_DECAY,
    POLICY_FAMILY_FIXED_HOLD,
    POLICY_FAMILY_RANK_DETERIORATION,
    POLICY_FAMILY_REGIME_EXIT,
    POLICY_FAMILY_TREND_FAILURE,
    REGIME_LABEL_ALL,
)
from app.workspace_exit_research.data_cache import RankPathCache, RegimePathCache, ResearchBarCache
from app.workspace_exit_research.policy_simulators import (
    ExitMetricsEngine,
    alpha_decay_returns,
    filter_entries,
    run_fixed_hold_batch,
    run_rank_deterioration_batch,
    run_regime_exit_batch,
    run_trend_failure_batch,
)
from app.workspace_exit_research.progress import (
    log_alpha_decay_progress,
    log_backfill_complete,
    log_backfill_startup,
    log_entry_progress,
    log_phase_changed,
    log_persist_progress,
    log_policy_batch_completed,
    persistence_progress_fields,
    should_log_persist_progress,
    should_log_progress,
    simulation_progress_fields,
)
from app.workspace_exit_research.reports import (
    build_exit_policy_comparison,
    build_family_report,
    build_recommended_exit_policy,
)
from app.workspace_exit_research.signal_cohort_loader import SignalCohortLoader


class ExitResearchService:
    def __init__(
        self,
        db: Session,
        run_repo: ExitResearchRunRepository,
        metric_repo: ExitResearchMetricRepository,
        *,
        persist_commit_interval: int = PERSIST_COMMIT_INTERVAL,
    ) -> None:
        self.db = db
        self.run_repo = run_repo
        self.metric_repo = metric_repo
        self.loader = SignalCohortLoader(db)
        self.engine = ExitMetricsEngine()
        self.persist_commit_interval = persist_commit_interval

    def _transition_phase(self, run: ExitResearchRun, phase: ExitResearchPhase, *, strategy_name: str) -> None:
        self.run_repo.set_phase(run, phase)
        self.db.commit()
        log_phase_changed(strategy_name=strategy_name, phase=phase.value)

    def _maybe_commit_persistence(self, run: ExitResearchRun, items_written: int) -> None:
        if items_written > 0 and items_written % self.persist_commit_interval == 0:
            self.db.commit()

    def _record_simulation_progress(
        self,
        run: ExitResearchRun,
        *,
        strategy_name: str,
        processed: int,
        total: int,
        progress_started: float,
    ) -> None:
        if not should_log_progress(processed, total):
            return
        fields = simulation_progress_fields(processed, total, progress_started)
        self.run_repo.update_progress(
            run,
            processed_entries=fields["processed_entries"],
            percent_complete=fields["percent_complete"],
            elapsed_seconds=fields["elapsed_seconds"],
        )
        self.db.commit()
        log_entry_progress(
            strategy_name=strategy_name,
            processed=processed,
            total=total,
            started_monotonic=progress_started,
        )

    def _record_persistence_progress(
        self,
        run: ExitResearchRun,
        *,
        strategy_name: str,
        phase: ExitResearchPhase,
        processed: int,
        total: int,
        progress_started: float,
    ) -> None:
        if not should_log_persist_progress(processed, total):
            return
        fields = persistence_progress_fields(processed, total, progress_started)
        self.run_repo.update_persistence_progress(
            run,
            persistence_items_processed=fields["persistence_items_processed"],
            percent_complete=fields["percent_complete"],
            elapsed_seconds=fields["elapsed_seconds"],
        )
        self.db.commit()
        log_persist_progress(
            strategy_name=strategy_name,
            phase=phase.value,
            processed=processed,
            total=total,
            started_monotonic=progress_started,
        )

    def backfill(
        self,
        *,
        strategy_name: str = RANKING_STRATEGY_BREAKOUT_V1,
        strategy_version: str = RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        universe_code: str,
        start_date: date,
        end_date: date,
        holdout_start_date: date = DEFAULT_HOLDOUT_START_DATE,
        force_recompute: bool = False,
    ) -> ExitResearchRun:
        run = self.run_repo.create_running(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            as_of_date_start=start_date,
            as_of_date_end=end_date,
            holdout_start_date=holdout_start_date,
            parameter_set={
                "dataset_splits": list(DATASET_SPLITS),
                "persist_commit_interval": self.persist_commit_interval,
            },
        )
        self.db.commit()
        backfill_started = time.monotonic()
        try:
            if force_recompute:
                self.metric_repo.delete_for_run(run.id)
                self.db.commit()

            self._transition_phase(run, ExitResearchPhase.COLLECTING_ENTRIES, strategy_name=strategy_name)
            entries = self.loader.load_entries(
                strategy_name=strategy_name,
                strategy_version=strategy_version,
                universe_code=universe_code,
                start_date=start_date,
                end_date=end_date,
                holdout_start_date=holdout_start_date,
            )
            total_entries = len(entries)
            self.run_repo.set_total_entries(run, total_entries)
            self.db.commit()

            progress_started = log_backfill_startup(
                strategy_name=strategy_name,
                strategy_version=strategy_version,
                universe_code=universe_code,
                start_date=start_date,
                end_date=end_date,
                total_entries=total_entries,
            )

            self._transition_phase(run, ExitResearchPhase.SIMULATING, strategy_name=strategy_name)

            stock_ids = {e.stock_id for e in entries}
            bar_cache = ResearchBarCache(self.db)
            bar_cache.load_for_stocks(stock_ids, start_date=start_date, end_date=end_date)
            rank_cache = RankPathCache(self.db)
            rank_cache.load(
                strategy_name=strategy_name,
                strategy_version=strategy_version,
                universe_code=universe_code,
                stock_ids=stock_ids,
                start_date=start_date,
                end_date=end_date,
            )
            regime_cache = RegimePathCache(self.db)
            regime_cache.load(start_date=start_date, end_date=end_date)

            entry_sims: dict[tuple, list] = {}
            alpha_by_stratum: dict[tuple[str, str], dict[int, list[Decimal]]] = defaultdict(
                lambda: defaultdict(list)
            )
            simulations_generated = 0
            alpha_points_generated = 0
            entries_with_bars = 0

            for entry in entries:
                bars = bar_cache.get(entry.stock_id)
                if not bars:
                    continue
                entries_with_bars += 1
                key = (entry.ranking_run_id, entry.stock_id)
                sims: list = []
                sims.extend(run_fixed_hold_batch(entry, bars))
                sims.extend(run_rank_deterioration_batch(entry, bars, rank_cache))
                sims.extend(run_regime_exit_batch(entry, bars, regime_cache))
                sims.extend(run_trend_failure_batch(entry, bars))
                entry_sims[key] = sims
                simulations_generated += len(sims)

                decay = alpha_decay_returns(entry, bars)
                alpha_points_generated += sum(1 for ret in decay.values() if ret is not None)
                for regime in [REGIME_LABEL_ALL, entry.regime_label]:
                    for split in DATASET_SPLITS:
                        if not filter_entries(
                            [entry],
                            regime_label=regime,
                            dataset_split=split,
                            holdout_start_date=holdout_start_date,
                        ):
                            continue
                        for day, ret in decay.items():
                            if ret is not None:
                                alpha_by_stratum[(regime, split)][day].append(ret)

                self._record_simulation_progress(
                    run,
                    strategy_name=strategy_name,
                    processed=entries_with_bars,
                    total=total_entries,
                    progress_started=progress_started,
                )

            log_policy_batch_completed(POLICY_FAMILY_FIXED_HOLD, entries=entries_with_bars)
            log_policy_batch_completed(POLICY_FAMILY_RANK_DETERIORATION, entries=entries_with_bars)
            log_policy_batch_completed(POLICY_FAMILY_REGIME_EXIT, entries=entries_with_bars)
            log_policy_batch_completed(POLICY_FAMILY_TREND_FAILURE, entries=entries_with_bars)

            self._transition_phase(run, ExitResearchPhase.AGGREGATING_METRICS, strategy_name=strategy_name)

            policy_buckets = build_policy_metric_buckets(
                entries,
                entry_sims,
                holdout_start_date=holdout_start_date,
            )
            policy_persist_total = count_policy_persist_items(policy_buckets)
            alpha_persist_total = count_alpha_persist_items(len(alpha_by_stratum), trading_days=ALPHA_DECAY_MAX_DAYS)
            persistence_total = policy_persist_total + alpha_persist_total
            self.run_repo.set_persistence_totals(run, persistence_items_total=persistence_total)
            self.db.commit()

            metrics_written = 0
            persist_processed = 0

            self._transition_phase(
                run,
                ExitResearchPhase.PERSISTING_POLICY_METRICS,
                strategy_name=strategy_name,
            )

            for (family, variant, regime_label, dataset_split), matching in sorted(policy_buckets.items()):
                if not matching:
                    continue
                result = self.engine.aggregate_policy(
                    matching,
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    universe_code=universe_code,
                    regime_label=regime_label,
                    dataset_split=dataset_split,
                    horizon=DEFAULT_RESEARCH_HORIZON,
                    holdout_start_date=holdout_start_date,
                    as_of_date_start=start_date,
                    as_of_date_end=end_date,
                )
                if result:
                    self.metric_repo.upsert_policy_metric(run.id, result)
                    metrics_written += 1
                    persist_processed += 1
                    self._maybe_commit_persistence(run, persist_processed)
                    self._record_persistence_progress(
                        run,
                        strategy_name=strategy_name,
                        phase=ExitResearchPhase.PERSISTING_POLICY_METRICS,
                        processed=persist_processed,
                        total=persistence_total,
                        progress_started=progress_started,
                    )

            self.db.commit()

            self._transition_phase(
                run,
                ExitResearchPhase.PERSISTING_ALPHA_DECAY,
                strategy_name=strategy_name,
            )

            alpha_rows_written = 0
            for (regime_label, dataset_split), day_map in alpha_by_stratum.items():
                for point in self.engine.aggregate_alpha_decay(
                    day_map, regime_label=regime_label, dataset_split=dataset_split
                ):
                    self.metric_repo.upsert_alpha_decay_point(
                        run.id,
                        strategy_name=strategy_name,
                        strategy_version=strategy_version,
                        universe_code=universe_code,
                        holdout_start_date=holdout_start_date,
                        as_of_date_start=start_date,
                        as_of_date_end=end_date,
                        point=point,
                    )
                    metrics_written += 1
                    alpha_rows_written += 1
                    persist_processed += 1
                    self._maybe_commit_persistence(run, persist_processed)
                    self._record_persistence_progress(
                        run,
                        strategy_name=strategy_name,
                        phase=ExitResearchPhase.PERSISTING_ALPHA_DECAY,
                        processed=persist_processed,
                        total=persistence_total,
                        progress_started=progress_started,
                    )

            self.db.commit()

            log_alpha_decay_progress(
                entries_processed=entries_with_bars,
                alpha_points_generated=alpha_points_generated,
                alpha_rows_written=alpha_rows_written,
            )
            log_policy_batch_completed(POLICY_FAMILY_ALPHA_DECAY, entries=entries_with_bars)

            self._transition_phase(run, ExitResearchPhase.FINALIZING, strategy_name=strategy_name)

            runtime_sec = time.monotonic() - backfill_started
            log_backfill_complete(
                strategy_name=strategy_name,
                runtime_sec=runtime_sec,
                simulations_generated=simulations_generated,
                alpha_points_generated=alpha_points_generated,
                database_rows_written=metrics_written,
                signals_processed=len(entries),
            )

            completed = self.run_repo.complete(
                run,
                signals_processed=len(entries),
                metrics_written=metrics_written,
            )
            self.run_repo.update_progress(
                completed,
                processed_entries=entries_with_bars,
                percent_complete=100.0,
                elapsed_seconds=round(runtime_sec, 2),
            )
            self.db.commit()
            return completed
        except Exception as exc:
            self.run_repo.fail(run, str(exc))
            self.db.commit()
            raise

    def get_policy_comparison(self, **filters) -> dict:
        return build_exit_policy_comparison(self.metric_repo.list_policy_metrics(**filters))

    def get_family_report(self, policy_family: str, report_name: str, **filters) -> dict:
        metrics = self.metric_repo.list_policy_metrics(policy_family=policy_family, **filters)
        return build_family_report(metrics, policy_family=policy_family, report_name=report_name)

    def get_alpha_decay_report(self, **filters) -> dict:
        points = self.metric_repo.list_alpha_decay(**filters)
        return {
            "report": "alpha_decay_analysis",
            "curve": [
                {
                    "trading_day": p.trading_day,
                    "regime_label": p.regime_label,
                    "dataset_split": p.dataset_split,
                    "sample_size": p.sample_size,
                    "mean_return": float(p.mean_return) if p.mean_return is not None else None,
                    "cumulative_mean_return": (
                        float(p.cumulative_mean_return) if p.cumulative_mean_return is not None else None
                    ),
                    "conclusion_status": p.conclusion_status,
                }
                for p in points
            ],
        }

    def get_recommended_policy(self, *, dataset_split: str = "HOLDOUT", **filters) -> dict:
        return build_recommended_exit_policy(
            self.metric_repo.list_policy_metrics(**filters),
            dataset_split=dataset_split,
        )

    def list_runs(self, limit: int = 50) -> list[dict]:
        return [
            {
                "id": str(r.id),
                "status": r.status,
                "current_phase": r.current_phase,
                "strategy_name": r.strategy_name,
                "universe_code": r.universe_code,
                "signals_processed": r.signals_processed,
                "metrics_written": r.metrics_written,
                "total_entries": r.total_entries,
                "processed_entries": r.processed_entries,
                "percent_complete": float(r.percent_complete) if r.percent_complete is not None else None,
                "persistence_items_total": r.persistence_items_total,
                "persistence_items_processed": r.persistence_items_processed,
                "elapsed_seconds": float(r.elapsed_seconds) if r.elapsed_seconds is not None else None,
                "last_progress_at": r.last_progress_at.isoformat() if r.last_progress_at else None,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in self.run_repo.list_runs(limit=limit)
        ]
