from __future__ import annotations

from app.args.llm.port import LlmPort
from app.workspace_args.committee_contracts import CommitteeResult, CommitteeReviewOutput
from app.workspace_args.constants import COMMITTEE_NRCC
from app.workspace_args.models import InvestmentReviewPacket


class NrccStubCommitteePlugin:
    committee_code = COMMITTEE_NRCC
    version = "1.0.0-stub"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        _ = llm
        output = CommitteeReviewOutput(
            committee_code=self.committee_code,
            committee_version=self.version,
            findings="News/catalyst feed not available — degraded stub.",
            strengths=[],
            risks=["news_feed_unavailable"],
            supporting_evidence=[{"ref": "stub:nrcc"}],
            confidence=0.25,
            research_label="neutral",
        )
        return CommitteeResult(output=output, model="stub")
