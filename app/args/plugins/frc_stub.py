from __future__ import annotations

from app.args.llm.port import LlmPort
from app.workspace_args.committee_contracts import CommitteeResult, CommitteeReviewOutput
from app.workspace_args.constants import COMMITTEE_FRC
from app.workspace_args.models import InvestmentReviewPacket


class FrcStubCommitteePlugin:
    committee_code = COMMITTEE_FRC
    version = "1.0.0-stub"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        _ = llm
        output = CommitteeReviewOutput(
            committee_code=self.committee_code,
            committee_version=self.version,
            findings="Fundamental data not wired in Phase 1.",
            strengths=[],
            risks=["fundamental_data_unavailable"],
            supporting_evidence=[{"ref": "stub:frc"}],
            confidence=0.3,
            research_label="neutral",
        )
        return CommitteeResult(output=output, model="stub")
