from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class UniverseFilterConfigSchema(BaseModel):
    min_history_days: int = Field(default=63, ge=1)
    min_avg_daily_traded_value: Decimal = Field(default=Decimal("10000000"), gt=0)
    min_stock_price: Decimal = Field(default=Decimal("50"), gt=0)
    require_data_status_active: bool = True
    require_stock_active: bool = True
    market_data_source: str = "yahoo"


class RankingRunRequest(BaseModel):
    universe_code: str | None = None
    as_of_date: date | None = None
    strategy_name: str | None = None
    strategy_version: str | None = None
    benchmark_symbol: str | None = None
    filter_config: UniverseFilterConfigSchema | None = None
    force_regenerate: bool = False


class RankingResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    stock_id: str
    symbol: str | None = None
    rank: int
    score: float
    score_components: dict | None = None


class RankingRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    universe_code: str
    as_of_date: date
    strategy_name: str
    strategy_version: str
    benchmark_symbol: str
    inputs_hash: str | None = None
    filter_config_hash: str
    normalization_method: str
    status: str
    started_at: str
    completed_at: str | None = None
    error_message: str | None = None
    metadata: dict | None = None
    results_count: int = 0
    results: list[RankingResultRead] = Field(default_factory=list)


class RankingTopRead(BaseModel):
    run_id: str
    as_of_date: date
    strategy_name: str
    strategy_version: str
    top: list[RankingResultRead]
