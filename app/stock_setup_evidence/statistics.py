from __future__ import annotations

import math
from statistics import median, stdev

# Two-sided 95% t critical values (df = n-1) for small samples; large n → 1.96.
_T_CRITICAL_95: dict[int, float] = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    15: 2.131,
    20: 2.086,
    25: 2.060,
    30: 2.042,
}


def _t_critical_95(sample_size: int) -> float:
    if sample_size <= 0:
        return 1.96
    df = sample_size - 1
    if df >= 30:
        return 1.96
    return _T_CRITICAL_95.get(df, 2.0)


def mean_or_none(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


def win_rate(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(1 for v in present if v > 0) / len(present)


def std_dev_sample(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if len(present) < 2:
        return None
    return stdev(present)


def confidence_interval_95_mean(values: list[float | None]) -> tuple[float | None, float | None]:
    present = [v for v in values if v is not None]
    n = len(present)
    if n < 2:
        return None, None
    avg = sum(present) / n
    if n == 2:
        spread = abs(present[0] - present[1]) / 2
        return avg - spread, avg + spread
    sd = stdev(present)
    margin = _t_critical_95(n) * sd / math.sqrt(n)
    return avg - margin, avg + margin


def median_or_none(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return float(median(present))


def max_or_none(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return max(present)


def min_or_none(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return min(present)
