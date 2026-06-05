from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.outcome_attribution.constants import (
    ATTRIBUTION_BUCKETS,
    ATTRIBUTION_HORIZONS,
    BUCKET_BENCHMARK,
    RANK_BANDS_TOP_20,
    REGIME_LABEL_ALL,
)
from app.outcome_attribution.models import (
    BucketMetrics,
    OutcomeAttributionConfig,
    OutcomeAttributionReport,
    RunBenchmark,
    SegmentMetrics,
    StockObservation,
)
from app.outcome_attribution.statistics import (
    compute_bucket_metrics,
    mean_or_none,
    rank_in_band,
    rank_in_bucket,
)


class OutcomeAttributionService:
    def compute(
        self,
        config: OutcomeAttributionConfig,
        observations: list[StockObservation],
        benchmarks: list[RunBenchmark],
    ) -> OutcomeAttributionReport:
        benchmark_by_run = {bench.run_id: bench for bench in benchmarks}
        run_dates = {obs.run_id: obs.as_of_date for obs in observations}
        ranked_run_count = len({obs.run_id for obs in observations})

        segments: list[SegmentMetrics] = []
        for strategy in config.strategy_names:
            strategy_obs = [obs for obs in observations if obs.strategy_name == strategy]
            if not strategy_obs:
                continue
            regimes = sorted(
                {obs.regime_label for obs in strategy_obs if obs.regime_label},
            )
            regime_labels = [REGIME_LABEL_ALL, *regimes]
            for regime in regime_labels:
                subset = _filter_regime(strategy_obs, regime)
                if not subset:
                    continue
                segments.append(
                    _build_segment(strategy, regime, subset, benchmark_by_run, run_dates)
                )

        runs_with_data = _count_runs_with_horizon(observations, benchmark_by_run, horizon=20)
        verdict, verdict_summary = _build_verdict(segments)

        return OutcomeAttributionReport(
            config=config,
            ranked_run_count=ranked_run_count,
            runs_with_forward_data=runs_with_data,
            segments=tuple(segments),
            verdict=verdict,
            verdict_summary=verdict_summary,
        )


def _filter_regime(observations: list[StockObservation], regime: str) -> list[StockObservation]:
    if regime == REGIME_LABEL_ALL:
        return observations
    return [obs for obs in observations if obs.regime_label == regime]


def _build_segment(
    strategy: str,
    regime: str,
    observations: list[StockObservation],
    benchmark_by_run: dict,
    run_dates: dict,
) -> SegmentMetrics:
    horizons: dict[int, dict[str, BucketMetrics]] = {}
    rank_bands: dict[int, dict[str, BucketMetrics]] = {}

    for horizon in ATTRIBUTION_HORIZONS:
        horizons[horizon] = {}
        for bucket in ATTRIBUTION_BUCKETS:
            horizons[horizon][bucket] = _metrics_for_bucket(
                bucket=bucket,
                horizon=horizon,
                observations=observations,
                benchmark_by_run=benchmark_by_run,
                run_dates=run_dates,
            )

        rank_bands[horizon] = {}
        for band in RANK_BANDS_TOP_20:
            rank_bands[horizon][band] = _metrics_for_rank_band(
                band=band,
                horizon=horizon,
                observations=observations,
                benchmark_by_run=benchmark_by_run,
                run_dates=run_dates,
            )

    return SegmentMetrics(
        strategy_name=strategy,
        regime_label=regime,
        horizons=horizons,
        rank_bands=rank_bands,
    )


def _metrics_for_bucket(
    *,
    bucket: str,
    horizon: int,
    observations: list[StockObservation],
    benchmark_by_run: dict,
    run_dates: dict,
) -> BucketMetrics:
    stock_returns: list[float] = []
    benchmark_returns: list[float] = []
    per_run_pairs: list[tuple[date, float]] = []

    if bucket == BUCKET_BENCHMARK:
        seen_runs: set = set()
        for obs in sorted(observations, key=lambda item: (item.as_of_date, str(item.run_id))):
            if obs.run_id in seen_runs:
                continue
            bench = benchmark_by_run.get(obs.run_id)
            if bench is None:
                continue
            bench_value = bench.returns.get(horizon)
            if bench_value is not None:
                per_run_pairs.append((obs.as_of_date, bench_value))
                seen_runs.add(obs.run_id)
        benchmark_returns = [value for _, value in per_run_pairs]
    else:
        grouped: dict = defaultdict(list)
        for obs in observations:
            if not rank_in_bucket(obs.rank, bucket):
                continue
            value = obs.returns.get(horizon)
            if value is not None:
                grouped[obs.run_id].append(value)

        for run_id, values in grouped.items():
            avg = mean_or_none(values)
            if avg is not None:
                per_run_pairs.append((run_dates.get(run_id, date.min), avg))
                stock_returns.extend(values)
            bench = benchmark_by_run.get(run_id)
            if bench is not None:
                bench_value = bench.returns.get(horizon)
                if bench_value is not None:
                    benchmark_returns.append(bench_value)

    per_run_pairs.sort(key=lambda item: item[0])
    per_run_returns = [value for _, value in per_run_pairs]
    if bucket == BUCKET_BENCHMARK:
        stock_returns = per_run_returns

    return compute_bucket_metrics(
        bucket=bucket,
        horizon=horizon,
        per_run_returns=per_run_returns,
        stock_returns=stock_returns,
        benchmark_returns=benchmark_returns,
    )


def _metrics_for_rank_band(
    *,
    band: str,
    horizon: int,
    observations: list[StockObservation],
    benchmark_by_run: dict,
    run_dates: dict,
) -> BucketMetrics:
    grouped: dict = defaultdict(list)
    for obs in observations:
        if not rank_in_band(obs.rank, band):
            continue
        value = obs.returns.get(horizon)
        if value is not None:
            grouped[obs.run_id].append(value)

    per_run_pairs: list[tuple[date, float]] = []
    stock_returns: list[float] = []
    benchmark_returns: list[float] = []

    for run_id, values in grouped.items():
        avg = mean_or_none(values)
        if avg is not None:
            per_run_pairs.append((run_dates.get(run_id, date.min), avg))
            stock_returns.extend(values)
        bench = benchmark_by_run.get(run_id)
        if bench is not None:
            bench_value = bench.returns.get(horizon)
            if bench_value is not None:
                benchmark_returns.append(bench_value)

    per_run_pairs.sort(key=lambda item: item[0])
    per_run_returns = [value for _, value in per_run_pairs]

    return compute_bucket_metrics(
        bucket=band,
        horizon=horizon,
        per_run_returns=per_run_returns,
        stock_returns=stock_returns,
        benchmark_returns=benchmark_returns,
    )


def _count_runs_with_horizon(
    observations: list[StockObservation],
    benchmark_by_run: dict,
    *,
    horizon: int,
) -> int:
    runs: set = set()
    for obs in observations:
        if obs.returns.get(horizon) is not None:
            runs.add(obs.run_id)
    for run_id, bench in benchmark_by_run.items():
        if bench.returns.get(horizon) is not None:
            runs.add(run_id)
    return len(runs)


def _build_verdict(segments: list[SegmentMetrics]) -> tuple[str, str]:
    """Summarize whether higher rank reliably beats benchmark at 20d horizon."""
    evidence: list[tuple[str, str, float | None, float | None, float | None]] = []

    for segment in segments:
        if segment.regime_label != REGIME_LABEL_ALL:
            continue
        metrics_20 = segment.horizons.get(20, {})
        top5 = metrics_20.get("top_5")
        top10 = metrics_20.get("top_10")
        top20 = metrics_20.get("top_20")
        if not top5 or not top10 or not top20:
            continue
        evidence.append(
            (
                segment.strategy_name,
                segment.regime_label,
                top5.alpha,
                top10.alpha,
                top20.alpha,
            )
        )

    if not evidence:
        return (
            "insufficient_data",
            "Not enough completed ranking runs with 20-day forward returns to assess rank-outcome linkage.",
        )

    positive_alpha = sum(
        1 for _, _, a5, a10, a20 in evidence if (a5 or 0) > 0 and (a10 or 0) > 0 and (a20 or 0) > 0
    )
    monotonic = sum(
        1
        for _, _, a5, a10, a20 in evidence
        if a5 is not None and a10 is not None and a20 is not None and a5 >= a10 >= a20
    )

    if positive_alpha == len(evidence) and monotonic >= len(evidence) // 2:
        return (
            "yes_with_caveats",
            "Higher-ranked buckets show positive alpha vs benchmark at 20d for all strategies in aggregate, "
            "with generally decreasing alpha as bucket width widens (rank selectivity signal).",
        )
    if positive_alpha >= len(evidence) // 2:
        return (
            "partial",
            "Top-ranked buckets beat benchmark on average in some strategies/segments, but the rank gradient "
            "is not consistently monotonic — ranking generates selective alpha but not uniformly across buckets.",
        )
    return (
        "no",
        "Top-ranked buckets do not reliably outperform benchmark on average at 20d in the evaluated window.",
    )
