from __future__ import annotations

import logging
import time
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.constants import (
    LineageEntityType,
    LineageRelationshipType,
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V1_VERSION,
)
from app.core.structured_logging import log_event
from app.db.repositories.experiment_run_repository import ExperimentRunRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.regime_backtest_run_repository import RegimeBacktestRunRepository
from app.db.repositories.regime_policy_config_repository import RegimePolicyConfigRepository
from app.db.repositories.regime_policy_decision_repository import RegimePolicyDecisionRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.validation_metrics_repository import ValidationMetricsRepository
from app.models.regime_policy import RegimeBacktestRun, RegimePolicyConfig
from app.regime_policy.engine import PolicyConfigSpec, RegimePolicyEngine, breakout_v1_preset_specs
from app.regime_policy.metrics import build_research_findings, compare_spread_significance
from app.regime_policy.models import PolicyEvaluationContext, ReplayWindowSpec
from app.regime_policy.replay import RegimePolicyReplayService, build_single_holdout_window
from app.regime_policy.scored_returns_loader import (
    batch_load_scored_returns_by_run,
    count_scored_returns_by_run,
)
from app.services.experiment_service import ExperimentService

logger = logging.getLogger(__name__)


class RegimePolicyPresetService:
    """Load E1-E4 draft configurations without embedding them in migrations."""

    def __init__(self, config_repo: RegimePolicyConfigRepository) -> None:
        self.config_repo = config_repo

    def load_breakout_v1_presets(self, *, dry_run: bool = False) -> list[RegimePolicyConfig]:
        created: list[RegimePolicyConfig] = []
        for spec in breakout_v1_preset_specs():
            existing = self.config_repo.find_by_name_and_version(spec.policy_name, 1)
            if existing is not None:
                created.append(existing)
                continue
            if dry_run:
                continue
            config = self.config_repo.create(
                policy_name=spec.policy_name,
                policy_type=spec.policy_type,
                strategy_name=spec.strategy_name,
                strategy_version=spec.strategy_version,
                policy_version=1,
                allowed_regimes=spec.allowed_regimes,
                size_multipliers=spec.size_multipliers,
                min_decile=spec.min_decile,
                max_decile=spec.max_decile,
                default_action=spec.default_action,
                notes=spec.notes,
            )
            created.append(config)
        return created


class RegimePolicyService:
    def __init__(
        self,
        db: Session,
        config_repo: RegimePolicyConfigRepository,
        decision_repo: RegimePolicyDecisionRepository,
        backtest_repo: RegimeBacktestRunRepository,
        validation_repo: RankingValidationRepository,
        validation_metrics_repo: ValidationMetricsRepository,
        ranking_run_repo: RankingRunRepository,
        lineage_repo: RunLineageRepository,
        experiment_service: ExperimentService,
        preset_service: RegimePolicyPresetService,
        engine: RegimePolicyEngine | None = None,
    ) -> None:
        self.db = db
        self.config_repo = config_repo
        self.decision_repo = decision_repo
        self.backtest_repo = backtest_repo
        self.validation_repo = validation_repo
        self.validation_metrics_repo = validation_metrics_repo
        self.ranking_run_repo = ranking_run_repo
        self.lineage_repo = lineage_repo
        self.experiment_service = experiment_service
        self.preset_service = preset_service
        self.engine = engine or RegimePolicyEngine()
        self.replay_service = RegimePolicyReplayService(db, validation_repo, self.engine)

    def list_configs(
        self,
        *,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
        policy_type: str | None = None,
        status: str | None = None,
    ) -> list[RegimePolicyConfig]:
        return self.config_repo.list_configs(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            policy_type=policy_type,
            status=status,
        )

    def create_config(
        self,
        *,
        policy_name: str,
        policy_type: str,
        strategy_name: str,
        strategy_version: str,
        allowed_regimes: list[str],
        size_multipliers: dict[str, float],
        min_decile: int | None,
        max_decile: int | None,
        default_action: str,
        notes: str | None = None,
    ) -> RegimePolicyConfig:
        version = self.config_repo.get_next_version(policy_name)
        config = self.config_repo.create(
            policy_name=policy_name,
            policy_type=policy_type,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            policy_version=version,
            allowed_regimes=allowed_regimes,
            size_multipliers=size_multipliers,
            min_decile=min_decile,
            max_decile=max_decile,
            default_action=default_action,
            notes=notes,
        )
        self.db.commit()
        return config

    def activate_config(self, config_id: UUID) -> RegimePolicyConfig:
        config = self.config_repo.get_by_id(config_id)
        if config is None:
            raise ValueError(f"Policy config not found: {config_id}")
        activated = self.config_repo.activate(config)
        log_event(
            logger,
            "regime_policy_config_activated",
            policy_config_id=activated.id,
            policy_name=activated.policy_name,
            policy_type=activated.policy_type,
        )
        self.db.commit()
        return activated

    def load_presets(self, *, dry_run: bool = False) -> list[RegimePolicyConfig]:
        configs = self.preset_service.load_breakout_v1_presets(dry_run=dry_run)
        if not dry_run:
            self.db.commit()
        return configs

    def evaluate(
        self,
        *,
        ranking_run_id: UUID,
        policy_config_id: UUID | None = None,
        persist: bool = False,
        experiment_run_id: UUID | None = None,
    ) -> dict:
        run = self.ranking_run_repo.get_by_id(ranking_run_id)
        if run is None:
            raise ValueError(f"Ranking run not found: {ranking_run_id}")

        config = self._resolve_config(policy_config_id, run.strategy_name, run.strategy_version)
        spec = self._config_to_spec(config)
        regime = run.regime_label
        report = self.validation_repo.get_by_ranking_run_id(ranking_run_id)
        if report and report.regime_label:
            regime = report.regime_label

        decision = self.engine.evaluate_run(spec, PolicyEvaluationContext(regime_label=regime))
        log_event(
            logger,
            "regime_policy_evaluated",
            ranking_run_id=ranking_run_id,
            policy_config_id=config.id,
            action=decision.action,
            regime_label=regime,
        )

        if persist:
            self.decision_repo.create(
                policy_config_id=config.id,
                ranking_run_id=ranking_run_id,
                validation_report_id=report.id if report else None,
                as_of_date=run.as_of_date,
                regime_label=regime,
                action=decision.action,
                size_multiplier=float(decision.size_multiplier),
                decile_filter=decision.decile_filter,
                reason=decision.reason,
                experiment_run_id=experiment_run_id,
            )
            self.db.commit()

        return {
            "policy_config_id": str(config.id),
            "ranking_run_id": str(ranking_run_id),
            "as_of_date": run.as_of_date.isoformat(),
            "regime_label": regime,
            "action": decision.action,
            "size_multiplier": float(decision.size_multiplier),
            "decile_filter": decision.decile_filter,
            "reason": decision.reason,
        }

    def list_decisions(
        self,
        *,
        ranking_run_id: UUID | None = None,
        as_of_date: date | None = None,
        regime_label: str | None = None,
        action: str | None = None,
        experiment_run_id: UUID | None = None,
        limit: int = 100,
    ) -> list[dict]:
        rows = self.decision_repo.list_decisions(
            ranking_run_id=ranking_run_id,
            as_of_date=as_of_date,
            regime_label=regime_label,
            action=action,
            experiment_run_id=experiment_run_id,
            limit=limit,
        )
        return [_decision_to_dict(row) for row in rows]

    def run_backtest_comparison(
        self,
        *,
        strategy_name: str = RANKING_STRATEGY_BREAKOUT_V1,
        strategy_version: str = RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        universe_code: str,
        horizon: int,
        start_date: date,
        end_date: date,
        holdout_start_date: date,
        policy_config_ids: list[UUID],
        baseline_policy_config_id: UUID,
        experiment_name: str,
        persist_decisions: bool = True,
    ) -> dict:
        t_start = time.perf_counter()
        experiment = self.experiment_service.start(
            experiment_name=experiment_name,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            parameter_set={
                "horizon": horizon,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "holdout_start_date": holdout_start_date.isoformat(),
                "policy_config_ids": [str(pid) for pid in policy_config_ids],
                "baseline_policy_config_id": str(baseline_policy_config_id),
                "universe_code": universe_code,
            },
            notes="Sprint 8.1 regime policy backtest comparison",
        )
        log_event(
            logger,
            "regime_backtest_started",
            experiment_id=experiment.id,
            experiment_name=experiment_name,
            policy_count=len(policy_config_ids),
        )

        window_spec = build_single_holdout_window(start_date, end_date, holdout_start_date)

        t_policies = time.perf_counter()
        baseline_config = self.config_repo.get_by_id(baseline_policy_config_id)
        if baseline_config is None:
            raise ValueError(f"Baseline config not found: {baseline_policy_config_id}")
        baseline_spec = self._config_to_spec(baseline_config)
        log_event(
            logger,
            "regime_backtest_policies_loaded",
            experiment_id=experiment.id,
            duration_ms=int((time.perf_counter() - t_policies) * 1000),
        )

        t_reports = time.perf_counter()
        reports = self.validation_repo.list_completed_with_runs(
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            start_date=start_date,
            end_date=end_date,
        )
        report_ids = [report.id for report in reports]
        horizon_spreads_by_report = self.validation_metrics_repo.spreads_by_report_for_horizon(
            report_ids,
            horizon,
        )
        horizon_sample_sizes_by_report = (
            self.validation_metrics_repo.sample_sizes_by_report_for_horizon(
                report_ids,
                horizon,
            )
        )
        run_ids = [
            report.ranking_run.id for report in reports if report.ranking_run is not None
        ]
        scored_by_run = batch_load_scored_returns_by_run(self.db, run_ids, horizon)
        runs_with_data, total_scored_rows = count_scored_returns_by_run(scored_by_run)
        log_event(
            logger,
            "regime_backtest_data_loaded",
            experiment_id=experiment.id,
            report_count=len(reports),
            horizon_metric_count=len(horizon_spreads_by_report),
            horizon_sample_count=len(horizon_sample_sizes_by_report),
            scored_run_count=len(scored_by_run),
            runs_with_scored_data=runs_with_data,
            total_scored_rows=total_scored_rows,
            duration_ms=int((time.perf_counter() - t_reports) * 1000),
        )

        t_baseline_spreads = time.perf_counter()
        baseline_spreads = self.replay_service.compute_daily_spreads_by_date(
            reports,
            baseline_spec,
            horizon,
            scored_by_run=scored_by_run,
            horizon_spreads_by_report=horizon_spreads_by_report,
        )
        log_event(
            logger,
            "regime_backtest_baseline_spreads_computed",
            experiment_id=experiment.id,
            spread_days=len(baseline_spreads),
            duration_ms=int((time.perf_counter() - t_baseline_spreads) * 1000),
        )

        t_baseline_replay = time.perf_counter()
        baseline_replay = self.replay_service.replay(
            policy_config_id=baseline_policy_config_id,
            config=baseline_spec,
            window_spec=window_spec,
            horizon=horizon,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            universe_code=universe_code,
            reports=reports,
            scored_by_run=scored_by_run,
            horizon_spreads_by_report=horizon_spreads_by_report,
            horizon_sample_sizes_by_report=horizon_sample_sizes_by_report,
        )
        baseline_holdout_metrics = baseline_replay.holdout_metrics
        log_event(
            logger,
            "regime_backtest_baseline_replay_completed",
            experiment_id=experiment.id,
            duration_ms=int((time.perf_counter() - t_baseline_replay) * 1000),
        )

        backtest_runs: list[RegimeBacktestRun] = []
        summary: dict[str, dict] = {}

        for policy_id in policy_config_ids:
            config = self.config_repo.get_by_id(policy_id)
            if config is None:
                raise ValueError(f"Policy config not found: {policy_id}")
            spec = self._config_to_spec(config)
            bt_run = self.backtest_repo.create_running(
                experiment_run_id=experiment.id,
                policy_config_id=config.id,
                baseline_policy_config_id=baseline_policy_config_id,
                strategy_name=strategy_name,
                strategy_version=strategy_version,
                universe_code=universe_code,
                horizon=horizon,
                window_spec=window_spec.to_dict(),
                start_date=start_date,
                end_date=end_date,
                holdout_start_date=holdout_start_date,
            )
            self.db.flush()
            log_event(
                logger,
                "regime_backtest_run_created",
                experiment_id=experiment.id,
                backtest_run_id=bt_run.id,
                policy_type=config.policy_type,
            )
            try:
                t_replay = time.perf_counter()
                replay = self.replay_service.replay(
                    policy_config_id=config.id,
                    config=spec,
                    window_spec=window_spec,
                    horizon=horizon,
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    universe_code=universe_code,
                    reports=reports,
                    scored_by_run=scored_by_run,
                    horizon_spreads_by_report=horizon_spreads_by_report,
                    horizon_sample_sizes_by_report=horizon_sample_sizes_by_report,
                )
                log_event(
                    logger,
                    "regime_backtest_replay_completed",
                    experiment_id=experiment.id,
                    backtest_run_id=bt_run.id,
                    policy_type=config.policy_type,
                    duration_ms=int((time.perf_counter() - t_replay) * 1000),
                )
                if persist_decisions:
                    for day in replay.day_results:
                        self.decision_repo.create(
                            policy_config_id=config.id,
                            ranking_run_id=day.ranking_run_id,
                            validation_report_id=day.validation_report_id,
                            as_of_date=day.as_of_date,
                            regime_label=day.regime_label,
                            action=day.decision.action,
                            size_multiplier=float(day.decision.size_multiplier),
                            decile_filter=day.decision.decile_filter,
                            reason=day.decision.reason,
                            experiment_run_id=experiment.id,
                        )
                for report_id in replay.validation_report_ids:
                    self.lineage_repo.link(
                        child_entity_type=LineageEntityType.EXPERIMENT_RUN.value,
                        child_entity_id=experiment.id,
                        parent_entity_type=LineageEntityType.VALIDATION_REPORT.value,
                        parent_entity_id=report_id,
                        relationship_type=LineageRelationshipType.POLICY_BACKTEST_USES_VALIDATION.value,
                    )

                policy_spreads = self.replay_service.compute_daily_spreads_by_date(
                    reports,
                    spec,
                    horizon,
                    scored_by_run=scored_by_run,
                    horizon_spreads_by_report=horizon_spreads_by_report,
                )
                holdout_dates = [
                    d for d in sorted(policy_spreads)
                    if d >= holdout_start_date
                ]
                baseline_holdout = [baseline_spreads[d] for d in holdout_dates if d in baseline_spreads]
                policy_holdout = [policy_spreads[d] for d in holdout_dates if d in policy_spreads]
                spread_sig = compare_spread_significance(policy_holdout, baseline_holdout)

                holdout = replay.holdout_metrics
                findings_metrics = (
                    holdout if holdout.ranked_days > 0 else replay.train_metrics
                )
                if holdout.spread_significance is None and spread_sig.value is not None:
                    holdout = holdout.__class__(
                        ic_spearman=holdout.ic_spearman,
                        spread=holdout.spread,
                        hit_rate=holdout.hit_rate,
                        drawdown=holdout.drawdown,
                        sample_count=holdout.sample_count,
                        ranked_days=holdout.ranked_days,
                        spread_significance=spread_sig,
                    )

                comparison = {
                    "baseline_spread": baseline_holdout_metrics.spread,
                    "policy_spread": holdout.spread,
                    "spread_improvement": (
                        (holdout.spread - baseline_holdout_metrics.spread)
                        if holdout.spread is not None and baseline_holdout_metrics.spread is not None
                        else None
                    ),
                    "spread_significance": spread_sig.to_dict(),
                }
                findings = build_research_findings(
                    policy_type=config.policy_type,
                    baseline_spread=baseline_holdout_metrics.spread,
                    policy_spread=holdout.spread,
                    sample_count=findings_metrics.sample_count,
                    ranked_days=findings_metrics.ranked_days,
                    spread_significance=spread_sig,
                )
                completed = self.backtest_repo.complete(
                    bt_run,
                    train_metrics=replay.train_metrics.to_dict(),
                    holdout_metrics=holdout.to_dict(),
                    comparison_vs_baseline=comparison,
                    research_findings=findings,
                    days_included=replay.days_included,
                    days_excluded=replay.days_excluded,
                )
                log_event(
                    logger,
                    "regime_backtest_run_completed",
                    experiment_id=experiment.id,
                    backtest_run_id=completed.id,
                    policy_type=config.policy_type,
                )
                backtest_runs.append(completed)
                summary[config.policy_type] = {
                    "backtest_run_id": str(completed.id),
                    "holdout_metrics": holdout.to_dict(),
                    "research_findings": findings,
                }
            except Exception as exc:
                self.backtest_repo.fail(bt_run, str(exc))
                raise

        self.experiment_service.complete(experiment.id)
        log_event(
            logger,
            "regime_backtest_completed",
            experiment_id=experiment.id,
            backtest_count=len(backtest_runs),
            duration_ms=int((time.perf_counter() - t_start) * 1000),
        )
        self.db.commit()

        best = _pick_best_policy(summary)
        return {
            "experiment_run_id": str(experiment.id),
            "backtest_run_ids": [str(r.id) for r in backtest_runs],
            "summary": summary,
            "best_policy_on_holdout": best,
        }

    def list_backtest_runs(
        self,
        *,
        experiment_run_id: UUID | None = None,
        policy_config_id: UUID | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        rows = self.backtest_repo.list_runs(
            experiment_run_id=experiment_run_id,
            policy_config_id=policy_config_id,
            status=status,
            limit=limit,
        )
        return [_backtest_run_to_dict(row) for row in rows]

    def _resolve_config(
        self,
        policy_config_id: UUID | None,
        strategy_name: str,
        strategy_version: str,
    ) -> RegimePolicyConfig:
        if policy_config_id:
            config = self.config_repo.get_by_id(policy_config_id)
            if config is None:
                raise ValueError(f"Policy config not found: {policy_config_id}")
            return config
        active = self.config_repo.list_configs(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            status="active",
        )
        if not active:
            raise ValueError("No active policy config found")
        return active[0]

    @staticmethod
    def _config_to_spec(config: RegimePolicyConfig) -> PolicyConfigSpec:
        return PolicyConfigSpec(
            policy_name=config.policy_name,
            policy_type=config.policy_type,
            strategy_name=config.strategy_name,
            strategy_version=config.strategy_version,
            allowed_regimes=list(config.allowed_regimes or []),
            size_multipliers=dict(config.size_multipliers or {}),
            min_decile=config.min_decile,
            max_decile=config.max_decile,
            default_action=config.default_action,
            notes=config.notes,
        )


def _decision_to_dict(row) -> dict:
    return {
        "id": str(row.id),
        "policy_config_id": str(row.policy_config_id),
        "ranking_run_id": str(row.ranking_run_id) if row.ranking_run_id else None,
        "validation_report_id": str(row.validation_report_id) if row.validation_report_id else None,
        "as_of_date": row.as_of_date.isoformat(),
        "regime_label": row.regime_label,
        "action": row.action,
        "size_multiplier": float(row.size_multiplier),
        "decile_filter": row.decile_filter,
        "reason": row.reason,
        "experiment_run_id": str(row.experiment_run_id) if row.experiment_run_id else None,
        "created_at": row.created_at.isoformat(),
    }


def _backtest_run_to_dict(row: RegimeBacktestRun) -> dict:
    return {
        "id": str(row.id),
        "experiment_run_id": str(row.experiment_run_id),
        "policy_config_id": str(row.policy_config_id),
        "baseline_policy_config_id": (
            str(row.baseline_policy_config_id) if row.baseline_policy_config_id else None
        ),
        "strategy_name": row.strategy_name,
        "strategy_version": row.strategy_version,
        "universe_code": row.universe_code,
        "horizon": row.horizon,
        "window_spec": row.window_spec,
        "start_date": row.start_date.isoformat(),
        "end_date": row.end_date.isoformat(),
        "holdout_start_date": (
            row.holdout_start_date.isoformat() if row.holdout_start_date else None
        ),
        "train_metrics": row.train_metrics,
        "holdout_metrics": row.holdout_metrics,
        "comparison_vs_baseline": row.comparison_vs_baseline,
        "research_findings": row.research_findings,
        "days_included": row.days_included,
        "days_excluded": row.days_excluded,
        "status": row.status,
        "error_message": row.error_message,
        "started_at": row.started_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _pick_best_policy(summary: dict[str, dict]) -> str | None:
    best_type: str | None = None
    best_spread: float | None = None
    for policy_type, payload in summary.items():
        findings = payload.get("research_findings") or {}
        spread = findings.get("policy_spread")
        if spread is None:
            continue
        if best_spread is None or spread > best_spread:
            best_spread = spread
            best_type = policy_type
    return best_type
