from __future__ import annotations

import logging

from app.args.committee_evidence_enforcement import build_frc_abstention
from app.args.committee_packet_views import build_frc_view
from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.providers.yahoo.client import YahooFinanceProvider
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_FRC
from app.workspace_args.models import InvestmentReviewPacket

logger = logging.getLogger(__name__)


class FrcCommitteePlugin:
    """Fundamentals & Risk Committee — fetches live fundamentals at deliberation time.

    FRC gathers its own evidence (profitability, valuation, balance sheet, growth).
    It does NOT rely on fundamental_snapshot in the packet — fundamentals are live
    research, not deterministic pipeline output.

    Architecture:
    - Deterministic packet = ranking, validation, factor IC (never changes in DB)
    - FRC evidence = live Yahoo Finance .info metrics fetched at committee time
    - Ephemeral overlay passes live data to ref validation without touching DB packet
    """

    committee_code = COMMITTEE_FRC
    version = "1.0.0"

    def __init__(self, fundamentals_provider: YahooFinanceProvider | None = None) -> None:
        self.fundamentals_provider = fundamentals_provider or YahooFinanceProvider()

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        live_fundamentals = self.fundamentals_provider.fetch_fundamentals(packet.symbol)
        logger.info(
            "frc_fundamentals_fetch symbol=%s status=%s",
            packet.symbol,
            live_fundamentals.get("status"),
        )

        view = build_frc_view({
            **packet.payload,
            "fundamental_snapshot": live_fundamentals,
            "symbol": packet.symbol,
        })

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
            "You have fetched live fundamental metrics for this symbol. "
            "Use ONLY fundamental_snapshot in the scoped payload. "
            "NEVER cite ranking, regime, validation IC, technical factors, or news. "
            "Return strict JSON with keys: findings, strengths, risks, supporting_evidence, confidence, "
            "research_label, contrarian_view. "
            "supporting_evidence MUST have at least 3 items, each a dict with key 'ref'. "
            "Use refs like: 'fundamental_snapshot:profitability', 'fundamental_snapshot:valuation', "
            "'fundamental_snapshot:balance_sheet', 'fundamental_snapshot:growth', 'fundamental_snapshot:status'. "
            "contrarian_view must note when technical/quant optimism lacks fundamental confirmation. "
            "Do not recommend buy/sell/hold, assign position sizes, or stop losses."
        )

        # Ephemeral overlay — live fundamentals for ref validation but NOT persisted to DB packet.
        frc_packet = InvestmentReviewPacket(
            symbol=packet.symbol,
            stock_id=packet.stock_id,
            ranking_run_id=packet.ranking_run_id,
            ranking_result_id=packet.ranking_result_id,
            payload={**packet.payload, "fundamental_snapshot": live_fundamentals},
            packet_hash=packet.packet_hash,
            packet_version=packet.packet_version,
        )
        return execute_committee_llm(
            packet=frc_packet,
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
