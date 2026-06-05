"""Portfolio mobile DTOs (WS10) — dataclasses serialisable to JSON.

Consumed directly by mobile layer (M4). No transformation needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class PortfolioPerformanceDTO:
    from_date: str | None
    to_date: str | None
    total_return_pct: float | None
    cagr_pct: float | None
    alpha_pct: float | None
    volatility_pct: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    max_drawdown_pct: float | None
    turnover_pct: float | None
    win_rate: float | None
    profit_factor: float | None
    avg_holding_days: float | None
    avg_exposure_pct: float | None
    avg_cash_pct: float | None
    closed_positions: int
    open_positions: int


@dataclass
class RiskAlertDTO:
    code: str
    level: str
    message: str


@dataclass
class PortfolioRiskDTO:
    risk_level: str
    gross_exposure_pct: float | None
    cash_pct: float | None
    largest_position_pct: float | None
    top_3_concentration_pct: float | None
    max_sector_name: str | None
    max_sector_pct: float | None
    open_positions: int
    max_positions_allowed: int
    current_drawdown_pct: float | None
    alerts: list[RiskAlertDTO] = field(default_factory=list)


@dataclass
class SectorExposureDTO:
    sector: str
    weight_pct: float


@dataclass
class PortfolioExposureDTO:
    gross_exposure_pct: float | None
    cash_pct: float | None
    sector_exposures: list[SectorExposureDTO] = field(default_factory=list)


@dataclass
class PortfolioBenchmarkDTO:
    benchmark_symbol: str
    portfolio_return_pct: float | None
    benchmark_return_pct: float | None
    alpha_pct: float | None
    tracking_error_pct: float | None
    information_ratio: float | None
    outperformance_pct: float | None


@dataclass
class AttributionBucketDTO:
    label: str
    count: int
    avg_return_pct: float | None
    avg_alpha_pct: float | None
    win_rate: float | None
    contribution_pct: float | None


@dataclass
class PortfolioAttributionDTO:
    total_alpha_pct: float | None
    by_strategy: list[AttributionBucketDTO] = field(default_factory=list)
    by_conviction_band: list[AttributionBucketDTO] = field(default_factory=list)
    by_regime: list[AttributionBucketDTO] = field(default_factory=list)
    by_sector: list[AttributionBucketDTO] = field(default_factory=list)
    by_holding_duration: list[AttributionBucketDTO] = field(default_factory=list)
    by_committee_advisory: list[AttributionBucketDTO] = field(default_factory=list)
    note: str = ""


@dataclass
class ExitRecommendationDTO:
    id: str
    symbol: str | None
    status: str
    urgency: str
    triggers: list[str]
    current_rank: int | None
    days_held: int | None
    unrealized_pnl_pct: float | None
    as_of_date: str


@dataclass
class ContributorDTO:
    symbol: str | None
    contribution_pct: float | None
    conviction_band: str | None


@dataclass
class PortfolioDashboardDTO:
    """Future mobile dashboard model (WS11)."""
    nav: float | None
    today_change_pct: float | None
    alpha_pct: float | None
    cash_pct: float | None
    active_positions: int
    pending_exits: int
    risk_level: str
    risk_alerts: list[RiskAlertDTO]
    trust_score: float | None
    top_contributors: list[ContributorDTO]
    worst_contributors: list[ContributorDTO]
    reconciliation_status: str | None
