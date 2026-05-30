from pydantic import BaseModel, Field, field_validator

from app.core.constants import IngestPeriod
from app.core.symbols import validate_ingest_symbol


class MarketDataIngestRequest(BaseModel):
    symbols: list[str] = Field(min_length=1)
    period: IngestPeriod = IngestPeriod.ONE_YEAR

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, values: list[str]) -> list[str]:
        return [validate_ingest_symbol(raw) for raw in values]
