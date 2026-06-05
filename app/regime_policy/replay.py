from __future__ import annotations

import logging
import time
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.constants import PolicyAction, PolicyType, ReplayWindowMode
from app.core.structured_logging import log_event
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.models.ranking_validation_report import RankingValidationReport
from app.regime_policy.engine import PolicyConfigSpec, RegimePolicyEngine
from app.regime_policy.metrics import (
    bootstrap_metric_ci,
    compute_daily_portfolio_return,
    compute_max_drawdown,
    compute_pooled_period_metrics,
    metrics_from_scored_returns,
)
from app.regime_policy.models import (
    DailyPortfolioReturn,
    MetricWithSignificance,
    PeriodMetrics,
    PolicyDecision,
    PolicyEvaluationContext,
    ReplayDayResult,
    ReplayResult,
    ReplayWindowSpec,
)
from app.regime_policy.scored_returns_loader import (
    batch_load_scored_returns_by_run,
    count_scored_returns_by_run,
)
from app.validation.statistics import _ScoredReturn, assign_deciles

logger = logging.getLogger(__name__)

_POLICIES_USING_PRECOMPUTED_SPREAD = frozenset(
    {PolicyType.BASELINE_E1.value, PolicyType.HARD_GATE_E2.value}
)


class RegimePolicyReplayService:
    """Overlay regime policies on stored ranking/validation results without reranking."""

    def __init__(
        self,
        db: Session,
        validation_repo: RankingValidationRepository,
        engine: RegimePolicyEngine | None = None,
    ) -> None:
        self.db = db
        self.validation_repo = validation_repo
        self.engine = engine or RegimePolicyEngine()

    def replay(
        self,
        *,
        policy_config_id: UUID,
        config: PolicyConfigSpec,
        window_spec: ReplayWindowSpec,
        horizon: int,
        strategy_name: str,
        strategy_version: str,
        universe_code: str | None = None,
        reports: list[RankingValidationReport] | None = None,
        scored_by_run: dict[UUID, list[_ScoredReturn]] | None = None,
        horizon_spreads_by_report: dict[UUID, float] | None = None,
        horizon_sample_sizes_by_report: dict[UUID, int] | None = None,
    ) -> ReplayResult:
        t0 = time.perf_counter()
        if reports is None:
            reports = self.validation_repo.list_completed_with_runs(
                universe_code=universe_code,
                strategy_name=strategy_name,
                strategy_version=strategy_version,
                start_date=window_spec.start_date,
                end_date=window_spec.end_date,
            )
        log_event(
            logger,
            "regime_replay_reports_loaded",
            policy_config_id=policy_config_id,
            report_count=len(reports),
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )

        if scored_by_run is None:
            t1 = time.perf_counter()
            run_ids = [report.ranking_run_id for report in reports if report.ranking_run_id]
            scored_by_run = batch_load_scored_returns_by_run(self.db, run_ids, horizon)
            runs_with_data, total_rows = count_scored_returns_by_run(scored_by_run)
            log_event(
                logger,
                "regime_replay_scored_returns_loaded",
                policy_config_id=policy_config_id,
                run_count=len(scored_by_run),
                runs_with_data=runs_with_data,
                total_rows=total_rows,
                duration_ms=int((time.perf_counter() - t1) * 1000),
            )

        train_scored: list[_ScoredReturn] = []
        holdout_scored: list[_ScoredReturn] = []
        train_days: set[date] = set()
        holdout_days: set[date] = set()
        train_daily_returns: list[float] = []
        holdout_daily_returns: list[float] = []
        day_results: list[ReplayDayResult] = []
        daily_returns: list[DailyPortfolioReturn] = []
        validation_report_ids: list[UUID] = []
        included_run_ids: set[UUID] = set()
        days_included = 0
        days_excluded = 0
        train_fallback_samples = 0
        holdout_fallback_samples = 0

        t2 = time.perf_counter()
        for report in reports:
            run = report.ranking_run
            if run is None:
                continue
            as_of = run.as_of_date
            regime = report.regime_label
            run_id = report.ranking_run_id
            run_context = PolicyEvaluationContext(regime_label=regime)
            run_decision = self.engine.evaluate_run(config, run_context)
            validation_report_ids.append(report.id)

            log_event(
                logger,
                "regime_replay_day_evaluated",
                policy_config_id=policy_config_id,
                report_id=str(report.id),
                ranking_run_id=str(run_id),
                regime_label=regime,
                policy_action=run_decision.action,
                scored_returns_loaded=len(scored_by_run.get(run_id, [])),
            )

            if run_decision.action == PolicyAction.BLOCK.value:
                days_excluded += 1
                day_results.append(
                    ReplayDayResult(
                        as_of_date=as_of,
                        ranking_run_id=run_id,
                        validation_report_id=report.id,
                        regime_label=regime,
                        decision=run_decision,
                        included=False,
                    )
                )
                continue

            day_scored = self._filter_scored_returns(
                scored_by_run.get(run_id, []),
                config,
                regime,
            )
            if not day_scored:
                included_from_precomputed, train_samples, holdout_samples = (
                    self._try_include_precomputed_day(
                        report=report,
                        run_id=run_id,
                        as_of=as_of,
                        regime=regime,
                        config=config,
                        run_decision=run_decision,
                        window_spec=window_spec,
                        horizon_spreads_by_report=horizon_spreads_by_report,
                        horizon_sample_sizes_by_report=horizon_sample_sizes_by_report,
                        train_days=train_days,
                        holdout_days=holdout_days,
                        train_daily_returns=train_daily_returns,
                        holdout_daily_returns=holdout_daily_returns,
                        daily_returns=daily_returns,
                        day_results=day_results,
                    )
                )
                if included_from_precomputed:
                    train_fallback_samples += train_samples
                    holdout_fallback_samples += holdout_samples
                    included_run_ids.add(run_id)
                    days_included += 1
                    log_event(
                        logger,
                        "regime_replay_day_included_precomputed",
                        policy_config_id=policy_config_id,
                        report_id=str(report.id),
                        ranking_run_id=str(run_id),
                        regime_label=regime,
                        policy_action=run_decision.action,
                    )
                    continue

                days_excluded += 1
                log_event(
                    logger,
                    "regime_replay_day_excluded_no_scored_returns",
                    policy_config_id=policy_config_id,
                    report_id=str(report.id),
                    ranking_run_id=str(run_id),
                    regime_label=regime,
                    policy_action=run_decision.action,
                )
                day_results.append(
                    ReplayDayResult(
                        as_of_date=as_of,
                        ranking_run_id=run_id,
                        validation_report_id=report.id,
                        regime_label=regime,
                        decision=run_decision,
                        included=False,
                    )
                )
                continue

            if config.policy_type == PolicyType.SOFT_GATE_E3.value:
                multiplier = run_decision.size_multiplier
                day_scored = [
                    _ScoredReturn(
                        symbol=item.symbol,
                        score=item.score,
                        rank=item.rank,
                        forward_return=item.forward_return * multiplier,
                    )
                    for item in day_scored
                ]

            daily_return = compute_daily_portfolio_return(day_scored, Decimal("1.0"))
            split = window_spec.split_dates(as_of)
            if split == "holdout":
                holdout_scored.extend(day_scored)
                holdout_days.add(as_of)
                if daily_return is not None:
                    holdout_daily_returns.append(float(daily_return))
            else:
                train_scored.extend(day_scored)
                train_days.add(as_of)
                if daily_return is not None:
                    train_daily_returns.append(float(daily_return))

            if daily_return is not None:
                daily_returns.append(
                    DailyPortfolioReturn(
                        as_of_date=as_of,
                        portfolio_return=daily_return,
                        size_multiplier=run_decision.size_multiplier,
                        stock_count=len(day_scored),
                    )
                )

            included_run_ids.add(run_id)
            days_included += 1
            day_results.append(
                ReplayDayResult(
                    as_of_date=as_of,
                    ranking_run_id=run_id,
                    validation_report_id=report.id,
                    regime_label=regime,
                    decision=run_decision,
                    included=True,
                    scored_returns_count=len(day_scored),
                )
            )

        log_event(
            logger,
            "regime_replay_day_loop_completed",
            policy_config_id=policy_config_id,
            days_included=days_included,
            days_excluded=days_excluded,
            included_run_ids_count=len(included_run_ids),
            train_pool_size=len(train_scored),
            holdout_pool_size=len(holdout_scored),
            train_fallback_samples=train_fallback_samples,
            holdout_fallback_samples=holdout_fallback_samples,
            duration_ms=int((time.perf_counter() - t2) * 1000),
        )

        log_event(
            logger,
            "regime_replay_pooled_samples_before_metrics",
            policy_config_id=policy_config_id,
            train_scored_count=len(train_scored),
            holdout_scored_count=len(holdout_scored),
            train_ranked_days=len(train_days),
            holdout_ranked_days=len(holdout_days),
        )

        t3 = time.perf_counter()
        train_metrics = self._build_period_metrics(
            train_scored,
            ranked_days=len(train_days),
            horizon=horizon,
            daily_returns=train_daily_returns,
            fallback_sample_count=train_fallback_samples,
        )
        holdout_metrics = self._build_period_metrics(
            holdout_scored,
            ranked_days=len(holdout_days),
            horizon=horizon,
            daily_returns=holdout_daily_returns,
            fallback_sample_count=holdout_fallback_samples,
        )
        log_event(
            logger,
            "regime_replay_metrics_computed",
            policy_config_id=policy_config_id,
            duration_ms=int((time.perf_counter() - t3) * 1000),
        )

        return ReplayResult(
            policy_config_id=policy_config_id,
            window_spec=window_spec,
            horizon=horizon,
            train_metrics=train_metrics,
            holdout_metrics=holdout_metrics,
            days_included=days_included,
            days_excluded=days_excluded,
            day_results=day_results,
            daily_returns=daily_returns,
            validation_report_ids=validation_report_ids,
        )

    def compute_daily_spreads_by_date(
        self,
        reports: list[RankingValidationReport],
        config: PolicyConfigSpec,
        horizon: int,
        *,
        scored_by_run: dict[UUID, list[_ScoredReturn]] | None = None,
        horizon_spreads_by_report: dict[UUID, float] | None = None,
    ) -> dict[date, float]:
        spreads: dict[date, float] = {}
        use_precomputed = (
            config.policy_type in _POLICIES_USING_PRECOMPUTED_SPREAD
            and horizon_spreads_by_report is not None
        )

        if not use_precomputed and scored_by_run is None:
            run_ids = [
                report.ranking_run.id for report in reports if report.ranking_run is not None
            ]
            scored_by_run = batch_load_scored_returns_by_run(self.db, run_ids, horizon)
        elif scored_by_run is None:
            scored_by_run = {}

        for report in reports:
            run = report.ranking_run
            if run is None:
                continue
            regime = report.regime_label
            run_decision = self.engine.evaluate_run(
                config,
                PolicyEvaluationContext(regime_label=regime),
            )
            if run_decision.action == PolicyAction.BLOCK.value:
                continue

            if use_precomputed:
                spread = horizon_spreads_by_report.get(report.id)
                if spread is not None:
                    spreads[run.as_of_date] = spread
                continue

            day_scored = self._filter_scored_returns(
                scored_by_run.get(run.id, []),
                config,
                regime,
            )
            if not day_scored:
                continue
            if config.policy_type == PolicyType.SOFT_GATE_E3.value:
                multiplier = run_decision.size_multiplier
                day_scored = [
                    _ScoredReturn(
                        symbol=item.symbol,
                        score=item.score,
                        rank=item.rank,
                        forward_return=item.forward_return * multiplier,
                    )
                    for item in day_scored
                ]
            metrics = metrics_from_scored_returns(
                day_scored,
                horizon=horizon,
                ranked_days=1,
            )
            if metrics["spread"] is not None:
                spreads[run.as_of_date] = metrics["spread"]
        return spreads

    def _filter_scored_returns(
        self,
        scored: list[_ScoredReturn],
        config: PolicyConfigSpec,
        regime: str | None,
    ) -> list[_ScoredReturn]:
        if config.policy_type != PolicyType.THRESHOLD_GATE_E4.value:
            return scored

        buckets = assign_deciles(scored)
        decile_map: dict[str, int] = {}
        for decile, items in buckets.items():
            for item in items:
                decile_map[item.symbol] = decile

        filtered: list[_ScoredReturn] = []
        for item in scored:
            decile = decile_map.get(item.symbol)
            stock_decision = self.engine.evaluate_stock(
                config,
                PolicyEvaluationContext(regime_label=regime, decile=decile),
            )
            if stock_decision.action != PolicyAction.BLOCK.value:
                filtered.append(item)
        return filtered

    def _try_include_precomputed_day(
        self,
        *,
        report: RankingValidationReport,
        run_id: UUID,
        as_of: date,
        regime: str | None,
        config: PolicyConfigSpec,
        run_decision: PolicyDecision,
        window_spec: ReplayWindowSpec,
        horizon_spreads_by_report: dict[UUID, float] | None,
        horizon_sample_sizes_by_report: dict[UUID, int] | None,
        train_days: set[date],
        holdout_days: set[date],
        train_daily_returns: list[float],
        holdout_daily_returns: list[float],
        daily_returns: list[DailyPortfolioReturn],
        day_results: list[ReplayDayResult],
    ) -> tuple[bool, int, int]:
        """Include E1/E2 days from validation_horizon_metrics when snapshot returns are missing."""
        if config.policy_type not in _POLICIES_USING_PRECOMPUTED_SPREAD:
            return False, 0, 0
        if horizon_spreads_by_report is None:
            return False, 0, 0

        spread = horizon_spreads_by_report.get(report.id)
        sample_size = (horizon_sample_sizes_by_report or {}).get(report.id, 0)
        if spread is None or sample_size <= 0:
            return False, 0, 0

        split = window_spec.split_dates(as_of)
        train_samples = 0
        holdout_samples = 0
        if split == "holdout":
            holdout_days.add(as_of)
            holdout_daily_returns.append(float(spread))
            holdout_samples = sample_size
        else:
            train_days.add(as_of)
            train_daily_returns.append(float(spread))
            train_samples = sample_size

        daily_returns.append(
            DailyPortfolioReturn(
                as_of_date=as_of,
                portfolio_return=Decimal(str(spread)),
                size_multiplier=run_decision.size_multiplier,
                stock_count=sample_size,
            )
        )
        day_results.append(
            ReplayDayResult(
                as_of_date=as_of,
                ranking_run_id=run_id,
                validation_report_id=report.id,
                regime_label=regime,
                decision=run_decision,
                included=True,
                scored_returns_count=0,
            )
        )
        return True, train_samples, holdout_samples

    def _build_period_metrics(
        self,
        scored_returns: list[_ScoredReturn],
        *,
        ranked_days: int,
        horizon: int,
        daily_returns: list[float],
        fallback_sample_count: int = 0,
    ) -> PeriodMetrics:
        raw = compute_pooled_period_metrics(
            scored_returns,
            horizon=horizon,
            ranked_days=ranked_days,
            daily_returns=daily_returns,
        )
        drawdown = compute_max_drawdown(daily_returns).max_drawdown
        spread_sig = None
        if daily_returns:
            spread_ci = bootstrap_metric_ci(daily_returns)
            spread_sig = MetricWithSignificance(
                value=raw["spread"],
                ci_lower=spread_ci.ci_lower,
                ci_upper=spread_ci.ci_upper,
            )
        sample_count = raw["sample_count"]
        if fallback_sample_count and sample_count == 0:
            sample_count = fallback_sample_count
        elif fallback_sample_count:
            sample_count += fallback_sample_count
        spread = raw["spread"]
        if spread is None and daily_returns:
            spread = sum(daily_returns) / len(daily_returns)
        return PeriodMetrics(
            ic_spearman=raw["ic_spearman"],
            spread=spread,
            hit_rate=raw["hit_rate"],
            drawdown=drawdown,
            sample_count=sample_count,
            ranked_days=ranked_days,
            spread_significance=spread_sig,
        )


def build_single_holdout_window(
    start_date: date,
    end_date: date,
    holdout_start_date: date,
) -> ReplayWindowSpec:
    return ReplayWindowSpec(
        mode=ReplayWindowMode.SINGLE_HOLDOUT.value,
        start_date=start_date,
        end_date=end_date,
        holdout_start_date=holdout_start_date,
    )
