from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class InvestmentReviewPacket:
    """In-memory packet before persistence."""

    symbol: str
    stock_id: UUID
    ranking_run_id: UUID
    ranking_result_id: UUID
    payload: dict[str, Any]
    packet_hash: str
    packet_version: str = "1.0.0"


@dataclass
class PacketRef:
    packet_id: UUID
    packet_hash: str
    symbol: str
    stock_id: UUID


@dataclass
class WorkflowError:
    committee_code: str | None
    message: str
    phase: str


@dataclass
class ArgsWorkflowState:
    run_id: UUID
    run_config: dict[str, Any]
    ranking_run_id: UUID
    candidate_stock_ids: list[UUID] = field(default_factory=list)
    packets: list[InvestmentReviewPacket] = field(default_factory=list)
    packet_refs: list[PacketRef] = field(default_factory=list)
    committee_codes: list[str] = field(default_factory=list)
    reviews: list[Any] = field(default_factory=list)
    cro_outputs: list[Any] = field(default_factory=list)
    errors: list[WorkflowError] = field(default_factory=list)
    phase: str = "init"
    token_usage_total: int = 0
