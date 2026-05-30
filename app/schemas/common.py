import re

from pydantic import BaseModel, Field, field_validator

from app.core.constants import SYMBOL_PATTERN, IngestPeriod


def normalize_symbol(value: str) -> str:
    return value.strip().upper()


class MarketDataIngestRequest(BaseModel):
    symbols: list[str] = Field(min_length=1)
    period: IngestPeriod = IngestPeriod.ONE_YEAR

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for raw in values:
            symbol = normalize_symbol(raw)
            if not re.match(SYMBOL_PATTERN, symbol):
                raise ValueError(f"Invalid symbol format: {raw}")
            normalized.append(symbol)
        return normalized
