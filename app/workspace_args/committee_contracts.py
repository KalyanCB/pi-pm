from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CommitteeReviewOutput:
    committee_code: str
    committee_version: str
    findings: str
    strengths: list[str]
    risks: list[str]
    supporting_evidence: list[dict[str, Any]]
    confidence: float
    extensions: dict[str, Any] = field(default_factory=dict)
    research_label: str = "neutral"


@dataclass(frozen=True)
class CommitteeResult:
    output: CommitteeReviewOutput
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class CroAggregationResult:
    output: CroAggregationOutput
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class CroAggregationOutput:
    aggregation_snapshot: dict[str, Any]
    rationale: str
    dissent_summary: dict[str, Any]
    confidence: float
    summary: str
    structured: dict[str, Any]
    evidence_refs: list[dict[str, Any]]


@dataclass(frozen=True)
class CroAggregationResult:
    output: CroAggregationOutput
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
