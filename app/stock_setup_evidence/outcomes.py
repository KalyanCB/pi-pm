from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median

from app.ranking.math_utils import PriceBar, bars_on_or_before


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


def max_drawdown_and_runup(bars: list[PriceBar], setup_date: date, horizon_days: int) -> tuple[float | None, float | None]:
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
    trough = entry
    max_dd = 0.0
    max_run = 0.0
    for bar in window:
        px = float(bar.close)
        peak = max(peak, px)
        trough = min(trough, px)
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
        outcomes.append(
            SetupOutcome(
                setup_date=setup_date,
                similarity_score=sim,
                regime_label=regime_by_date.get(setup_date),
                return_5d=forward_return(bars, setup_date, 5),
                return_20d=forward_return(bars, setup_date, 20),
                max_drawdown_20d=max_drawdown_and_runup(bars, setup_date, 20)[0],
                max_runup_20d=max_drawdown_and_runup(bars, setup_date, 20)[1],
            )
        )
    return outcomes


@dataclass(frozen=True)
class RegimeAggregateMetrics:
    regime_label: str
    occurrence_count: int
    win_rate_5d: float | None
    win_rate_20d: float | None
    avg_return_5d: float | None
    avg_return_20d: float | None
    median_return_20d: float | None
    avg_max_drawdown: float | None
    avg_max_runup: float | None
    avg_similarity_score: float | None


def _win_rate(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(1 for v in present if v > 0) / len(present)


def _avg(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


def aggregate_outcomes(
    outcomes: list[SetupOutcome],
    regime_label: str,
) -> RegimeAggregateMetrics:
    if regime_label == "ALL_REGIMES":
        subset = outcomes
    else:
        subset = [o for o in outcomes if o.regime_label == regime_label]
    return RegimeAggregateMetrics(
        regime_label=regime_label,
        occurrence_count=len(subset),
        win_rate_5d=_win_rate([o.return_5d for o in subset]),
        win_rate_20d=_win_rate([o.return_20d for o in subset]),
        avg_return_5d=_avg([o.return_5d for o in subset]),
        avg_return_20d=_avg([o.return_20d for o in subset]),
        median_return_20d=(
            median([o.return_20d for o in subset if o.return_20d is not None])
            if any(o.return_20d is not None for o in subset)
            else None
        ),
        avg_max_drawdown=_avg([o.max_drawdown_20d for o in subset]),
        avg_max_runup=_avg([o.max_runup_20d for o in subset]),
        avg_similarity_score=_avg([o.similarity_score for o in subset]),
    )
