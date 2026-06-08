from __future__ import annotations

import logging

from app.args.committee_evidence_enforcement import build_nrcc_no_news_abstention
from app.args.committee_packet_views import build_nrcc_view
from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.providers.yahoo.client import YahooFinanceProvider
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_NRCC
from app.workspace_args.models import InvestmentReviewPacket

logger = logging.getLogger(__name__)


class NrccCommitteePlugin:
    """News & Events Committee — fetches live news at deliberation time.

    NRCC gathers its own evidence (headlines, corporate events) via Yahoo Finance.
    It does NOT rely on a pre-populated news_snapshot in the packet — news is live
    research, not deterministic pipeline output.

    Architecture:
    - Deterministic packet = ranking, validation, factor IC (never changes in DB)
    - NRCC evidence = live Yahoo Finance news fetched fresh at committee time
    - Ephemeral overlay passes live news to ref validation without touching DB packet
    """

    committee_code = COMMITTEE_NRCC
    version = "1.0.0"

    def __init__(self, news_provider: YahooFinanceProvider | None = None) -> None:
        self.news_provider = news_provider or YahooFinanceProvider()

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        live_news = self.news_provider.fetch_news(packet.symbol)
        logger.info(
            "nrcc_news_fetch symbol=%s status=%s items=%d",
            packet.symbol,
            live_news.get("status"),
            len(live_news.get("items") or []),
        )

        view = build_nrcc_view({**packet.payload, "news_snapshot": live_news, "symbol": packet.symbol})

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
            "You have fetched live news headlines for this symbol. "
            "Use ONLY the news_snapshot items and research_context catalysts provided. "
            "NEVER cite ranking/composite score, validation IC, or technical factor lists. "
            "Return strict JSON with keys: findings, strengths, risks, supporting_evidence, confidence, "
            "research_label, contrarian_view. "
            "supporting_evidence MUST have at least 3 items, each a dict with key 'ref'. "
            "Use refs exactly like: 'news_snapshot:item:0', 'news_snapshot:item:1', 'news_snapshot:status'. "
            "contrarian_view must note when constructive quant/technical signals lack news corroboration. "
            "Do not recommend buy/sell/hold or invent headlines not present in the payload."
        )

        # Ephemeral overlay — live news available for ref validation but NOT persisted to DB packet.
        nrcc_packet = InvestmentReviewPacket(
            symbol=packet.symbol,
            stock_id=packet.stock_id,
            ranking_run_id=packet.ranking_run_id,
            ranking_result_id=packet.ranking_result_id,
            payload={**packet.payload, "news_snapshot": live_news},
            packet_hash=packet.packet_hash,
            packet_version=packet.packet_version,
        )
        return execute_committee_llm(
            packet=nrcc_packet,
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
