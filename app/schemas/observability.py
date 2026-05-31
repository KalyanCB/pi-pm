from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LineageRecordRead(BaseModel):
    child_entity_type: str
    child_entity_id: str
    parent_entity_type: str
    parent_entity_id: str
    relationship_type: str
    created_at: str


class ExperimentRunCreate(BaseModel):
    experiment_name: str = Field(min_length=1, max_length=128)
    strategy_name: str
    strategy_version: str
    parameter_set: dict = Field(default_factory=dict)
    notes: str | None = None


class ExperimentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    experiment_id: UUID
    experiment_name: str
    strategy_name: str
    strategy_version: str
    parameter_set: dict
    status: str
    started_at: str
    completed_at: str | None = None
    notes: str | None = None


class FactorContributionRead(BaseModel):
    factor_name: str
    raw: float | None
    normalized: float | None
    weighted: float | None


class ScoreReconstructionRead(BaseModel):
    ranking_run_id: str
    stock_id: str
    reconstructed_score: float
    factors: list[FactorContributionRead]
