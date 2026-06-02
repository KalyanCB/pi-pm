from __future__ import annotations

from app.args.llm.port import LlmPort
from app.workspace_args.committee_contracts import CommitteeResult, CommitteeReviewOutput
from app.workspace_args.constants import COMMITTEE_RC
from app.workspace_args.models import InvestmentReviewPacket


class RcStubCommitteePlugin:
    committee_code = COMMITTEE_RC
    version = "1.0.0-stub"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        _ = llm
        output = CommitteeReviewOutput(
            committee_code=self.committee_code,
            committee_version=self.version,
            findings="Risk committee stub — no sizing or stop-loss outputs in ARGS Phase 1.",
            strengths=["rank_visibility"],
            risks=["stub_mode"],
            supporting_evidence=[
                {"ref": f"ranking:rank:{packet.payload.get('ranking', {}).get('rank')}"}
            ],
            confidence=0.4,
            research_label="neutral",
        )
        return CommitteeResult(output=output, model="stub")
