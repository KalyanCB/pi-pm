from __future__ import annotations

import json
from typing import Any

from app.args.llm.port import LlmPort
from app.workspace_args.committee_contracts import CommitteeResult, CommitteeReviewOutput
from app.workspace_args.evidence_validator import validate_committee_output
from app.workspace_args.models import InvestmentReviewPacket

FORBIDDEN_EXTENSION_KEYS = frozenset(
    {
        "vote",
        "recommendation",
        "recommendation_label",
        "position_size",
        "position_size_pct",
        "stop_loss",
        "stop_loss_pct",
        "final_score",
        "label",
    }
)


def execute_committee_llm(
    *,
    packet: InvestmentReviewPacket,
    llm: LlmPort,
    committee_code: str,
    committee_version: str,
    system: str,
    user_payload: dict[str, Any],
    strict_numeric_findings: bool = True,
) -> CommitteeResult:
    user = json.dumps(user_payload, default=str)
    completion = llm.complete(system=system, user=user)
    parsed = json.loads(completion.content)
    extensions = {
        k: v
        for k, v in parsed.items()
        if k
        not in {
            "findings",
            "strengths",
            "risks",
            "supporting_evidence",
            "confidence",
            "research_label",
            *FORBIDDEN_EXTENSION_KEYS,
        }
    }
    output = validate_committee_output(
        packet.payload,
        CommitteeReviewOutput(
            committee_code=committee_code,
            committee_version=committee_version,
            findings=parsed.get("findings", ""),
            strengths=list(parsed.get("strengths") or []),
            risks=list(parsed.get("risks") or []),
            supporting_evidence=list(parsed.get("supporting_evidence") or []),
            confidence=float(parsed.get("confidence", 0.5)),
            extensions=extensions,
            research_label=str(parsed.get("research_label", "neutral")),
        ),
        strict_numeric_findings=strict_numeric_findings,
    )
    return CommitteeResult(
        output=output,
        model=completion.model,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
    )
