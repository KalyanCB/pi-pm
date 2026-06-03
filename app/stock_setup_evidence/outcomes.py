from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.ranking.math_utils import PriceBar, bars_on_or_before
from app.stock_setup_evidence.constants import REGIME_LABEL_ALL_REGIMES
from app.stock_setup_evidence.statistics import (
    confidence_interval_95_mean,
    max_or_none,
    mean_or_none,
    median_or_none,
    min_or_none,
    std_dev_sample,
    win_rate,
)


@dataclass(frozen=True)
class SetupOutcome:
    setup_date: date
    similarity_score: float
    regime_label: str | None
    return_5d: float | None
    return_20d: float | None
    max_drawdown_20d: float | None
    max_runup_20d: float | None


def _index_on_or_before(bars: list[PriceBar], setup_date: date) -> int | None:
    eligible = bars_on_or_before(bars, setup_date)
    if not eligible:
        return None
    last_date = eligible[-1].date
    for idx, bar in enumerate(bars):
        if bar.date == last_date:
            return idx
    return None


def forward_return(bars: list[PriceBar], setup_date: date, horizon_days: int) -> float | None:
    start_idx = _index_on_or_before(bars, setup_date)
    if start_idx is None:
        return None
    end_idx = start_idx + horizon_days
    if end_idx >= len(bars):
        return None
    start_px = float(bars[start_idx].close)
    end_px = float(bars[end_idx].close)
    if start_px <= 0:
        return None
    return (end_px / start_px) - 1.0


def max_drawdown_and_runup(
    bars: list[PriceBar], setup_date: date, horizon_days: int
) -> tuple[float | None, float | None]:
    start_idx = _index_on_or_before(bars, setup_date)
    if start_idx is None:
        return None, None
    end_idx = start_idx + horizon_days
    if end_idx >= len(bars):
        return None, None
    entry = float(bars[start_idx].close)
    if entry <= 0:
        return None, None
    window = bars[start_idx : end_idx + 1]
    peak = entry
    max_dd = 0.0
    max_run = 0.0
    for bar in window:
        px = float(bar.close)
        peak = max(peak, px)
        if peak > 0:
            max_dd = max(max_dd, (peak - px) / peak)
        max_run = max(max_run, (px - entry) / entry)
    return max_dd, max_run


def build_setup_outcomes(
    bars: list[PriceBar],
    matches: list[tuple[date, float, dict[str, float]]],
    regime_by_date: dict[date, str],
) -> list[SetupOutcome]:
    outcomes: list[SetupOutcome] = []
    for setup_date, sim, _profile in matches:
        dd, run = max_drawdown_and_runup(bars, setup_date, 20)
        outcomes.append(
            SetupOutcome(
                setup_date=setup_date,
                similarity_score=sim,
                regime_label=regime_by_date.get(setup_date),
                return_5d=forward_return(bars, setup_date, 5),
                return_20d=forward_return(bars, setup_date, 20),
                max_drawdown_20d=dd,
                max_runup_20d=run,
            )
        )
    return outcomes


@dataclass(frozen=True)
class RegimeAggregateMetrics:
    regime_label: str
    sample_size: int
    win_rate_5d: float | None
    win_rate_20d: float | None
    average_return_5d: float | None
    average_return_20d: float | None
    median_return_20d: float | None
    standard_deviation_20d: float | None
    max_return_20d: float | None
    min_return_20d: float | None
    confidence_interval_95_lower_20d: float | None
    confidence_interval_95_upper_20d: float | None
    avg_max_drawdown: float | None
    avg_max_runup: float | None
    avg_similarity_score: float | None

    # Legacy aliases for v1 consumers
    @property
    def occurrence_count(self) -> int:
        return self.sample_size

    @property
    def avg_return_5d(self) -> float | None:
        return self.average_return_5d

    @property
    def avg_return_20d(self) -> float | None:
        return self.average_return_20d


def aggregate_outcomes(
    outcomes: list[SetupOutcome],
    regime_label: str,
) -> RegimeAggregateMetrics:
    if regime_label == REGIME_LABEL_ALL_REGIMES:
        subset = outcomes
    else:
        subset = [o for o in outcomes if o.regime_label == regime_label]

    returns_5d = [o.return_5d for o in subset]
    returns_20d = [o.return_20d for o in subset]
    ci_lower, ci_upper = confidence_interval_95_mean(returns_20d)

    return RegimeAggregateMetrics(
        regime_label=regime_label,
        sample_size=len(subset),
        win_rate_5d=win_rate(returns_5d),
        win_rate_20d=win_rate(returns_20d),
        average_return_5d=mean_or_none(returns_5d),
        average_return_20d=mean_or_none(returns_20d),
        median_return_20d=median_or_none(returns_20d),
        standard_deviation_20d=std_dev_sample(returns_20d),
        max_return_20d=max_or_none(returns_20d),
        min_return_20d=min_or_none(returns_20d),
        confidence_interval_95_lower_20d=ci_lower,
        confidence_interval_95_upper_20d=ci_upper,
        avg_max_drawdown=mean_or_none([o.max_drawdown_20d for o in subset]),
        avg_max_runup=mean_or_none([o.max_runup_20d for o in subset]),
        avg_similarity_score=mean_or_none([o.similarity_score for o in subset]),
    )


def metrics_to_dict(agg: RegimeAggregateMetrics) -> dict:
    return {
        "regime_label": agg.regime_label,
        "sample_size": agg.sample_size,
        "occurrence_count": agg.sample_size,
        "win_rate_5d": agg.win_rate_5d,
        "win_rate_20d": agg.win_rate_20d,
        "average_return_5d": agg.average_return_5d,
        "average_return_20d": agg.average_return_20d,
        "avg_return_5d": agg.average_return_5d,
        "avg_return_20d": agg.average_return_20d,
        "median_return_20d": agg.median_return_20d,
        "standard_deviation_20d": agg.standard_deviation_20d,
        "max_return_20d": agg.max_return_20d,
        "min_return_20d": agg.min_return_20d,
        "confidence_interval_95_lower_20d": agg.confidence_interval_95_lower_20d,
        "confidence_interval_95_upper_20d": agg.confidence_interval_95_upper_20d,
        "avg_max_drawdown": agg.avg_max_drawdown,
        "avg_max_runup": agg.avg_max_runup,
        "avg_similarity_score": agg.avg_similarity_score,
    }
