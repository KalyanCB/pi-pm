from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V1_VERSION,
)
from app.db.repositories.exit_research_metric_repository import ExitResearchMetricRepository
from app.db.repositories.exit_research_run_repository import ExitResearchRunRepository
from app.factor_analytics.constants import DATASET_SPLITS, DEFAULT_HOLDOUT_START_DATE
from app.models.exit_research import ExitResearchRun
from app.workspace_exit_research.constants import DEFAULT_RESEARCH_HORIZON, REGIME_LABEL_ALL, REGIME_LABELS
from app.workspace_exit_research.data_cache import RankPathCache, RegimePathCache, ResearchBarCache
from app.workspace_exit_research.policy_simulators import (
    ExitMetricsEngine,
    alpha_decay_returns,
    filter_entries,
    run_all_simulations,
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
    ) -> None:
        self.db = db
        self.run_repo = run_repo
        self.metric_repo = metric_repo
        self.loader = SignalCohortLoader(db)
        self.engine = ExitMetricsEngine()

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
            parameter_set={"dataset_splits": list(DATASET_SPLITS)},
        )
        try:
            if force_recompute:
                self.metric_repo.delete_for_run(run.id)

            entries = self.loader.load_entries(
                strategy_name=strategy_name,
                strategy_version=strategy_version,
                universe_code=universe_code,
                start_date=start_date,
                end_date=end_date,
                holdout_start_date=holdout_start_date,
            )
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

            for entry in entries:
                bars = bar_cache.get(entry.stock_id)
                if not bars:
                    continue
                sims = run_all_simulations(entry, bars, rank_cache, regime_cache)
                entry_sims[(entry.ranking_run_id, entry.stock_id)] = sims
                decay = alpha_decay_returns(entry, bars)
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

            variant_keys: set[tuple[str, str]] = set()
            for sims in entry_sims.values():
                if isinstance(sims, list):
                    for sim in sims:
                        variant_keys.add((sim.policy_family, sim.policy_variant))

            metrics_written = 0
            regime_targets = list(REGIME_LABELS) + [REGIME_LABEL_ALL]
            for family, variant in sorted(variant_keys):
                for dataset_split in DATASET_SPLITS:
                    for regime_label in regime_targets:
                        matching = []
                        for entry in filter_entries(
                            entries,
                            regime_label=regime_label,
                            dataset_split=dataset_split,
                            holdout_start_date=holdout_start_date,
                        ):
                            sims = entry_sims.get((entry.ranking_run_id, entry.stock_id), [])
                            for sim in sims:
                                if sim.policy_family == family and sim.policy_variant == variant:
                                    matching.append(sim)
                                    break
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

            completed = self.run_repo.complete(
                run,
                signals_processed=len(entries),
                metrics_written=metrics_written,
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
                "strategy_name": r.strategy_name,
                "universe_code": r.universe_code,
                "signals_processed": r.signals_processed,
                "metrics_written": r.metrics_written,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in self.run_repo.list_runs(limit=limit)
        ]
