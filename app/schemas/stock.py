from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    name: str
    exchange: str
    sector: str | None
    industry: str | None
    is_active: bool
    data_status: str
    created_at: datetime
    updated_at: datetime
