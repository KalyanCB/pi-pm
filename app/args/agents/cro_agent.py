from __future__ import annotations

import json
from collections import Counter

from app.args.llm.port import LlmPort
from app.workspace_args.committee_contracts import (
    CommitteeReviewOutput,
    CroAggregationOutput,
    CroAggregationResult,
)
from app.workspace_args.constants import COMMITTEE_CRO


def aggregate_committee_reviews(
    symbol: str,
    reviews: list[CommitteeReviewOutput],
    llm: LlmPort,
) -> CroAggregationResult:
    labels = [r.research_label for r in reviews]
    label_counts = dict(Counter(labels))
    committee_summaries = [
        {
            "committee_code": r.committee_code,
            "research_label": r.research_label,
            "confidence": r.confidence,
            "findings": r.findings[:200],
        }
        for r in reviews
    ]
    disagreements = [
        r.committee_code
        for r in reviews
        if r.research_label == "cautious" and label_counts.get("supportive", 0) > 0
    ]
    system = (
        f"{COMMITTEE_CRO} research officer. Summarize committee consensus and disagreement only. "
        "Never recommend buy/sell/hold, rank securities, or suggest position sizes."
    )
    user = json.dumps({"symbol": symbol, "committees": committee_summaries}, default=str)
    completion = llm.complete(system=system, user=user)
    parsed = json.loads(completion.content)
    snapshot = {
        "committee_count": len(reviews),
        "label_distribution": label_counts,
        "committee_summaries": committee_summaries,
    }
    output = CroAggregationOutput(
        aggregation_snapshot=snapshot,
        rationale=parsed.get("rationale", "Aggregated committee research."),
        dissent_summary=parsed.get("dissent_summary", {"disagreements": disagreements}),
        confidence=float(parsed.get("confidence", 0.75)),
        summary=parsed.get("summary", f"Research synthesis for {symbol}."),
        structured=parsed.get("structured", {"consensus": [r.committee_code for r in reviews]}),
        evidence_refs=[
            {"ref": ev.get("ref", "unknown"), "committee": r.committee_code}
            for r in reviews
            for ev in r.supporting_evidence[:3]
            if isinstance(ev, dict)
        ],
    )
    return CroAggregationResult(
        output=output,
        model=completion.model,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
    )
