from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.args import LlmExecutionRecord


class LlmExecutionRecordRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        model: str,
        provider: str = "mock",
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LlmExecutionRecord:
        row = LlmExecutionRecord(
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            metadata_=metadata,
            created_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.flush()
        return row
