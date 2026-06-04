from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.outcome_attribution.models import RunBenchmark
from app.outcome_attribution.statistics import compute_bucket_metrics, mean_or_none
from app.ranking_research.calibration import (
    CalibrationTables,
    build_calibration_tables,
    compute_calibrated_score,
)
from app.ranking_research.constants import RESEARCH_HORIZONS
from app.ranking_research.models import (
    CalibratedRankingBacktestReport,
    EnrichedStockObservation,
    PortfolioBacktestMetrics,
    RankingResearchConfig,
)
from app.ranking_research.rank_reliability import _spearman_correlation


def _portfolio_metrics_for_runs(
    *,
    label: str,
    horizon: int,
    run_selections: dict,
    benchmark_by_run: dict,
    run_dates: dict,
) -> PortfolioBacktestMetrics:
    per_run_pairs: list[tuple[date, float]] = []
    stock_returns: list[float] = []
    benchmark_returns: list[float] = []
    rank_ret_pairs: list[tuple[int, float]] = []

    for run_id, stocks in run_selections.items():
        values = [s["return"] for s in stocks if s["return"] is not None]
        if not values:
            continue
        avg = mean_or_none(values)
        if avg is not None:
            per_run_pairs.append((run_dates.get(run_id, date.min), avg))
            stock_returns.extend(values)
        bench = benchmark_by_run.get(run_id)
        if bench is not None:
            bench_value = bench.returns.get(horizon)
            if bench_value is not None:
                benchmark_returns.append(bench_value)
        for s in stocks:
            if s["return"] is not None:
                rank_ret_pairs.append((s["rank"], s["return"]))

    per_run_pairs.sort(key=lambda item: item[0])
    per_run_returns = [v for _, v in per_run_pairs]
    bucket = compute_bucket_metrics(
        bucket=label,
        horizon=horizon,
        per_run_returns=per_run_returns,
        stock_returns=stock_returns,
        benchmark_returns=benchmark_returns,
    )
    corr = None
    if len(rank_ret_pairs) >= 3:
        corr = _spearman_correlation(
            [p[0] for p in rank_ret_pairs],
            [p[1] for p in rank_ret_pairs],
        )

    return PortfolioBacktestMetrics(
        label=label,
        horizon=horizon,
        hit_rate=bucket.hit_rate,
        average_return=bucket.average_return,
        alpha=bucket.alpha,
        sharpe=bucket.sharpe,
        max_drawdown=bucket.max_drawdown,
        rank_return_correlation=corr,
        run_count=bucket.run_count,
        observation_count=bucket.observation_count,
    )


def _build_horizon_portfolio(
    *,
    label: str,
    horizon: int,
    by_run: dict,
    selector,
    benchmark_by_run: dict,
    run_dates: dict,
) -> PortfolioBacktestMetrics:
    run_selections: dict = {}
    for run_id, obs_list in by_run.items():
        selected = [o for o in obs_list if selector(o)]
        run_selections[run_id] = [
            {"rank": o.rank, "return": o.returns.get(horizon)} for o in selected
        ]
    return _portfolio_metrics_for_runs(
        label=label,
        horizon=horizon,
        run_selections=run_selections,
        benchmark_by_run=benchmark_by_run,
        run_dates=run_dates,
    )


def _build_horizon_portfolio_calibrated(
    *,
    label: str,
    horizon: int,
    by_run: dict,
    tables: CalibrationTables,
    benchmark_by_run: dict,
    run_dates: dict,
) -> PortfolioBacktestMetrics:
    run_selections: dict = {}
    for run_id, obs_list in by_run.items():
        if not obs_list:
            continue
        strategy = obs_list[0].strategy_name
        regime = obs_list[0].regime_label
        scored = []
        for obs in obs_list:
            cal = compute_calibrated_score(
                raw_score=obs.score,
                rank=obs.rank,
                strategy_name=strategy,
                regime_label=regime,
                score_components=obs.score_components,
                tables=tables,
            )
            scored.append((cal, obs))
        scored.sort(key=lambda item: (-item[0], item[1].rank))
        top = scored[:20]
        run_selections[run_id] = [
            {"rank": idx + 1, "return": o.returns.get(horizon)}
            for idx, (_, o) in enumerate(top)
        ]
    return _portfolio_metrics_for_runs(
        label=label,
        horizon=horizon,
        run_selections=run_selections,
        benchmark_by_run=benchmark_by_run,
        run_dates=run_dates,
    )


def _finalize_backtest(
    *,
    config: RankingResearchConfig,
    observations: list[EnrichedStockObservation],
    production: list[PortfolioBacktestMetrics],
    calibrated: list[PortfolioBacktestMetrics],
) -> CalibratedRankingBacktestReport:
    prod_20 = next(m for m in production if m.horizon == 20)
    cal_20 = next(m for m in calibrated if m.horizon == 20)
    prod_5 = next((m for m in production if m.horizon == 5), None)
    cal_5 = next((m for m in calibrated if m.horizon == 5), None)
    prod_10 = next((m for m in production if m.horizon == 10), None)
    cal_10 = next((m for m in calibrated if m.horizon == 10), None)

    meets_mono = (
        cal_20.rank_return_correlation is not None
        and prod_20.rank_return_correlation is not None
        and cal_20.rank_return_correlation < prod_20.rank_return_correlation
    )
    meets_top5 = (
        prod_5 is not None
        and cal_5 is not None
        and prod_5.alpha is not None
        and cal_5.alpha is not None
        and cal_5.alpha > prod_5.alpha
    )
    meets_top10 = (
        prod_10 is not None
        and cal_10 is not None
        and prod_10.alpha is not None
        and cal_10.alpha is not None
        and cal_10.alpha > prod_10.alpha
    )
    meets_sharpe = (
        cal_20.sharpe is not None
        and prod_20.sharpe is not None
        and cal_20.sharpe > prod_20.sharpe
    )
    alpha_20_bps = 0.0
    if prod_20.alpha is not None and cal_20.alpha is not None:
        alpha_20_bps = (cal_20.alpha - prod_20.alpha) * 10_000
    meets_material_alpha = alpha_20_bps >= 5.0

    success_count = sum([meets_mono, meets_top5, meets_top10, meets_sharpe])
    all_criteria = meets_mono and meets_top5 and meets_top10 and meets_sharpe
    if all_criteria and meets_material_alpha:
        verdict = "promising"
        summary = (
            "Calibrated re-ranking meets all success criteria with material 20d alpha lift in-sample; "
            "still requires out-of-sample walk-forward before ranking v2."
        )
    elif success_count >= 3:
        verdict = "mixed"
        summary = (
            "Calibration passes some checks (e.g. Sharpe/monotonicity) but top-5 alpha or 20d alpha "
            "lift is weak — not ready for production promotion."
        )
    elif success_count >= 2:
        verdict = "mixed"
        summary = (
            "Calibration shows partial improvement; rank monotonicity or alpha gains "
            "are not consistent enough for production promotion."
        )
    else:
        verdict = "insufficient"
        summary = (
            "Calibrated ranking does not meet success criteria in this window; "
            "keep production rank order and revisit factor/regime tables."
        )

    ranked_run_count = len({o.run_id for o in observations})
    return CalibratedRankingBacktestReport(
        config=config,
        ranked_run_count=ranked_run_count,
        production=tuple(production),
        calibrated=tuple(calibrated),
        meets_monotonicity=meets_mono,
        meets_top5_alpha=meets_top5,
        meets_top10_alpha=meets_top10,
        meets_sharpe=meets_sharpe,
        verdict=verdict,
        verdict_summary=summary,
    )


def run_calibrated_backtest(
    config: RankingResearchConfig,
    observations: list[EnrichedStockObservation],
    benchmarks: list[RunBenchmark],
    *,
    tables: CalibrationTables | None = None,
) -> CalibratedRankingBacktestReport:
    tables = tables or build_calibration_tables(observations, benchmarks)
    benchmark_by_run = {b.run_id: b for b in benchmarks}
    run_dates = {o.run_id: o.as_of_date for o in observations}

    by_run: dict = defaultdict(list)
    for obs in observations:
        by_run[obs.run_id].append(obs)

    production_metrics: list[PortfolioBacktestMetrics] = []
    calibrated_metrics: list[PortfolioBacktestMetrics] = []

    for horizon in RESEARCH_HORIZONS:
        production_metrics.append(
            _build_horizon_portfolio(
                label="production_top20",
                horizon=horizon,
                by_run=by_run,
                selector=lambda obs, h=horizon: obs.rank <= 20,
                benchmark_by_run=benchmark_by_run,
                run_dates=run_dates,
            )
        )
        calibrated_metrics.append(
            _build_horizon_portfolio_calibrated(
                label="calibrated_top20",
                horizon=horizon,
                by_run=by_run,
                tables=tables,
                benchmark_by_run=benchmark_by_run,
                run_dates=run_dates,
            )
        )

    return _finalize_backtest(
        config=config,
        observations=observations,
        production=production_metrics,
        calibrated=calibrated_metrics,
    )
