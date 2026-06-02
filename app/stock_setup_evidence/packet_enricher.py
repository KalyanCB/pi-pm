from __future__ import annotations

from uuid import UUID

from app.services.stock_setup_research_service import StockSetupResearchService


def attach_stock_setup_evidence(
    payload: dict,
    *,
    see_service: StockSetupResearchService | None,
    ranking_run_id: UUID,
    stock_id: UUID,
) -> dict:
    """Add stock-level setup evidence to packet payload (no ARGS agent changes)."""
    if see_service is None:
        payload["stock_setup_evidence"] = {"status": "unavailable"}
        return payload
    evidence = see_service.get_packet_evidence(
        ranking_run_id=ranking_run_id, stock_id=stock_id
    )
    payload["stock_setup_evidence"] = evidence
    return payload
