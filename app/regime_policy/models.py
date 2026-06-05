from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    size_multiplier: Decimal
    reason: str
    decile_filter: int | None = None


@dataclass(frozen=True)
class PolicyEvaluationContext:
    regime_label: str | None
    decile: int | None = None


@dataclass(frozen=True)
class ReplayWindowSpec:
    """Walk-forward ready window specification."""

    mode: str
    start_date: date
    end_date: date
    holdout_start_date: date | None = None
    rolling_window_days: int | None = None
    walk_forward_step_days: int | None = None
    holdout_periods: tuple[tuple[date, date], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "holdout_start_date": (
                self.holdout_start_date.isoformat() if self.holdout_start_date else None
            ),
            "rolling_window_days": self.rolling_window_days,
            "walk_forward_step_days": self.walk_forward_step_days,
            "holdout_periods": [
                {"start": start.isoformat(), "end": end.isoformat()}
                for start, end in self.holdout_periods
            ],
        }

    def split_dates(self, as_of_date: date) -> str:
        if self.mode == "single_holdout" and self.holdout_start_date is not None:
            return "holdout" if as_of_date >= self.holdout_start_date else "train"
        for period_name, periods in (("holdout", self.holdout_periods),):
            for start, end in periods:
                if start <= as_of_date <= end:
                    return period_name
        return "train"


@dataclass(frozen=True)
class MetricWithSignificance:
    value: float | None
    ci_lower: float | None = None
    ci_upper: float | None = None
    p_value: float | None = None
    is_statistically_significant: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "p_value": self.p_value,
            "is_statistically_significant": self.is_statistically_significant,
        }


@dataclass(frozen=True)
class PeriodMetrics:
    ic_spearman: float | None
    spread: float | None
    hit_rate: float | None
    drawdown: float | None
    sample_count: int
    ranked_days: int
    spread_significance: MetricWithSignificance | None = None
    ic_significance: MetricWithSignificance | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ic_spearman": self.ic_spearman,
            "spread": self.spread,
            "hit_rate": self.hit_rate,
            "drawdown": self.drawdown,
            "sample_count": self.sample_count,
            "ranked_days": self.ranked_days,
        }
        if self.spread_significance is not None:
            payload["spread_significance"] = self.spread_significance.to_dict()
        if self.ic_significance is not None:
            payload["ic_significance"] = self.ic_significance.to_dict()
        return payload


@dataclass(frozen=True)
class DailyPortfolioReturn:
    as_of_date: date
    portfolio_return: Decimal
    size_multiplier: Decimal
    stock_count: int


@dataclass(frozen=True)
class ReplayDayResult:
    as_of_date: date
    ranking_run_id: UUID
    validation_report_id: UUID
    regime_label: str | None
    decision: PolicyDecision
    included: bool
    scored_returns_count: int = 0


@dataclass
class ReplayResult:
    policy_config_id: UUID
    window_spec: ReplayWindowSpec
    horizon: int
    train_metrics: PeriodMetrics
    holdout_metrics: PeriodMetrics
    days_included: int
    days_excluded: int
    day_results: list[ReplayDayResult] = field(default_factory=list)
    daily_returns: list[DailyPortfolioReturn] = field(default_factory=list)
    validation_report_ids: list[UUID] = field(default_factory=list)
