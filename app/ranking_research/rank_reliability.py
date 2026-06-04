from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.outcome_attribution.constants import REGIME_LABEL_ALL
from app.outcome_attribution.models import BucketMetrics, RunBenchmark
from app.outcome_attribution.statistics import compute_bucket_metrics, mean_or_none
from app.ranking_research.constants import (
    CLIFF_ALPHA_JUMP_THRESHOLD,
    EXACT_RANKS,
    MIN_OBS_FOR_RANK_ANALYSIS,
    NOISY_ALPHA_ABS_THRESHOLD,
    RESEARCH_HORIZONS,
)
from app.ranking_research.models import (
    CliffEvent,
    DecileMonotonicitySummary,
    EnrichedStockObservation,
    MonotonicitySummary,
    ScoreQuintileMetrics,
    StrategyRankReliability,
)


def _metrics_for_exact_rank(
    *,
    rank: int,
    horizon: int,
    observations: list[EnrichedStockObservation],
    benchmark_by_run: dict,
    run_dates: dict,
) -> BucketMetrics:
    grouped: dict = defaultdict(list)
    for obs in observations:
        if obs.rank != rank:
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
        bucket=f"rank_{rank}",
        horizon=horizon,
        per_run_returns=per_run_returns,
        stock_returns=stock_returns,
        benchmark_returns=benchmark_returns,
    )


def _spearman_correlation(ranks: list[int], values: list[float]) -> float | None:
    if len(ranks) < 2 or len(ranks) != len(values):
        return None
    n = len(ranks)

    def rank_data(data: list[float]) -> list[float]:
        sorted_idx = sorted(range(len(data)), key=lambda i: data[i])
        out = [0.0] * len(data)
        i = 0
        while i < len(data):
            j = i
            while j + 1 < len(data) and data[sorted_idx[j + 1]] == data[sorted_idx[i]]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[sorted_idx[k]] = avg_rank
            i = j + 1
        return out

    rank_r = rank_data([float(r) for r in ranks])
    rank_v = rank_data(values)
    mean_r = sum(rank_r) / n
    mean_v = sum(rank_v) / n
    num = sum((rank_r[i] - mean_r) * (rank_v[i] - mean_v) for i in range(n))
    den_r = sum((rank_r[i] - mean_r) ** 2 for i in range(n))
    den_v = sum((rank_v[i] - mean_v) ** 2 for i in range(n))
    if den_r == 0 or den_v == 0:
        return None
    return num / (den_r**0.5 * den_v**0.5)


def _count_alpha_inversions(alphas_by_rank: dict[int, float]) -> int:
    inversions = 0
    for rank in range(1, 20):
        a_lo = alphas_by_rank.get(rank)
        a_hi = alphas_by_rank.get(rank + 1)
        if a_lo is not None and a_hi is not None and a_lo > a_hi:
            inversions += 1
    return inversions


def _detect_cliffs(alphas_by_rank: dict[int, float], horizon: int) -> tuple[CliffEvent, ...]:
    cliffs: list[CliffEvent] = []
    for rank in range(1, 20):
        a_lo = alphas_by_rank.get(rank)
        a_hi = alphas_by_rank.get(rank + 1)
        if a_lo is None or a_hi is None:
            continue
        jump = a_hi - a_lo
        if jump >= CLIFF_ALPHA_JUMP_THRESHOLD:
            cliffs.append(
                CliffEvent(rank_from=rank, rank_to=rank + 1, horizon=horizon, alpha_jump=jump)
            )
    return tuple(cliffs)


def _noisy_ranks(alphas_by_rank: dict[int, float], obs_by_rank: dict[int, int]) -> tuple[int, ...]:
    noisy: list[int] = []
    for rank, alpha in alphas_by_rank.items():
        if obs_by_rank.get(rank, 0) < MIN_OBS_FOR_RANK_ANALYSIS:
            continue
        if alpha is not None and abs(alpha) < NOISY_ALPHA_ABS_THRESHOLD:
            noisy.append(rank)
    return tuple(sorted(noisy))


def _metrics_for_rank_range(
    *,
    rank_start: int,
    rank_end: int,
    horizon: int,
    observations: list[EnrichedStockObservation],
    benchmark_by_run: dict,
    run_dates: dict,
) -> BucketMetrics:
    grouped: dict = defaultdict(list)
    for obs in observations:
        if obs.rank < rank_start or obs.rank > rank_end:
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
        bucket=f"rank_{rank_start}_{rank_end}",
        horizon=horizon,
        per_run_returns=per_run_returns,
        stock_returns=stock_returns,
        benchmark_returns=benchmark_returns,
    )


def build_rank_decile_monotonicity(
    per_rank: dict[int, dict[int, BucketMetrics]],
    horizon: int,
) -> DecileMonotonicitySummary:
    """Pair ranks 1–2, 3–4, … 19–20 into ten deciles (decile 1 = best ranks)."""
    decile_alphas: dict[int, float] = {}
    for decile in range(1, 11):
        rank_start = (decile - 1) * 2 + 1
        rank_end = rank_start + 1
        alphas = []
        for rank in range(rank_start, rank_end + 1):
            m = per_rank.get(rank, {}).get(horizon)
            if m and m.alpha is not None and m.status == "ok":
                alphas.append(m.alpha)
        if alphas:
            decile_alphas[decile] = sum(alphas) / len(alphas)

    deciles = sorted(decile_alphas.keys())
    values = [decile_alphas[d] for d in deciles]
    spearman = _spearman_correlation(deciles, values) if len(values) >= 3 else None
    inversions = 0
    for d in range(1, 10):
        a_lo = decile_alphas.get(d)
        a_hi = decile_alphas.get(d + 1)
        if a_lo is not None and a_hi is not None and a_lo > a_hi:
            inversions += 1
    monotonic = spearman is not None and spearman <= -0.2 and inversions <= 4
    return DecileMonotonicitySummary(
        horizon=horizon,
        decile_alphas=decile_alphas,
        spearman_correlation=spearman,
        inversion_count=inversions,
        monotonic=monotonic,
    )


def build_score_quintile_metrics(
    *,
    strategy_name: str,
    regime_label: str,
    horizon: int,
    observations: list[EnrichedStockObservation],
    benchmark_by_run: dict,
) -> tuple[ScoreQuintileMetrics, ...]:
    """Quintile 1 = highest composite score within each run's top-20 set."""
    from app.outcome_attribution.constants import REGIME_LABEL_ALL

    if regime_label == REGIME_LABEL_ALL:
        subset = [o for o in observations if o.strategy_name == strategy_name and o.rank <= 20]
    else:
        subset = [
            o
            for o in observations
            if o.strategy_name == strategy_name
            and o.regime_label == regime_label
            and o.rank <= 20
        ]
    if not subset:
        return ()

    by_run: dict = defaultdict(list)
    for obs in subset:
        if obs.returns.get(horizon) is not None:
            by_run[obs.run_id].append(obs)

    quintile_returns: dict[int, list[float]] = defaultdict(list)
    quintile_alphas: dict[int, list[float]] = defaultdict(list)
    run_dates: dict = {}

    for run_id, run_obs in by_run.items():
        if len(run_obs) < 5:
            continue
        run_dates[run_id] = run_obs[0].as_of_date
        sorted_obs = sorted(run_obs, key=lambda o: (-o.score, o.rank))
        n = len(sorted_obs)
        for idx, obs in enumerate(sorted_obs):
            quintile = min(5, 1 + (idx * 5) // n)
            ret = obs.returns.get(horizon)
            if ret is None:
                continue
            quintile_returns[quintile].append(ret)
            bench = benchmark_by_run.get(run_id)
            bench_ret = bench.returns.get(horizon) if bench else None
            alpha = ret - bench_ret if bench_ret is not None else ret
            quintile_alphas[quintile].append(alpha)

    results: list[ScoreQuintileMetrics] = []
    for quintile in range(1, 6):
        alphas = quintile_alphas.get(quintile, [])
        returns = quintile_returns.get(quintile, [])
        if not alphas:
            continue
        avg_alpha = sum(alphas) / len(alphas)
        avg_return = sum(returns) / len(returns) if returns else None
        hit = sum(1 for a in alphas if a > 0) / len(alphas)
        results.append(
            ScoreQuintileMetrics(
                quintile=quintile,
                horizon=horizon,
                hit_rate=hit,
                average_return=avg_return,
                alpha=avg_alpha,
                observation_count=len(alphas),
            )
        )
    return tuple(results)


def build_strategy_rank_reliability(
    *,
    strategy_name: str,
    regime_label: str,
    observations: list[EnrichedStockObservation],
    benchmark_by_run: dict,
) -> StrategyRankReliability | None:
    if regime_label == REGIME_LABEL_ALL:
        subset = [o for o in observations if o.strategy_name == strategy_name]
    else:
        subset = [
            o
            for o in observations
            if o.strategy_name == strategy_name and o.regime_label == regime_label
        ]
    if not subset:
        return None

    run_dates = {obs.run_id: obs.as_of_date for obs in subset}
    per_rank: dict[int, dict[int, BucketMetrics]] = {}
    for rank in EXACT_RANKS:
        per_rank[rank] = {}
        for horizon in RESEARCH_HORIZONS:
            per_rank[rank][horizon] = _metrics_for_exact_rank(
                rank=rank,
                horizon=horizon,
                observations=subset,
                benchmark_by_run=benchmark_by_run,
                run_dates=run_dates,
            )

    monotonicity: dict[int, MonotonicitySummary] = {}
    cliffs_all: list[CliffEvent] = []

    for horizon in RESEARCH_HORIZONS:
        alphas: dict[int, float] = {}
        obs_counts: dict[int, int] = {}
        for rank in EXACT_RANKS:
            m = per_rank[rank][horizon]
            obs_counts[rank] = m.observation_count
            if m.alpha is not None and m.status == "ok":
                alphas[rank] = m.alpha

        ranks_sorted = sorted(alphas.keys())
        values = [alphas[r] for r in ranks_sorted]
        spearman = _spearman_correlation(ranks_sorted, values) if len(values) >= 3 else None
        inversions = _count_alpha_inversions(alphas)
        # Negative spearman expected if higher rank = better (lower rank number = higher alpha)
        monotonic = spearman is not None and spearman <= -0.15 and inversions <= 8
        top5_alpha = mean_or_none([alphas.get(r) for r in range(1, 6) if r in alphas])
        rank6_10_alpha = mean_or_none([alphas.get(r) for r in range(6, 11) if r in alphas])
        top5_overconfident = (
            top5_alpha is not None
            and rank6_10_alpha is not None
            and top5_alpha < rank6_10_alpha - 0.002
        )
        notes_parts: list[str] = []
        if spearman is not None:
            notes_parts.append(f"Spearman(rank, alpha)={spearman:.3f}")
        notes_parts.append(f"alpha inversions={inversions}")
        if top5_overconfident:
            notes_parts.append("top-5 avg alpha below ranks 6-10")

        monotonicity[horizon] = MonotonicitySummary(
            horizon=horizon,
            spearman_correlation=spearman,
            inversion_count=inversions,
            monotonic=monotonic,
            top5_overconfident=top5_overconfident,
            notes="; ".join(notes_parts),
        )
        cliffs_all.extend(_detect_cliffs(alphas, horizon))

    noisy = _noisy_ranks(
        {r: per_rank[r][20].alpha for r in EXACT_RANKS if per_rank[r][20].alpha is not None},
        {r: per_rank[r][20].observation_count for r in EXACT_RANKS},
    )

    decile_mono = {
        h: build_rank_decile_monotonicity(per_rank, h) for h in RESEARCH_HORIZONS
    }
    score_quintiles = {
        h: build_score_quintile_metrics(
            strategy_name=strategy_name,
            regime_label=regime_label,
            horizon=h,
            observations=subset,
            benchmark_by_run=benchmark_by_run,
        )
        for h in RESEARCH_HORIZONS
    }

    return StrategyRankReliability(
        strategy_name=strategy_name,
        regime_label=regime_label,
        per_rank=per_rank,
        monotonicity=monotonicity,
        decile_monotonicity=decile_mono,
        score_quintiles=score_quintiles,
        cliffs=tuple(cliffs_all),
        noisy_ranks=noisy,
    )
