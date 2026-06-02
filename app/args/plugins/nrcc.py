from __future__ import annotations

from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.workspace_args.committee_contracts import CommitteeResult, CommitteeReviewOutput
from app.workspace_args.constants import COMMITTEE_NRCC
from app.workspace_args.models import InvestmentReviewPacket


class NrccCommitteePlugin:
    committee_code = COMMITTEE_NRCC
    version = "1.0.0"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        news = packet.payload.get("news_snapshot") or {}
        items = news.get("items") or []
        if not items:
            output = CommitteeReviewOutput(
                committee_code=self.committee_code,
                committee_version=self.version,
                findings="News/catalyst feed unavailable; NRCC review degraded.",
                strengths=[],
                risks=["news_feed_unavailable"],
                supporting_evidence=[{"ref": "news_snapshot:status"}],
                confidence=0.25,
                extensions={"degraded": True},
                research_label="neutral",
            )
            return CommitteeResult(output=output, model="nrcc-degraded")

        system = (
            f"{COMMITTEE_NRCC} news and catalyst committee. "
            "Use only news_snapshot and regime context. "
            "Do not recommend buy/sell/hold or invent headlines not present in the packet."
        )
        return execute_committee_llm(
            packet=packet,
            llm=llm,
            committee_code=self.committee_code,
            committee_version=self.version,
            system=system,
            user_payload={
                "symbol": packet.symbol,
                "news_snapshot": news,
                "regime": packet.payload.get("regime"),
            },
            strict_numeric_findings=False,
        )
