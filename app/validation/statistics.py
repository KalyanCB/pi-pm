from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from statistics import median

from app.validation.constants import MIN_IC_SAMPLE_SIZE
from app.validation.models import DecileBucket, FullHorizonMetrics, HitRateMetrics, HorizonMetrics

_QUANTIZE = Decimal("0.00000001")
_HORIZON_STATUS_OK = "ok"
_HORIZON_STATUS_INSUFFICIENT = "insufficient_data"


@dataclass(frozen=True)
class _ScoredReturn:
    symbol: str
    score: Decimal
    rank: int
    forward_return: Decimal


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTIZE, rounding=ROUND_HALF_UP)


def _rank_values(values: list[Decimal]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: (item[1], item[0]))
    ranks = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        j = index
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[index][1]:
            j += 1
        avg_rank = (index + j) / 2.0 + 1.0
        for k in range(index, j + 1):
            ranks[indexed[k][0]] = avg_rank
        index = j + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def pearson_ic(scores: list[Decimal], returns: list[Decimal]) -> Decimal | None:
    if len(scores) != len(returns) or len(scores) < MIN_IC_SAMPLE_SIZE:
        return None
    xs = [float(score) for score in scores]
    ys = [float(ret) for ret in returns]
    corr = _pearson(xs, ys)
    if corr is None:
        return None
    return _quantize(Decimal(str(corr)))


def spearman_ic(scores: list[Decimal], returns: list[Decimal]) -> Decimal | None:
    if len(scores) != len(returns) or len(scores) < MIN_IC_SAMPLE_SIZE:
        return None
    score_ranks = _rank_values(scores)
    return_ranks = _rank_values(returns)
    corr = _pearson(score_ranks, return_ranks)
    if corr is None:
        return None
    return _quantize(Decimal(str(corr)))


def assign_deciles(items: list[_ScoredReturn]) -> dict[int, list[_ScoredReturn]]:
    if not items:
        return {}
    sorted_items = sorted(items, key=lambda item: (-item.score, item.symbol))
    n = len(sorted_items)
    bucket_count = min(10, n)
    buckets: dict[int, list[_ScoredReturn]] = {i: [] for i in range(1, bucket_count + 1)}

    for index, item in enumerate(sorted_items):
        decile = min((index * bucket_count) // n + 1, bucket_count)
        buckets[decile].append(item)

    return buckets


def _mean_decimal(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return _quantize(sum(values, Decimal("0")) / Decimal(len(values)))


def _median_decimal(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return _quantize(Decimal(str(median([float(v) for v in values]))))


def _win_rate(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    wins = sum(1 for value in values if value > 0)
    return _quantize(Decimal(wins) / Decimal(len(values)))


def compute_deciles(items: list[_ScoredReturn]) -> tuple[DecileBucket, ...]:
    buckets = assign_deciles(items)
    result: list[DecileBucket] = []
    for decile in sorted(buckets):
        returns = [item.forward_return for item in buckets[decile]]
        result.append(
            DecileBucket(
                decile=decile,
                count=len(buckets[decile]),
                mean_return=_mean_decimal(returns),
                median_return=_median_decimal(returns),
                win_rate=_win_rate(returns),
            )
        )
    return tuple(result)


def compute_hit_rates(items: list[_ScoredReturn], deciles: tuple[DecileBucket, ...]) -> HitRateMetrics:
    if not items or not deciles:
        return HitRateMetrics(None, None, None)

    buckets = assign_deciles(items)
    top_items = buckets.get(1, [])
    bottom_decile_num = max(buckets)
    bottom_items = buckets.get(bottom_decile_num, [])
    bottom_decile = deciles[-1]

    all_returns = [item.forward_return for item in items]
    cross_median = _median_decimal(all_returns)
    bottom_mean = bottom_decile.mean_return

    top_vs_median: Decimal | None = None
    if cross_median is not None and top_items:
        hits = sum(1 for item in top_items if item.forward_return > cross_median)
        top_vs_median = _quantize(Decimal(hits) / Decimal(len(top_items)))

    top_vs_bottom: Decimal | None = None
    if bottom_mean is not None and top_items:
        hits = sum(1 for item in top_items if item.forward_return > bottom_mean)
        top_vs_bottom = _quantize(Decimal(hits) / Decimal(len(top_items)))

    directional: Decimal | None = None
    sorted_items = sorted(items, key=lambda item: (-item.score, item.symbol))
    if len(sorted_items) >= 2:
        pairs = 0
        hits = 0
        for i in range(len(sorted_items)):
            for j in range(i + 1, len(sorted_items)):
                if sorted_items[i].score == sorted_items[j].score:
                    continue
                pairs += 1
                score_order = sorted_items[i].score > sorted_items[j].score
                return_order = sorted_items[i].forward_return > sorted_items[j].forward_return
                if score_order == return_order:
                    hits += 1
        if pairs > 0:
            directional = _quantize(Decimal(hits) / Decimal(pairs))

    return HitRateMetrics(top_vs_median, top_vs_bottom, directional)


def compute_top_n_return(items: list[_ScoredReturn], n: int) -> Decimal | None:
    if not items or n <= 0:
        return None
    sorted_items = sorted(items, key=lambda item: (item.rank, item.symbol))
    top_items = sorted_items[: min(n, len(sorted_items))]
    if not top_items:
        return None
    return _mean_decimal([item.forward_return for item in top_items])


def is_decile_monotonic(deciles: tuple[DecileBucket, ...]) -> bool:
    if len(deciles) < 2:
        return False
    means = [bucket.mean_return for bucket in deciles if bucket.mean_return is not None]
    if len(means) < 2:
        return False
    return all(means[index] >= means[index + 1] for index in range(len(means) - 1))


def compute_full_horizon_metrics(
    horizon: int,
    scored_returns: list[_ScoredReturn],
    *,
    ranked_days: int = 1,
) -> FullHorizonMetrics:
    if len(scored_returns) < MIN_IC_SAMPLE_SIZE:
        return FullHorizonMetrics(
            horizon=horizon,
            status=_HORIZON_STATUS_INSUFFICIENT,
            ic_pearson=None,
            rank_ic_spearman=None,
            hit_rate=None,
            directional_hit_rate=None,
            top_decile_return=None,
            bottom_decile_return=None,
            spread=None,
            top_20_return=None,
            top_50_return=None,
            deciles=(),
            is_monotonic=False,
            sample_size=len(scored_returns),
            ranked_days=ranked_days,
        )

    scores = [item.score for item in scored_returns]
    returns = [item.forward_return for item in scored_returns]
    ic = pearson_ic(scores, returns)
    rank_ic = spearman_ic(scores, returns)
    deciles = compute_deciles(scored_returns)
    hit_rates = compute_hit_rates(scored_returns, deciles)

    top_decile = deciles[0].mean_return if deciles else None
    bottom_decile = deciles[-1].mean_return if deciles else None
    spread: Decimal | None = None
    if top_decile is not None and bottom_decile is not None:
        spread = _quantize(top_decile - bottom_decile)

    return FullHorizonMetrics(
        horizon=horizon,
        status=_HORIZON_STATUS_OK if ic is not None or rank_ic is not None else _HORIZON_STATUS_INSUFFICIENT,
        ic_pearson=ic,
        rank_ic_spearman=rank_ic,
        hit_rate=hit_rates.top_vs_median_hit_rate,
        directional_hit_rate=hit_rates.rank_directional_hit_rate,
        top_decile_return=top_decile,
        bottom_decile_return=bottom_decile,
        spread=spread,
        top_20_return=compute_top_n_return(scored_returns, 20),
        top_50_return=compute_top_n_return(scored_returns, 50),
        deciles=deciles,
        is_monotonic=is_decile_monotonic(deciles),
        sample_size=len(scored_returns),
        ranked_days=ranked_days,
    )


def compute_horizon_metrics(
    horizon: int,
    scored_returns: list[_ScoredReturn],
) -> HorizonMetrics:
    if len(scored_returns) < MIN_IC_SAMPLE_SIZE:
        empty_hits = HitRateMetrics(None, None, None)
        return HorizonMetrics(
            horizon=horizon,
            status=_HORIZON_STATUS_INSUFFICIENT,
            ic_spearman=None,
            deciles=(),
            top_minus_bottom_spread=None,
            hit_rates=empty_hits,
            sample_size=len(scored_returns),
        )

    scores = [item.score for item in scored_returns]
    returns = [item.forward_return for item in scored_returns]
    ic = spearman_ic(scores, returns)
    deciles = compute_deciles(scored_returns)
    hit_rates = compute_hit_rates(scored_returns, deciles)

    spread: Decimal | None = None
    if deciles and deciles[0].mean_return is not None and deciles[-1].mean_return is not None:
        spread = _quantize(deciles[0].mean_return - deciles[-1].mean_return)

    return HorizonMetrics(
        horizon=horizon,
        status=_HORIZON_STATUS_OK if ic is not None else _HORIZON_STATUS_INSUFFICIENT,
        ic_spearman=ic,
        deciles=deciles,
        top_minus_bottom_spread=spread,
        hit_rates=hit_rates,
        sample_size=len(scored_returns),
    )
