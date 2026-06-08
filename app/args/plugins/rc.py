from __future__ import annotations

from app.args.committee_evidence_enforcement import (
    build_evidence_validation_failed_output,
    build_rc_insufficient_abstention,
)
from app.args.committee_packet_views import build_rc_view
from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_RC
from app.workspace_args.models import InvestmentReviewPacket


class RcCommitteePlugin:
    committee_code = COMMITTEE_RC
    version = "1.0.0"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        view = build_rc_view({**packet.payload, "symbol": packet.symbol})
        if view.get("risk_evidence_status") == "insufficient":
            return CommitteeResult(
                output=build_rc_insufficient_abstention(
                    committee_code=self.committee_code,
                    committee_version=self.version,
                    symbol=packet.symbol,
                ),
                model="rc-abstention",
            )

        system = (
            f"{COMMITTEE_RC} risk research committee. "
            "Assess risk using ONLY the provided view keys: risk_drawdown, market_snapshot, "
            "concentration_context, regime_risk. "
            "NEVER promote bullish TARC-style factor strengths; articulate veto paths and reasons not to own. "
            "Return strict JSON with keys: findings, strengths, risks, supporting_evidence, confidence, "
            "research_label, contrarian_view. "
            "contrarian_view must challenge high technical rank when risk stack is elevated. "
            "supporting_evidence refs MUST start with exactly one of: "
            "risk_drawdown:, market_snapshot:, concentration_context:, regime_risk:, "
            "risk:, stock_setup_evidence:, portfolio_context:, regime:. "
            "Do NOT use ranking:, quant_evidence:, validation:, technical_factors:, or any other prefix. "
            "Never output position_size, stop_loss, buy/sell/hold, or sizing recommendations."
        )
        return execute_committee_llm(
            packet=packet,
            llm=llm,
            committee_code=self.committee_code,
            committee_version=self.version,
            system=system,
            user_payload=view,
            abstention_builder=lambda: (
                build_rc_insufficient_abstention(
                    committee_code=self.committee_code,
                    committee_version=self.version,
                    symbol=packet.symbol,
                )
                if view.get("risk_evidence_status") == "insufficient"
                else build_evidence_validation_failed_output(
                    committee_code=self.committee_code,
                    committee_version=self.version,
                    symbol=packet.symbol,
                    reason="LLM or evidence scope validation failed",
                )
            ),
        )
