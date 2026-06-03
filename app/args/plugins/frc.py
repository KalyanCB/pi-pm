from __future__ import annotations

from app.args.committee_evidence_enforcement import build_frc_abstention
from app.args.committee_packet_views import build_frc_view
from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_FRC
from app.workspace_args.models import InvestmentReviewPacket


class FrcCommitteePlugin:
    committee_code = COMMITTEE_FRC
    version = "1.0.0"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        view = build_frc_view({**packet.payload, "symbol": packet.symbol})
        if view.get("fundamental_evidence_status") == "insufficient":
            return CommitteeResult(
                output=build_frc_abstention(
                    committee_code=self.committee_code,
                    committee_version=self.version,
                    symbol=packet.symbol,
                ),
                model="frc-abstention",
            )

        system = (
            f"{COMMITTEE_FRC} fundamental research committee. "
            "Use ONLY fundamental_snapshot in the scoped payload. "
            "NEVER cite ranking, regime, validation IC, technical factors, or news. "
            "Return strict JSON with keys: findings, strengths, risks, supporting_evidence, confidence, "
            "research_label, contrarian_view. "
            "contrarian_view must note when technical/quant optimism lacks fundamental confirmation. "
            "supporting_evidence refs: fundamental:* or fundamental_snapshot:* only. "
            "Do not recommend buy/sell/hold, assign position sizes, or stop losses."
        )
        return execute_committee_llm(
            packet=packet,
            llm=llm,
            committee_code=self.committee_code,
            committee_version=self.version,
            system=system,
            user_payload=view,
            abstention_builder=lambda: build_frc_abstention(
                committee_code=self.committee_code,
                committee_version=self.version,
                symbol=packet.symbol,
            ),
        )
