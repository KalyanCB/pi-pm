from __future__ import annotations

from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_FRC
from app.workspace_args.models import InvestmentReviewPacket


class FrcCommitteePlugin:
    committee_code = COMMITTEE_FRC
    version = "1.0.0"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        system = (
            f"{COMMITTEE_FRC} fundamental research committee. "
            "Use only market_snapshot, fundamental_snapshot, and research_context in the packet. "
            "Do not recommend buy/sell/hold, assign position sizes, or stop losses."
        )
        return execute_committee_llm(
            packet=packet,
            llm=llm,
            committee_code=self.committee_code,
            committee_version=self.version,
            system=system,
            user_payload={
                "symbol": packet.symbol,
                "market_snapshot": packet.payload.get("market_snapshot"),
                "fundamental_snapshot": packet.payload.get("fundamental_snapshot"),
                "research_context": packet.payload.get("research_context"),
            },
        )
