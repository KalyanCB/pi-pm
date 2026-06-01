from __future__ import annotations

import random
from decimal import Decimal
from statistics import median, pstdev

from app.factor_analytics.constants import DATASET_SPLIT_ALL
from app.factor_analytics.window import include_in_split
from app.ranking.math_utils import (
    PriceBar,
    average_true_range,
    bars_on_or_before,
    simple_moving_average,
)
from app.validation.forward_returns import compute_forward_return
from app.workspace_exit_research.constants import (
    ALPHA_DECAY_MAX_DAYS,
    ATR_TRAIL_MULTIPLIER,
    BOOTSTRAP_CONFIDENCE,
    BOOTSTRAP_SAMPLE_COUNT,
    BOOTSTRAP_SEED,
    BREAKOUT_LOOKBACK_DAYS,
    FIXED_HOLD_DAYS,
    INSUFFICIENT_SAMPLE_STATUS,
    MIN_EXIT_SAMPLE_SIZE,
    POLICY_FAMILY_ALPHA_DECAY,
    POLICY_FAMILY_FIXED_HOLD,
    POLICY_FAMILY_RANK_DETERIORATION,
    POLICY_FAMILY_REGIME_EXIT,
    POLICY_FAMILY_TREND_FAILURE,
    RANK_EXIT_THRESHOLDS,
    REGIME_EXIT_VARIANTS,
    REGIME_LABEL_ALL,
    REGIME_LABELS,
    SNAPSHOT_RETURN_DAYS,
    TREND_FAILURE_VARIANTS,
)
from app.workspace_exit_research.data_cache import RankPathCache, RegimePathCache, ResearchBarCache
from app.workspace_exit_research.models import (
    AlphaDecayPointResult,
    ExitSimulationResult,
    PolicyMetricResult,
    SignalEntry,
)


def _entry_close(bars: list[PriceBar], entry_date) -> Decimal | None:
    eligible = bars_on_or_before(bars, entry_date)
    if not eligible:
        return None
    return eligible[-1].close


def _return_between(bars: list[PriceBar], entry_date, exit_date) -> Decimal | None:
    entry = _entry_close(bars, entry_date)
    if entry is None or entry <= 0:
        return None
    exit_bars = bars_on_or_before(bars, exit_date)
    if not exit_bars:
        return None
    exit_close = exit_bars[-1].close
    if exit_close <= 0:
        return None
    return (exit_close / entry) - Decimal("1")


def _trading_days_after(bars: list[PriceBar], entry_date, count: int) -> list[PriceBar]:
    future = [b for b in bars if b.date > entry_date]
    future.sort(key=lambda b: b.date)
    return future[:count]


def simulate_fixed_hold(entry: SignalEntry, hold_days: int, bars: list[PriceBar]) -> ExitSimulationResult:
    variant = f"FIXED_HOLD_{hold_days}"
    snapshot_map = {5: entry.return_5d, 10: entry.return_10d, 20: entry.return_20d, 60: entry.return_60d}
    if hold_days in SNAPSHOT_RETURN_DAYS and snapshot_map.get(hold_days) is not None:
        return ExitSimulationResult(
            POLICY_FAMILY_FIXED_HOLD,
            variant,
            snapshot_map[hold_days],
            hold_days,
            "TIME",
        )
    ret = compute_forward_return(bars, entry.entry_date, hold_days)
    return ExitSimulationResult(
        POLICY_FAMILY_FIXED_HOLD,
        variant,
        ret,
        hold_days,
        "TIME" if ret is not None else "DATA_END",
        censored=ret is None,
    )


def simulate_rank_exit(
    entry: SignalEntry,
    threshold: int,
    bars: list[PriceBar],
    rank_cache: RankPathCache,
) -> ExitSimulationResult:
    variant = f"RANK_EXIT_GT_{threshold}"
    path = rank_cache.ranks_after(entry.stock_id, entry.entry_date)
    exit_date = None
    for day, rank in path:
        if rank > threshold:
            exit_date = day
            break
    if exit_date is None:
        future = _trading_days_after(bars, entry.entry_date, 60)
        if len(future) >= 60:
            exit_date = future[59].date
            holding = 60
        else:
            return ExitSimulationResult(
                POLICY_FAMILY_RANK_DETERIORATION, variant, None, 0, "DATA_END", censored=True
            )
    else:
        holding = len([b for b in bars if entry.entry_date < b.date <= exit_date])
    ret = _return_between(bars, entry.entry_date, exit_date) if exit_date else None
    return ExitSimulationResult(
        POLICY_FAMILY_RANK_DETERIORATION,
        variant,
        ret,
        holding if exit_date else 0,
        "RANK" if path else "TIME",
        censored=ret is None,
    )


def simulate_regime_exit(
    entry: SignalEntry,
    variant: str,
    bars: list[PriceBar],
    regime_cache: RegimePathCache,
) -> ExitSimulationResult:
    if variant == "REGIME_NEVER":
        ret = compute_forward_return(bars, entry.entry_date, 60)
        return ExitSimulationResult(
            POLICY_FAMILY_REGIME_EXIT, variant, ret, 60, "TIME", censored=ret is None
        )
    changes = regime_cache.regime_changes_after(entry.entry_date, entry.regime_label)
    if not changes:
        ret = compute_forward_return(bars, entry.entry_date, 60)
        return ExitSimulationResult(
            POLICY_FAMILY_REGIME_EXIT, variant, ret, 60, "NO_CHANGE", censored=ret is None
        )
    change_date = changes[0]
    delay = {"REGIME_IMMEDIATE": 0, "REGIME_DELAY_3": 3, "REGIME_DELAY_5": 5}[variant]
    future = _trading_days_after(bars, change_date, delay + 1)
    if len(future) <= delay:
        return ExitSimulationResult(
            POLICY_FAMILY_REGIME_EXIT, variant, None, 0, "DATA_END", censored=True
        )
    exit_date = future[delay].date
    holding = len([b for b in bars if entry.entry_date < b.date <= exit_date])
    ret = _return_between(bars, entry.entry_date, exit_date)
    return ExitSimulationResult(
        POLICY_FAMILY_REGIME_EXIT, variant, ret, holding, "REGIME", censored=ret is None
    )


def simulate_trend_failure(
    entry: SignalEntry,
    variant: str,
    bars: list[PriceBar],
) -> ExitSimulationResult:
    future = _trading_days_after(bars, entry.entry_date, 60)
    if not future:
        return ExitSimulationResult(
            POLICY_FAMILY_TREND_FAILURE, variant, None, 0, "DATA_END", censored=True
        )
    entry_close = _entry_close(bars, entry.entry_date)
    if entry_close is None:
        return ExitSimulationResult(
            POLICY_FAMILY_TREND_FAILURE, variant, None, 0, "DATA_END", censored=True
        )
    pre_entry = bars_on_or_before(bars, entry.entry_date)
    breakout_level = max((b.close for b in pre_entry[-BREAKOUT_LOOKBACK_DAYS:]), default=entry_close)
    atr = average_true_range(pre_entry, 14) if len(pre_entry) >= 15 else None
    trail_stop = entry_close - ATR_TRAIL_MULTIPLIER * atr if atr else None
    peak = entry_close

    exit_date = future[-1].date
    exit_reason = "TIME"
    for index, bar in enumerate(future, start=1):
        peak = max(peak, bar.close)
        hist = bars_on_or_before(bars, bar.date)
        dma20 = simple_moving_average(hist, 20)
        dma50 = simple_moving_average(hist, 50)
        triggered = False
        if variant == "TREND_DMA20_BREAK" and dma20 is not None and bar.close < dma20:
            triggered = True
        elif variant == "TREND_DMA50_BREAK" and dma50 is not None and bar.close < dma50:
            triggered = True
        elif variant == "TREND_BREAKOUT_FAILURE" and bar.close < breakout_level:
            triggered = True
        elif variant == "TREND_ATR_TRAIL" and trail_stop is not None:
            trail_stop = max(trail_stop, peak - ATR_TRAIL_MULTIPLIER * (atr or Decimal("0")))
            if bar.close < trail_stop:
                triggered = True
        if triggered:
            exit_date = bar.date
            exit_reason = variant
            holding = index
            ret = _return_between(bars, entry.entry_date, exit_date)
            return ExitSimulationResult(
                POLICY_FAMILY_TREND_FAILURE, variant, ret, holding, exit_reason, censored=ret is None
            )
    ret = _return_between(bars, entry.entry_date, exit_date)
    return ExitSimulationResult(
        POLICY_FAMILY_TREND_FAILURE, variant, ret, len(future), exit_reason, censored=ret is None
    )


def alpha_decay_returns(entry: SignalEntry, bars: list[PriceBar]) -> dict[int, Decimal | None]:
    return {
        day: compute_forward_return(bars, entry.entry_date, day)
        for day in range(1, ALPHA_DECAY_MAX_DAYS + 1)
    }


def bootstrap_ci(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(values)
    means = []
    for _ in range(BOOTSTRAP_SAMPLE_COUNT):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / len(sample))
    means.sort()
    alpha = 1.0 - BOOTSTRAP_CONFIDENCE
    lower_idx = int((alpha / 2) * BOOTSTRAP_SAMPLE_COUNT)
    upper_idx = int((1 - alpha / 2) * BOOTSTRAP_SAMPLE_COUNT) - 1
    return means[max(0, lower_idx)], means[min(BOOTSTRAP_SAMPLE_COUNT - 1, upper_idx)]


class ExitMetricsEngine:
    def aggregate_policy(
        self,
        results: list[ExitSimulationResult],
        *,
        strategy_name: str,
        strategy_version: str,
        universe_code: str,
        regime_label: str,
        dataset_split: str,
        horizon: int,
        holdout_start_date,
        as_of_date_start,
        as_of_date_end,
    ) -> PolicyMetricResult | None:
        if not results:
            return None
        family = results[0].policy_family
        variant = results[0].policy_variant
        returns = [float(r.period_return) for r in results if r.period_return is not None]
        if len(returns) < MIN_EXIT_SAMPLE_SIZE:
            return PolicyMetricResult(
                family,
                variant,
                strategy_name,
                strategy_version,
                universe_code,
                regime_label,
                dataset_split,
                horizon,
                len(returns),
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                INSUFFICIENT_SAMPLE_STATUS,
                holdout_start_date,
                as_of_date_start,
                as_of_date_end,
            )
        mean_val = sum(returns) / len(returns)
        med = float(median(returns))
        std = float(pstdev(returns)) if len(returns) > 1 else 0.0
        hits = sum(1 for v in returns if v > 0) / len(returns)
        holdings = [float(r.holding_days) for r in results if r.period_return is not None]
        ci_lower, ci_upper = bootstrap_ci(returns)
        return PolicyMetricResult(
            family,
            variant,
            strategy_name,
            strategy_version,
            universe_code,
            regime_label,
            dataset_split,
            horizon,
            len(returns),
            mean_val,
            med,
            std,
            hits,
            sum(holdings) / len(holdings) if holdings else None,
            ci_lower,
            ci_upper,
            "ok",
            holdout_start_date,
            as_of_date_start,
            as_of_date_end,
        )

    def aggregate_alpha_decay(
        self,
        day_returns: dict[int, list[float]],
        *,
        regime_label: str,
        dataset_split: str,
    ) -> list[AlphaDecayPointResult]:
        points: list[AlphaDecayPointResult] = []
        cumulative: list[float] = []
        for day in range(1, ALPHA_DECAY_MAX_DAYS + 1):
            values = day_returns.get(day, [])
            if len(values) < MIN_EXIT_SAMPLE_SIZE:
                points.append(
                    AlphaDecayPointResult(
                        day,
                        regime_label,
                        dataset_split,
                        len(values),
                        None,
                        None,
                        INSUFFICIENT_SAMPLE_STATUS,
                    )
                )
                continue
            mean_val = sum(values) / len(values)
            cumulative.append(mean_val)
            cum_mean = sum(cumulative) / len(cumulative)
            points.append(
                AlphaDecayPointResult(
                    day,
                    regime_label,
                    dataset_split,
                    len(values),
                    mean_val,
                    cum_mean,
                    "ok",
                )
            )
        return points


def filter_entries(
    entries: list[SignalEntry],
    *,
    regime_label: str,
    dataset_split: str,
    holdout_start_date,
) -> list[SignalEntry]:
    filtered = []
    for entry in entries:
        if regime_label != REGIME_LABEL_ALL and entry.regime_label != regime_label:
            continue
        if not include_in_split(entry.entry_date, dataset_split, holdout_start_date):
            continue
        filtered.append(entry)
    return filtered


def run_all_simulations(
    entry: SignalEntry,
    bars: list[PriceBar],
    rank_cache: RankPathCache,
    regime_cache: RegimePathCache,
) -> list[ExitSimulationResult]:
    results: list[ExitSimulationResult] = []
    for days in FIXED_HOLD_DAYS:
        results.append(simulate_fixed_hold(entry, days, bars))
    for threshold in RANK_EXIT_THRESHOLDS:
        results.append(simulate_rank_exit(entry, threshold, bars, rank_cache))
    for variant in REGIME_EXIT_VARIANTS:
        results.append(simulate_regime_exit(entry, variant, bars, regime_cache))
    for variant in TREND_FAILURE_VARIANTS:
        results.append(simulate_trend_failure(entry, variant, bars))
    return results
