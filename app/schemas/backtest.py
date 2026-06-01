from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.schemas.ranking import UniverseFilterConfigSchema


class GenerateRankingsRequest(BaseModel):
    universe_code: str | None = None
    start_date: date
    end_date: date
    strategy_name: str | None = None
    strategy_version: str | None = None
    benchmark_symbol: str | None = None
    filter_config: UniverseFilterConfigSchema | None = None
    force_regenerate: bool = False

    @model_validator(mode="after")
    def validate_date_range(self) -> GenerateRankingsRequest:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class GenerateRankingsResponse(BaseModel):
    universe_code: str
    strategy_name: str
    strategy_version: str
    benchmark_symbol: str
    start_date: date
    end_date: date
    trading_days_total: int
    runs_created: int
    runs_reused: int
    runs_failed: int
    failed_dates: list[date] = Field(default_factory=list)
