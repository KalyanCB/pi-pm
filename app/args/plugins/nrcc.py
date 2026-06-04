from __future__ import annotations

from app.args.committee_evidence_enforcement import build_nrcc_no_news_abstention
from app.args.committee_packet_views import build_nrcc_view
from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_NRCC
from app.workspace_args.models import InvestmentReviewPacket


class NrccCommitteePlugin:
    committee_code = COMMITTEE_NRCC
    version = "1.0.0"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        view = build_nrcc_view({**packet.payload, "symbol": packet.symbol})
        if view.get("news_evidence_status") == "no_news_evidence":
            return CommitteeResult(
                output=build_nrcc_no_news_abstention(
                    committee_code=self.committee_code,
                    committee_version=self.version,
                    symbol=packet.symbol,
                ),
                model="nrcc-abstention",
            )

        system = (
            f"{COMMITTEE_NRCC} news and catalyst committee. "
            "Use ONLY news_snapshot and research_context catalysts in the scoped payload. "
            "NEVER cite ranking/composite score, validation IC, or technical factor lists. "
            "Return strict JSON with keys: findings, strengths, risks, supporting_evidence, confidence, "
            "research_label, contrarian_view. "
            "contrarian_view must note when constructive quant/technical signals lack news corroboration. "
            "supporting_evidence refs: news_snapshot:*, research_context:* only. "
            "Do not recommend buy/sell/hold or invent headlines not present in the packet."
        )
        return execute_committee_llm(
            packet=packet,
            llm=llm,
            committee_code=self.committee_code,
            committee_version=self.version,
            system=system,
            user_payload=view,
            strict_numeric_findings=False,
            abstention_builder=lambda: build_nrcc_no_news_abstention(
                committee_code=self.committee_code,
                committee_version=self.version,
                symbol=packet.symbol,
            ),
        )
