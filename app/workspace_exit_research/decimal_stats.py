from __future__ import annotations

import math
import random
from decimal import ROUND_HALF_UP, Decimal
from statistics import median

_QUANTIZE = Decimal("0.00000001")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTIZE, rounding=ROUND_HALF_UP)


def mean_decimal(values: list[Decimal]) -> Decimal:
    return _quantize(sum(values, Decimal("0")) / Decimal(len(values)))


def median_decimal(values: list[Decimal]) -> Decimal:
    return _quantize(Decimal(str(median([float(v) for v in values]))))


def pstdev_decimal(values: list[Decimal]) -> Decimal:
    if len(values) < 2:
        return Decimal("0")
    mean = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum((v - mean) ** 2 for v in values) / Decimal(len(values))
    return _quantize(Decimal(str(math.sqrt(float(variance)))))


def hit_rate_decimal(values: list[Decimal]) -> Decimal:
    wins = sum(1 for value in values if value > 0)
    return _quantize(Decimal(wins) / Decimal(len(values)))


def bootstrap_ci(
    values: list[Decimal],
    *,
    sample_count: int,
    confidence: float,
    seed: int,
) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    rng = random.Random(seed)
    n = len(values)
    means: list[Decimal] = []
    for _ in range(sample_count):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(mean_decimal(sample))
    means.sort()
    alpha = 1.0 - confidence
    lower_idx = int((alpha / 2) * sample_count)
    upper_idx = int((1 - alpha / 2) * sample_count) - 1
    lower_idx = max(0, min(lower_idx, sample_count - 1))
    upper_idx = max(0, min(upper_idx, sample_count - 1))
    return float(means[lower_idx]), float(means[upper_idx])
