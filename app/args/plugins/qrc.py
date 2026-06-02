from __future__ import annotations

from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_QRC
from app.workspace_args.models import InvestmentReviewPacket


class QrcCommitteePlugin:
    committee_code = COMMITTEE_QRC
    version = "1.0.0"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        system = (
            f"{COMMITTEE_QRC} quant research committee. "
            "Use only validation, decile, factor_ic, exit_research, and regime "
            "in packet.quant_evidence and packet.validation. "
            "Do not invent statistics or trade recommendations."
        )
        return execute_committee_llm(
            packet=packet,
            llm=llm,
            committee_code=self.committee_code,
            committee_version=self.version,
            system=system,
            user_payload={
                "symbol": packet.symbol,
                "validation": packet.payload.get("validation"),
                "quant_evidence": packet.payload.get("quant_evidence"),
                "regime": packet.payload.get("regime"),
            },
        )
