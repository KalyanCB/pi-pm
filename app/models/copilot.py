from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class CopilotQueryLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "copilot_query_logs"

    session_id: Mapped[UUID | None] = mapped_column(nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(32), nullable=False)
    entities: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    retrieved_ids: Mapped[list[dict] | None] = mapped_column(JSONB)
    answer: Mapped[str | None] = mapped_column(Text)
    answer_hash: Mapped[str | None] = mapped_column(String(64))
    citations: Mapped[list[dict] | None] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    refused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
