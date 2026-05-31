from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class RegimePolicyConfigCreate(BaseModel):
    policy_name: str = Field(min_length=1, max_length=64)
    policy_type: str = Field(min_length=1, max_length=32)
    strategy_name: str = Field(min_length=1, max_length=64)
    strategy_version: str = Field(min_length=1, max_length=32)
    allowed_regimes: list[str]
    size_multipliers: dict[str, float]
    min_decile: int | None = None
    max_decile: int | None = None
    default_action: str = Field(min_length=1, max_length=16)
    notes: str | None = None


class RegimePolicyConfigRead(BaseModel):
    id: UUID
    policy_name: str
    policy_type: str
    strategy_name: str
    strategy_version: str
    policy_version: int
    allowed_regimes: list[str]
    size_multipliers: dict[str, float]
    min_decile: int | None
    max_decile: int | None
    default_action: str
    status: str
    effective_from: date | None
    notes: str | None
    created_at: str
    activated_at: str | None


class RegimePolicyEvaluateRequest(BaseModel):
    ranking_run_id: UUID
    policy_config_id: UUID | None = None
    persist: bool = False


class RegimePolicyEvaluateResponse(BaseModel):
    policy_config_id: str
    ranking_run_id: str
    as_of_date: str
    regime_label: str | None
    action: str
    size_multiplier: float
    decile_filter: int | None
    reason: str


class RegimePolicyBacktestRunRequest(BaseModel):
    strategy_name: str = "breakout_v1"
    strategy_version: str = "1.0.0"
    universe_code: str
    horizon: int = 20
    start_date: date
    end_date: date
    holdout_start_date: date = date(2025, 1, 1)
    policy_config_ids: list[UUID]
    baseline_policy_config_id: UUID
    experiment_name: str = "sprint81_regime_gate_comparison"
    persist_decisions: bool = True

    @model_validator(mode="after")
    def validate_dates(self) -> RegimePolicyBacktestRunRequest:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if not (self.start_date <= self.holdout_start_date <= self.end_date):
            raise ValueError("holdout_start_date must be within [start_date, end_date]")
        return self


class RegimePolicyPresetLoadRequest(BaseModel):
    dry_run: bool = False


class RegimePolicyPresetLoadResponse(BaseModel):
    loaded_count: int
    config_ids: list[str]
    dry_run: bool
