from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class ValidationSnapshotRead(BaseModel):
    id: str
    stock_id: str
    symbol: str | None = None
    return_5d: float | None = None
    return_10d: float | None = None
    return_20d: float | None = None
    return_60d: float | None = None
    captured_at: str


class ValidationReportRead(BaseModel):
    ranking_run_id: str
    status: str
    validation_hash: str | None = None
    regime_label: str | None = None
    trend_regime: str | None = None
    vol_regime: str | None = None
    horizon_metrics: dict | None = None
    sample_summary: dict | None = None
    computed_at: str | None = None
    error_message: str | None = None


class RegimeIcRead(BaseModel):
    bull_low_vol_ic: str | None = None
    bull_high_vol_ic: str | None = None
    bear_low_vol_ic: str | None = None
    bear_high_vol_ic: str | None = None


class ValidationSummaryRead(BaseModel):
    reports_count: int
    horizon: int
    validated_runs: int = 0
    failed_runs: int = 0
    insufficient_data_runs: int = 0
    average_ic_20d: str | None = None
    median_ic_20d: str | None = None
    top_decile_return_20d: str | None = None
    bottom_decile_return_20d: str | None = None
    spread_20d: str | None = None
    hit_rate_20d: str | None = None
    directional_hit_rate_20d: str | None = None
    bull_market_ic: str | None = None
    bear_market_ic: str | None = None
    high_vol_ic: str | None = None
    low_vol_ic: str | None = None
    regime_ic: RegimeIcRead | None = None
    best_regime: str | None = None
    worst_regime: str | None = None


class BacktestSummaryRead(BaseModel):
    universe_code: str | None = None
    strategy_name: str | None = None
    strategy_version: str | None = None
    start_date: str
    end_date: str
    ranking_runs_total: int
    validated_runs_total: int
    pending_validation_runs: int


class ValidationBackfillRequest(BaseModel):
    start_date: date
    end_date: date
    force_recompute: bool = False

    @model_validator(mode="after")
    def validate_date_range(self) -> ValidationBackfillRequest:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ValidationBackfillResponse(BaseModel):
    runs_found: int = Field(ge=0)
    validated: int = Field(ge=0)
    reused: int = Field(ge=0)
    failed: int = Field(ge=0)
