from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.outcome_attribution.constants import REGIME_LABEL_ALL
from app.outcome_attribution.models import BucketMetrics
from app.outcome_attribution.statistics import compute_bucket_metrics, mean_or_none
from app.ranking_research.constants import RESEARCH_HORIZONS, SCORE_BUCKET_SPECS
from app.ranking_research.models import (
    EnrichedStockObservation,
    ScoreCompressionBucket,
    ScoreCompressionReport,
    ScoreCompressionSegment,
)


def _score_bucket_label(score: float) -> str | None:
    for label, low, high in SCORE_BUCKET_SPECS:
        if low <= score < high:
            return label
    return None


def _metrics_for_score_bucket(
    *,
    bucket_label: str,
    horizon: int,
    observations: list[EnrichedStockObservation],
    benchmark_by_run: dict,
    run_dates: dict,
) -> BucketMetrics:
    grouped: dict = defaultdict(list)
    for obs in observations:
        label = _score_bucket_label(obs.score)
        if label != bucket_label:
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
        bucket=bucket_label,
        horizon=horizon,
        per_run_returns=per_run_returns,
        stock_returns=stock_returns,
        benchmark_returns=benchmark_returns,
    )


def build_score_compression_segment(
    *,
    strategy_name: str,
    regime_label: str,
    observations: list[EnrichedStockObservation],
    benchmark_by_run: dict,
) -> ScoreCompressionSegment | None:
    if regime_label == REGIME_LABEL_ALL:
        subset = [
            o for o in observations if o.strategy_name == strategy_name and o.rank <= 20
        ]
    else:
        subset = [
            o
            for o in observations
            if o.strategy_name == strategy_name
            and o.regime_label == regime_label
            and o.rank <= 20
        ]
    if not subset:
        return None

    run_dates = {obs.run_id: obs.as_of_date for obs in subset}
    buckets: dict[str, dict[int, BucketMetrics]] = {}
    for label, _, _ in SCORE_BUCKET_SPECS:
        buckets[label] = {}
        for horizon in RESEARCH_HORIZONS:
            buckets[label][horizon] = _metrics_for_score_bucket(
                bucket_label=label,
                horizon=horizon,
                observations=subset,
                benchmark_by_run=benchmark_by_run,
                run_dates=run_dates,
            )

    return ScoreCompressionSegment(
        strategy_name=strategy_name,
        regime_label=regime_label,
        per_bucket=buckets,
    )


def build_score_compression_report(
    *,
    observations: list[EnrichedStockObservation],
    benchmark_by_run: dict,
    strategy_names: tuple[str, ...],
    regime_labels: tuple[str, ...],
) -> ScoreCompressionReport:
    segments: list[ScoreCompressionSegment] = []
    for strategy in strategy_names:
        for regime in regime_labels:
            seg = build_score_compression_segment(
                strategy_name=strategy,
                regime_label=regime,
                observations=observations,
                benchmark_by_run=benchmark_by_run,
            )
            if seg:
                segments.append(seg)
    return ScoreCompressionReport(segments=tuple(segments))


def compare_score_buckets(
    segment: ScoreCompressionSegment,
    horizon: int,
    high_label: str,
    low_label: str,
) -> ScoreCompressionBucket | None:
    high = segment.per_bucket.get(high_label, {}).get(horizon)
    low = segment.per_bucket.get(low_label, {}).get(horizon)
    if not high or not low:
        return None
    if high.status != "ok" or low.status != "ok":
        return None
    high_alpha = high.alpha or 0.0
    low_alpha = low.alpha or 0.0
    return ScoreCompressionBucket(
        horizon=horizon,
        high_bucket=high_label,
        low_bucket=low_label,
        high_alpha=high_alpha,
        low_alpha=low_alpha,
        alpha_spread=high_alpha - low_alpha,
        high_outperforms=high_alpha > low_alpha,
    )
