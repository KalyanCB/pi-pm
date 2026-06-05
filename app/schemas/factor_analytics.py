from __future__ import annotations

from datetime import date

from pydantic import BaseModel, model_validator


class FactorAnalyticsBackfillRequest(BaseModel):
    strategy_name: str = "breakout_v1"
    strategy_version: str = "1.0.0"
    universe_code: str
    start_date: date
    end_date: date
    holdout_start_date: date = date(2025, 1, 1)
    force_recompute: bool = False
    write_daily_metrics: bool = True

    @model_validator(mode="after")
    def validate_dates(self) -> FactorAnalyticsBackfillRequest:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class FactorAnalyticsBackfillResponse(BaseModel):
    run_id: str
    status: str
    reports_processed: int
    metrics_written: int
