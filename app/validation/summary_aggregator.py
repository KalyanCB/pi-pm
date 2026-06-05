from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from statistics import median

from app.models.ranking_validation_report import RankingValidationReport
from app.validation.constants import (
    VALIDATION_STATUS_COMPLETED,
    VALIDATION_STATUS_FAILED,
    VALIDATION_STATUS_INSUFFICIENT_DATA,
)

_QUANTIZE = Decimal("0.00000001")
_REGIME_LABELS = (
    "BULL_LOW_VOL",
    "BULL_HIGH_VOL",
    "BEAR_LOW_VOL",
    "BEAR_HIGH_VOL",
)


@dataclass(frozen=True)
class CrossRunSummary:
    reports_count: int
    horizon: int
    validated_runs: int
    failed_runs: int
    insufficient_data_runs: int
    average_ic: str | None = None
    median_ic: str | None = None
    top_decile_return: str | None = None
    bottom_decile_return: str | None = None
    spread: str | None = None
    hit_rate: str | None = None
    directional_hit_rate: str | None = None
    bull_market_ic: str | None = None
    bear_market_ic: str | None = None
    high_vol_ic: str | None = None
    low_vol_ic: str | None = None
    regime_ic: dict[str, str | None] = field(default_factory=dict)
    best_regime: str | None = None
    worst_regime: str | None = None


def aggregate_cross_run_summary(
    reports: list[RankingValidationReport],
    *,
    horizon: int = 20,
    all_reports: list[RankingValidationReport] | None = None,
) -> CrossRunSummary:
    quality_reports = all_reports if all_reports is not None else reports
    horizon_key = str(horizon)

    ic_values: list[Decimal] = []
    top_returns: list[Decimal] = []
    bottom_returns: list[Decimal] = []
    spreads: list[Decimal] = []
    hit_rates: list[Decimal] = []
    directional_hit_rates: list[Decimal] = []
    bull_ics: list[Decimal] = []
    bear_ics: list[Decimal] = []
    high_vol_ics: list[Decimal] = []
    low_vol_ics: list[Decimal] = []
    regime_ics: dict[str, list[Decimal]] = {label: [] for label in _REGIME_LABELS}

    for report in reports:
        if report.status != VALIDATION_STATUS_COMPLETED or not report.horizon_metrics:
            continue
        metrics = report.horizon_metrics.get(horizon_key)
        if not metrics or metrics.get("status") != "ok":
            continue

        ic = _to_decimal(metrics.get("ic_spearman"))
        if ic is not None:
            ic_values.append(ic)
            if report.trend_regime == "BULL":
                bull_ics.append(ic)
            elif report.trend_regime == "BEAR":
                bear_ics.append(ic)
            if report.vol_regime == "HIGH_VOL":
                high_vol_ics.append(ic)
            elif report.vol_regime == "LOW_VOL":
                low_vol_ics.append(ic)
            if report.regime_label in regime_ics:
                regime_ics[report.regime_label].append(ic)

        deciles = metrics.get("deciles") or []
        if deciles:
            top = _to_decimal(deciles[0].get("mean_return"))
            bottom = _to_decimal(deciles[-1].get("mean_return"))
            if top is not None:
                top_returns.append(top)
            if bottom is not None:
                bottom_returns.append(bottom)

        spread = _to_decimal(metrics.get("top_minus_bottom_spread"))
        if spread is not None:
            spreads.append(spread)

        hit_rate_data = metrics.get("hit_rates") or {}
        top_vs_bottom = _to_decimal(hit_rate_data.get("top_vs_bottom_hit_rate"))
        if top_vs_bottom is not None:
            hit_rates.append(top_vs_bottom)

        directional = _to_decimal(hit_rate_data.get("rank_directional_hit_rate"))
        if directional is not None:
            directional_hit_rates.append(directional)

    regime_ic_avg = {label: _avg(values) for label, values in regime_ics.items()}
    best_regime, worst_regime = _best_worst_regime(regime_ic_avg)

    return CrossRunSummary(
        reports_count=len(reports),
        horizon=horizon,
        validated_runs=_count_status(quality_reports, VALIDATION_STATUS_COMPLETED),
        failed_runs=_count_status(quality_reports, VALIDATION_STATUS_FAILED),
        insufficient_data_runs=_count_status(quality_reports, VALIDATION_STATUS_INSUFFICIENT_DATA),
        average_ic=_avg(ic_values),
        median_ic=_median(ic_values),
        top_decile_return=_avg(top_returns),
        bottom_decile_return=_avg(bottom_returns),
        spread=_avg(spreads),
        hit_rate=_avg(hit_rates),
        directional_hit_rate=_avg(directional_hit_rates),
        bull_market_ic=_avg(bull_ics),
        bear_market_ic=_avg(bear_ics),
        high_vol_ic=_avg(high_vol_ics),
        low_vol_ic=_avg(low_vol_ics),
        regime_ic=regime_ic_avg,
        best_regime=best_regime,
        worst_regime=worst_regime,
    )


def cross_run_summary_to_dict(summary: CrossRunSummary) -> dict:
    horizon = summary.horizon
    regime_ic = {
        "bull_low_vol_ic": summary.regime_ic.get("BULL_LOW_VOL"),
        "bull_high_vol_ic": summary.regime_ic.get("BULL_HIGH_VOL"),
        "bear_low_vol_ic": summary.regime_ic.get("BEAR_LOW_VOL"),
        "bear_high_vol_ic": summary.regime_ic.get("BEAR_HIGH_VOL"),
    }
    return {
        "reports_count": summary.reports_count,
        "horizon": horizon,
        "validated_runs": summary.validated_runs,
        "failed_runs": summary.failed_runs,
        "insufficient_data_runs": summary.insufficient_data_runs,
        f"average_ic_{horizon}d": summary.average_ic,
        f"median_ic_{horizon}d": summary.median_ic,
        f"top_decile_return_{horizon}d": summary.top_decile_return,
        f"bottom_decile_return_{horizon}d": summary.bottom_decile_return,
        f"spread_{horizon}d": summary.spread,
        f"hit_rate_{horizon}d": summary.hit_rate,
        f"directional_hit_rate_{horizon}d": summary.directional_hit_rate,
        "bull_market_ic": summary.bull_market_ic,
        "bear_market_ic": summary.bear_market_ic,
        "high_vol_ic": summary.high_vol_ic,
        "low_vol_ic": summary.low_vol_ic,
        "regime_ic": regime_ic,
        "best_regime": summary.best_regime,
        "worst_regime": summary.worst_regime,
    }


def _count_status(reports: list[RankingValidationReport], status: str) -> int:
    return sum(1 for report in reports if report.status == status)


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _avg(values: list[Decimal]) -> str | None:
    if not values:
        return None
    avg = sum(values, Decimal("0")) / Decimal(len(values))
    return str(avg.quantize(_QUANTIZE, rounding=ROUND_HALF_UP))


def _median(values: list[Decimal]) -> str | None:
    if not values:
        return None
    return str(
        Decimal(str(median([float(value) for value in values]))).quantize(
            _QUANTIZE, rounding=ROUND_HALF_UP
        )
    )


def _best_worst_regime(
    regime_ic: dict[str, str | None],
) -> tuple[str | None, str | None]:
    scored: list[tuple[str, Decimal]] = []
    for label, value in regime_ic.items():
        if value is None:
            continue
        scored.append((label, Decimal(value)))
    if not scored:
        return None, None
    scored.sort(key=lambda item: item[1])
    return scored[-1][0], scored[0][0]
