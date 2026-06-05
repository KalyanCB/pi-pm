"""Micro-benchmark: optimized alpha decay vs per-horizon compute_forward_return."""

from __future__ import annotations

import time
from datetime import date, timedelta
from decimal import Decimal

from app.ranking.math_utils import PriceBar
from app.validation.forward_returns import compute_forward_return
from app.workspace_exit_research.constants import ALPHA_DECAY_MAX_DAYS
from app.workspace_exit_research.forward_returns_index import BarForwardReturnIndex

BENCH_ENTRIES = 500
BENCH_BAR_COUNT = 250


def _synthetic_bars(start: date, count: int, base: float) -> list[PriceBar]:
    return [
        PriceBar(
            date=start + timedelta(days=offset),
            close=Decimal(f"{base + offset * 0.1:.6f}"),
            volume=1_000_000,
        )
        for offset in range(count)
    ]


def _legacy_alpha_decay(bars: list[PriceBar], as_of: date) -> dict[int, Decimal | None]:
    return {
        day: compute_forward_return(bars, as_of, day) for day in range(1, ALPHA_DECAY_MAX_DAYS + 1)
    }


def _optimized_alpha_decay(bars: list[PriceBar], as_of: date) -> dict[int, Decimal | None]:
    return BarForwardReturnIndex(bars, as_of).forward_returns_through(ALPHA_DECAY_MAX_DAYS)


def test_alpha_decay_benchmark_speedup():
    start = date(2020, 1, 1)
    cohort = [_synthetic_bars(start, BENCH_BAR_COUNT, 100.0 + i) for i in range(BENCH_ENTRIES)]
    as_of = start + timedelta(days=30)

    legacy_start = time.perf_counter()
    legacy_results = [_legacy_alpha_decay(bars, as_of) for bars in cohort]
    legacy_elapsed = time.perf_counter() - legacy_start

    optimized_start = time.perf_counter()
    optimized_results = [_optimized_alpha_decay(bars, as_of) for bars in cohort]
    optimized_elapsed = time.perf_counter() - optimized_start

    assert legacy_results == optimized_results
    speedup = legacy_elapsed / optimized_elapsed if optimized_elapsed > 0 else 0.0
    # Indexed path should be materially faster on representative workload.
    assert speedup >= 3.0, (
        f"expected >=3x speedup, got {speedup:.2f}x "
        f"(legacy={legacy_elapsed:.3f}s optimized={optimized_elapsed:.3f}s)"
    )
