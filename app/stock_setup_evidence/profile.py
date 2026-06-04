from __future__ import annotations

from datetime import date
from typing import Any

from app.ranking.math_utils import PriceBar, bars_on_or_before
from app.stock_setup_evidence.strategy_profiles import SeeStrategyConfig
from app.universe.models import StockSnapshot


def extract_reference_profile(
    score_components: dict[str, Any] | None,
    *,
    factor_names: tuple[str, ...],
) -> dict[str, float]:
    """Normalized factor vector from ranking score_components for a given strategy."""
    if not score_components:
        return {}
    profile: dict[str, float] = {}
    for name in factor_names:
        block = score_components.get(name)
        if not isinstance(block, dict):
            continue
        normalized = block.get("normalized")
        if normalized is None:
            continue
        try:
            profile[name] = float(normalized)
        except (TypeError, ValueError):
            continue
    return profile


def compute_raw_profile_at_date(
    stock: StockSnapshot,
    price_series: list[PriceBar],
    benchmark_series: list[PriceBar] | None,
    as_of_date: date,
    *,
    strategy_config: SeeStrategyConfig,
) -> dict[str, float]:
    raw = strategy_config.strategy.compute_raw_factors(
        stock, price_series, benchmark_series, as_of_date
    )
    out: dict[str, float] = {}
    for name in strategy_config.factor_names:
        value = raw.get(name)
        if value is None:
            continue
        try:
            out[name] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def build_stock_internal_normalized_profiles(
    stock: StockSnapshot,
    price_series: list[PriceBar],
    benchmark_series: list[PriceBar] | None,
    candidate_dates: list[date],
    *,
    strategy_config: SeeStrategyConfig,
    min_factors: int = 3,
) -> dict[date, dict[str, float]]:
    """Percentile-rank each factor within the stock's own history (0–1 scale)."""
    factor_names = strategy_config.factor_names
    raw_by_date: dict[date, dict[str, float]] = {}
    for d in candidate_dates:
        raw = compute_raw_profile_at_date(
            stock,
            price_series,
            benchmark_series,
            d,
            strategy_config=strategy_config,
        )
        if len(raw) >= min_factors:
            raw_by_date[d] = raw

    if not raw_by_date:
        return {}

    factor_values: dict[str, list[float]] = {name: [] for name in factor_names}
    for raw in raw_by_date.values():
        for name, value in raw.items():
            factor_values[name].append(value)

    normalized_by_date: dict[date, dict[str, float]] = {}
    for d, raw in raw_by_date.items():
        norm: dict[str, float] = {}
        for name, value in raw.items():
            series = factor_values.get(name) or []
            if len(series) < 2:
                norm[name] = 0.5
                continue
            sorted_vals = sorted(series)
            rank = sum(1 for v in sorted_vals if v <= value)
            norm[name] = rank / len(sorted_vals)
        normalized_by_date[d] = norm
    return normalized_by_date


def list_candidate_setup_dates(
    price_series: list[PriceBar],
    as_of_date: date,
    *,
    max_trading_days: int,
    sample_step: int,
) -> list[date]:
    bars = bars_on_or_before(price_series, as_of_date)
    if len(bars) < 60:
        return []
    window = bars[-max_trading_days:] if len(bars) > max_trading_days else bars
    dates = [b.date for b in window]
    sampled = dates[::sample_step]
    if dates and dates[-1] not in sampled:
        sampled.append(dates[-1])
    return [d for d in sampled if d < as_of_date]
