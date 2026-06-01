from __future__ import annotations

from datetime import date

from pydantic import BaseModel, model_validator


class ResearchIntelligenceGenerateRequest(BaseModel):
    universe_code: str
    start_date: date
    end_date: date
    holdout_start_date: date = date(2025, 1, 1)
    persist: bool = True

    @model_validator(mode="after")
    def validate_dates(self) -> ResearchIntelligenceGenerateRequest:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self
