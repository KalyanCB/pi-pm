from __future__ import annotations

from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_RC
from app.workspace_args.models import InvestmentReviewPacket


class RcCommitteePlugin:
    committee_code = COMMITTEE_RC
    version = "1.0.0"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        system = (
            f"{COMMITTEE_RC} risk research committee. "
            "Assess risk using ranking, validation, historical_performance, regime, "
            "and portfolio_context only. "
            "Never output position_size, stop_loss, buy/sell/hold, or sizing recommendations."
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
                "validation": packet.payload.get("validation"),
                "historical_performance": packet.payload.get("historical_performance"),
                "regime": packet.payload.get("regime"),
                "portfolio_context": packet.payload.get("portfolio_context"),
            },
        )
