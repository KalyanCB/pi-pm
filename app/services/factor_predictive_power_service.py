from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V1_VERSION,
)
from app.db.repositories.factor_performance_metric_repository import (
    FactorPerformanceMetricRepository,
)
from app.db.repositories.factor_performance_run_repository import FactorPerformanceRunRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.factor_analytics.constants import (
    DATASET_SPLITS,
    DATASET_SPLIT_ALL,
    DATASET_SPLIT_HOLDOUT,
    DATASET_SPLIT_TRAIN,
    DEFAULT_HOLDOUT_START_DATE,
    FACTOR_ANALYTICS_HORIZONS,
    REGIME_LABEL_ALL,
    REGIME_LABELS,
)
from app.factor_analytics.metrics_engine import FactorMetricsEngine
from app.factor_analytics.models import FactorObservation
from app.factor_analytics.observation_loader import FactorObservationLoader
from app.factor_analytics.reports import (
    build_horizon_stability,
    build_leaderboard,
    build_regime_matrix,
    build_train_holdout_drift,
    build_weight_alignment,
    metric_to_dict,
)
from app.factor_analytics.weight_resolver import resolve_factor_weights
from app.factor_analytics.window import include_in_split
from app.models.factor_analytics import FactorPerformanceRun
from app.ranking.registry import RankingStrategyRegistry


class FactorPredictivePowerService:
    def __init__(
        self,
        db: Session,
        metric_repo: FactorPerformanceMetricRepository,
        run_repo: FactorPerformanceRunRepository,
        validation_repo: RankingValidationRepository,
        ranking_run_repo: RankingRunRepository,
        strategy_registry: RankingStrategyRegistry | None = None,
    ) -> None:
        self.db = db
        self.metric_repo = metric_repo
        self.run_repo = run_repo
        self.validation_repo = validation_repo
        self.ranking_run_repo = ranking_run_repo
        self.strategy_registry = strategy_registry or RankingStrategyRegistry()
        self.loader = FactorObservationLoader(db)
        self.engine = FactorMetricsEngine()

    def backfill(
        self,
        *,
        strategy_name: str = RANKING_STRATEGY_BREAKOUT_V1,
        strategy_version: str = RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        universe_code: str,
        start_date: date,
        end_date: date,
        holdout_start_date: date = DEFAULT_HOLDOUT_START_DATE,
        horizons: list[int] | None = None,
        dataset_splits: list[str] | None = None,
        write_daily_metrics: bool = True,
        force_recompute: bool = False,
    ) -> FactorPerformanceRun:
        horizons = list(horizons or FACTOR_ANALYTICS_HORIZONS)
        dataset_splits = list(dataset_splits or DATASET_SPLITS)
        run = self.run_repo.create_running(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            as_of_date_start=start_date,
            as_of_date_end=end_date,
            holdout_start_date=holdout_start_date,
            horizon=None,
            parameter_set={
                "horizons": horizons,
                "dataset_splits": dataset_splits,
                "write_daily_metrics": write_daily_metrics,
                "force_recompute": force_recompute,
            },
        )
        try:
            reports = self.validation_repo.list_completed_with_runs(
                universe_code=universe_code,
                strategy_name=strategy_name,
                strategy_version=strategy_version,
                start_date=start_date,
                end_date=end_date,
            )
            if force_recompute:
                self.metric_repo.delete_metrics_for_window(
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    universe_code=universe_code,
                    as_of_date_start=start_date,
                    as_of_date_end=end_date,
                    holdout_start_date=holdout_start_date,
                )
                self.metric_repo.delete_daily_for_window(
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    universe_code=universe_code,
                    start_date=start_date,
                    end_date=end_date,
                )

            metrics_written = 0
            for horizon in horizons:
                observations = self.loader.load_observations(
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    universe_code=universe_code,
                    start_date=start_date,
                    end_date=end_date,
                    horizon=horizon,
                )
                daily_rows = self.engine.build_daily_metrics(
                    observations,
                    horizon=horizon,
                    holdout_start_date=holdout_start_date,
                )
                if write_daily_metrics:
                    for daily in daily_rows:
                        if daily.ic_spearman is not None:
                            self.metric_repo.upsert_daily(
                                daily,
                                strategy_name=strategy_name,
                                strategy_version=strategy_version,
                                universe_code=universe_code,
                            )

                daily_ic_lookup: dict[tuple[str, str, str], list[float]] = defaultdict(list)
                for daily in daily_rows:
                    if daily.ic_spearman is None:
                        continue
                    daily_ic_lookup[(daily.factor_name, daily.regime_label, daily.dataset_split)].append(
                        daily.ic_spearman
                    )

                factor_names = sorted({obs.factor_name for obs in observations})
                regime_targets = list(REGIME_LABELS) + [REGIME_LABEL_ALL]

                for dataset_split in dataset_splits:
                    total_days = len(
                        {
                            obs.as_of_date
                            for obs in observations
                            if include_in_split(obs.as_of_date, dataset_split, holdout_start_date)
                        }
                    )
                    for regime_label in regime_targets:
                        for factor_name in factor_names:
                            filtered = _filter_observations(
                                observations,
                                factor_name=factor_name,
                                regime_label=regime_label,
                                dataset_split=dataset_split,
                                holdout_start_date=holdout_start_date,
                            )
                            if regime_label == REGIME_LABEL_ALL:
                                split_targets = (
                                    [DATASET_SPLIT_TRAIN, DATASET_SPLIT_HOLDOUT]
                                    if dataset_split == DATASET_SPLIT_ALL
                                    else [dataset_split]
                                )
                                daily_ics = []
                                for regime in REGIME_LABELS:
                                    for split_target in split_targets:
                                        daily_ics.extend(
                                            daily_ic_lookup.get(
                                                (factor_name, regime, split_target), []
                                            )
                                        )
                            elif dataset_split == DATASET_SPLIT_ALL:
                                daily_ics = list(
                                    daily_ic_lookup.get(
                                        (factor_name, regime_label, DATASET_SPLIT_TRAIN), []
                                    )
                                ) + list(
                                    daily_ic_lookup.get(
                                        (factor_name, regime_label, DATASET_SPLIT_HOLDOUT), []
                                    )
                                )
                            else:
                                daily_ics = daily_ic_lookup.get(
                                    (factor_name, regime_label, dataset_split), []
                                )

                            ranked_days = len({obs.as_of_date for obs in filtered})
                            result = self.engine.aggregate_metric(
                                factor_name=factor_name,
                                strategy_name=strategy_name,
                                strategy_version=strategy_version,
                                universe_code=universe_code,
                                horizon=horizon,
                                regime_label=regime_label,
                                dataset_split=dataset_split,
                                observations=filtered,
                                daily_ics=daily_ics,
                                ranked_days_in_regime=ranked_days,
                                total_ranked_days_in_split=total_days,
                                holdout_start_date=holdout_start_date,
                                as_of_date_start=start_date,
                                as_of_date_end=end_date,
                            )
                            if result is None:
                                continue
                            self.metric_repo.upsert_metric(result)
                            metrics_written += 1

            completed = self.run_repo.complete(
                run,
                reports_processed=len(reports),
                metrics_written=metrics_written,
            )
            self.db.commit()
            return completed
        except Exception as exc:
            self.run_repo.fail(run, str(exc))
            self.db.commit()
            raise

    def get_performance(
        self,
        *,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
        universe_code: str | None = None,
        factor_name: str | None = None,
        regime_label: str | None = None,
        horizon: int | None = None,
        dataset_split: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 500,
    ) -> list[dict]:
        rows = self.metric_repo.list_metrics(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            factor_name=factor_name,
            regime_label=regime_label,
            horizon=horizon,
            dataset_split=dataset_split,
            as_of_date_start=start_date,
            as_of_date_end=end_date,
            limit=limit,
        )
        return [metric_to_dict(row) for row in rows]

    def get_leaderboard(
        self,
        *,
        regime_label: str,
        horizon: int,
        strategy_name: str = RANKING_STRATEGY_BREAKOUT_V1,
        strategy_version: str = RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        universe_code: str,
        dataset_split: str = DATASET_SPLIT_HOLDOUT,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_by: str = "ic_spearman",
    ) -> dict:
        holdout_metrics = self.metric_repo.list_metrics(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            regime_label=regime_label,
            horizon=horizon,
            dataset_split=dataset_split,
            as_of_date_start=start_date,
            as_of_date_end=end_date,
            limit=100,
        )
        train_metrics = self.metric_repo.list_metrics(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            regime_label=regime_label,
            horizon=horizon,
            dataset_split=DATASET_SPLIT_TRAIN,
            as_of_date_start=start_date,
            as_of_date_end=end_date,
            limit=100,
        )
        train_by_factor = {m.factor_name: m for m in train_metrics}
        runs = self.ranking_run_repo.list_completed_in_range(
            start_date or date(2000, 1, 1),
            end_date or date.today(),
        )
        weights = resolve_factor_weights(strategy_name, strategy_version, runs, self.strategy_registry)
        payload = build_leaderboard(
            holdout_metrics,
            weights=weights,
            train_by_factor=train_by_factor,
            sort_by=sort_by,
        )
        payload.update(
            {
                "regime_label": regime_label,
                "horizon": horizon,
                "dataset_split": dataset_split,
                "strategy_name": strategy_name,
                "universe_code": universe_code,
            }
        )
        return payload

    def compare_factor(
        self,
        *,
        factor_name: str,
        strategy_name: str = RANKING_STRATEGY_BREAKOUT_V1,
        strategy_version: str = RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        universe_code: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        metrics = self.metric_repo.list_metrics(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            factor_name=factor_name,
            as_of_date_start=start_date,
            as_of_date_end=end_date,
            limit=500,
        )
        by_regime: dict[str, dict] = {}
        by_horizon: dict[int, dict] = {}
        for metric in metrics:
            by_regime.setdefault(metric.regime_label, {})[metric.dataset_split] = metric_to_dict(metric)
            by_horizon.setdefault(metric.horizon, {})[metric.dataset_split] = metric_to_dict(metric)

        train_row = next((m for m in metrics if m.dataset_split == DATASET_SPLIT_TRAIN), None)
        holdout_row = next((m for m in metrics if m.dataset_split == DATASET_SPLIT_HOLDOUT), None)
        train_ic = float(train_row.ic_spearman) if train_row and train_row.ic_spearman is not None else None
        holdout_ic = (
            float(holdout_row.ic_spearman) if holdout_row and holdout_row.ic_spearman is not None else None
        )
        drift = round(train_ic - holdout_ic, 8) if train_ic is not None and holdout_ic is not None else None

        return {
            "factor_name": factor_name,
            "train_ic": train_ic,
            "holdout_ic": holdout_ic,
            "ic_drift": drift,
            "by_regime": by_regime,
            "by_horizon": by_horizon,
            "regime_matrix": build_regime_matrix(metrics, horizon=20, dataset_split=DATASET_SPLIT_HOLDOUT),
            "horizon_stability": build_horizon_stability(
                metrics, regime_label="BULL_LOW_VOL", dataset_split=DATASET_SPLIT_HOLDOUT
            ),
        }

    def get_train_holdout_drift(
        self,
        *,
        regime_label: str = "BULL_LOW_VOL",
        horizon: int = 20,
        strategy_name: str = RANKING_STRATEGY_BREAKOUT_V1,
        strategy_version: str = RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        universe_code: str,
        start_date: date | None = None,
        end_date: date | None = None,
        min_train_ic: float = 0.03,
        holdout_start_date: date = DEFAULT_HOLDOUT_START_DATE,
    ) -> dict:
        train_metrics = self.metric_repo.list_metrics(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            regime_label=regime_label,
            horizon=horizon,
            dataset_split=DATASET_SPLIT_TRAIN,
            as_of_date_start=start_date,
            as_of_date_end=end_date,
            limit=100,
        )
        holdout_metrics = self.metric_repo.list_metrics(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            regime_label=regime_label,
            horizon=horizon,
            dataset_split=DATASET_SPLIT_HOLDOUT,
            as_of_date_start=start_date,
            as_of_date_end=end_date,
            limit=100,
        )
        entries = build_train_holdout_drift(
            train_metrics, holdout_metrics, min_train_ic=min_train_ic
        )
        return {
            "regime_label": regime_label,
            "horizon": horizon,
            "holdout_start_date": holdout_start_date.isoformat(),
            "factors": [
                {
                    "factor_name": entry.factor_name,
                    "train_ic_spearman": entry.train_ic_spearman,
                    "holdout_ic_spearman": entry.holdout_ic_spearman,
                    "ic_drift": entry.ic_drift,
                    "stability_score": entry.stability_score,
                    "regime_coverage_pct": entry.regime_coverage_pct,
                    "verdict": entry.verdict,
                }
                for entry in entries
            ],
        }

    def get_weight_alignment_report(
        self,
        *,
        regime_label: str,
        horizon: int,
        strategy_name: str = RANKING_STRATEGY_BREAKOUT_V1,
        strategy_version: str = RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        universe_code: str,
        dataset_split: str = DATASET_SPLIT_HOLDOUT,
    ) -> dict:
        metrics = self.metric_repo.list_metrics(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            regime_label=regime_label,
            horizon=horizon,
            dataset_split=dataset_split,
            limit=100,
        )
        runs = self.ranking_run_repo.list_completed_in_range(date(2000, 1, 1), date.today())
        weights = resolve_factor_weights(strategy_name, strategy_version, runs, self.strategy_registry)
        return build_weight_alignment(metrics, weights=weights)

    def list_runs(self, *, status: str | None = None, limit: int = 50) -> list[dict]:
        rows = self.run_repo.list_runs(status=status, limit=limit)
        return [_run_to_dict(row) for row in rows]

    def get_run(self, run_id) -> dict | None:
        row = self.run_repo.get_by_id(run_id)
        return _run_to_dict(row) if row else None


def _filter_observations(
    observations: list[FactorObservation],
    *,
    factor_name: str,
    regime_label: str,
    dataset_split: str,
    holdout_start_date: date,
) -> list[FactorObservation]:
    filtered: list[FactorObservation] = []
    for obs in observations:
        if obs.factor_name != factor_name:
            continue
        if regime_label != REGIME_LABEL_ALL and obs.regime_label != regime_label:
            continue
        if not include_in_split(obs.as_of_date, dataset_split, holdout_start_date):
            continue
        filtered.append(obs)
    return filtered


def _run_to_dict(row: FactorPerformanceRun) -> dict:
    return {
        "id": str(row.id),
        "status": row.status,
        "strategy_name": row.strategy_name,
        "strategy_version": row.strategy_version,
        "universe_code": row.universe_code,
        "horizon": row.horizon,
        "as_of_date_start": row.as_of_date_start.isoformat(),
        "as_of_date_end": row.as_of_date_end.isoformat(),
        "holdout_start_date": row.holdout_start_date.isoformat(),
        "reports_processed": row.reports_processed,
        "metrics_written": row.metrics_written,
        "parameter_set": row.parameter_set,
        "started_at": row.started_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "error_message": row.error_message,
    }
