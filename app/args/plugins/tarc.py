from __future__ import annotations

from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_TARC
from app.workspace_args.models import InvestmentReviewPacket


class TarcCommitteePlugin:
    committee_code = COMMITTEE_TARC
    version = "1.0.0"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        system = (
            f"{COMMITTEE_TARC} technical research committee. "
            "Interpret only ranking factors, score components, regime, and technical_factors. "
            "Do not recommend buy/sell/hold or position sizes."
        )
        return execute_committee_llm(
            packet=packet,
            llm=llm,
            committee_code=self.committee_code,
            committee_version=self.version,
            system=system,
            user_payload={
                "symbol": packet.symbol,
                "ranking": packet.payload.get("ranking"),
                "technical_factors": packet.payload.get("technical_factors"),
                "regime": packet.payload.get("regime"),
            },
        )
