from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.args.agents.cro_agent import aggregate_committee_reviews
from app.args.graph.state import ArgsGraphState
from app.args.llm.registry import CommitteeLlmRegistry
from app.args.plugins.base import CommitteePlugin
from app.args.plugins.registry import CommitteeRegistry
from app.workspace_args.constants import (
    COMMITTEE_CRO,
    CommitteeAdvisoryAction,
    aggregate_cro_advisory,
    label_to_advisory_action,
)
from app.workspace_args.committee_contracts import CommitteeReviewOutput
from app.workspace_args.models import InvestmentReviewPacket

logger = logging.getLogger(__name__)

_MAX_PLUGIN_RETRIES = 2


class ArgsResearchWorkflow:
    """LangGraph workflow: packets → parallel committees → CRO → outputs."""

    def __init__(
        self,
        registry: CommitteeRegistry,
        llm_registry: CommitteeLlmRegistry,
        *,
        max_workers: int = 5,
    ) -> None:
        self.registry = registry
        self.llm_registry = llm_registry
        self.max_workers = max_workers
        self._graph = self._build()

    def _build(self):
        graph = StateGraph(ArgsGraphState)
        graph.add_node("parallel_committees", self._parallel_committees)
        graph.add_node("cro_aggregate", self._cro_aggregate)
        graph.set_entry_point("parallel_committees")
        graph.add_edge("parallel_committees", "cro_aggregate")
        graph.add_edge("cro_aggregate", END)
        return graph.compile()

    def run_committees_and_cro(
        self,
        packets: list[InvestmentReviewPacket],
        committee_codes: list[str],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        initial: ArgsGraphState = {
            "packets": [_packet_dict(p) for p in packets],
            "committee_codes": committee_codes,
            "reviews": [],
            "cro_outputs": [],
            "errors": [],
            "phase": "parallel_committees",
            "token_usage_total": 0,
        }
        final = self._graph.invoke(initial)
        return (
            final.get("reviews") or [],
            final.get("cro_outputs") or [],
            int(final.get("token_usage_total") or 0),
        )

    def _parallel_committees(self, state: ArgsGraphState) -> ArgsGraphState:
        plugins = self.registry.resolve(state.get("committee_codes"))
        reviews: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = list(state.get("errors") or [])
        tokens = int(state.get("token_usage_total") or 0)

        tasks: list[tuple[InvestmentReviewPacket, CommitteePlugin]] = []
        for packet_data in state.get("packets") or []:
            packet = _packet_from_dict(packet_data)
            for plugin in plugins:
                tasks.append((packet, plugin))

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._run_plugin_with_retry, packet, plugin): (packet, plugin)
                for packet, plugin in tasks
            }
            for future in as_completed(futures):
                packet, plugin = futures[future]
                try:
                    result = future.result()
                    tokens += result.input_tokens + result.output_tokens
                    reviews.append(
                        {
                            "symbol": packet.symbol,
                            "stock_id": str(packet.stock_id),
                            "ranking_result_id": str(packet.ranking_result_id),
                            "packet_hash": packet.packet_hash,
                            "committee_code": result.output.committee_code,
                            "output": _review_output_dict(result.output),
                            "model": result.model,
                            "input_tokens": result.input_tokens,
                            "output_tokens": result.output_tokens,
                        }
                    )
                except Exception as exc:
                    logger.warning(
                        "committee_plugin_failed",
                        extra={
                            "committee": plugin.committee_code,
                            "symbol": packet.symbol,
                            "error": str(exc),
                        },
                    )
                    errors.append(
                        {
                            "committee_code": plugin.committee_code,
                            "symbol": packet.symbol,
                            "message": str(exc),
                            "phase": "parallel_committees",
                        }
                    )

        return {
            **state,
            "reviews": reviews,
            "errors": errors,
            "token_usage_total": tokens,
            "phase": "cro_aggregate",
        }

    def _run_plugin_with_retry(self, packet: InvestmentReviewPacket, plugin: CommitteePlugin):
        last_error: Exception | None = None
        for attempt in range(_MAX_PLUGIN_RETRIES + 1):
            try:
                llm = self.llm_registry.get(plugin.committee_code)
                return plugin.execute(packet, llm)
            except Exception as exc:
                last_error = exc
                if attempt >= _MAX_PLUGIN_RETRIES:
                    raise
        raise last_error or RuntimeError("plugin execution failed")

    def _cro_aggregate(self, state: ArgsGraphState) -> ArgsGraphState:
        reviews = state.get("reviews") or []
        by_symbol: dict[str, list[CommitteeReviewOutput]] = {}
        for row in reviews:
            output = _review_output_from_dict(row["output"])
            by_symbol.setdefault(row["symbol"], []).append(output)

        cro_outputs: list[dict[str, Any]] = []
        tokens = int(state.get("token_usage_total") or 0)
        for symbol, committee_outputs in by_symbol.items():
            cro_result = aggregate_committee_reviews(
                symbol,
                committee_outputs,
                self.llm_registry.get(COMMITTEE_CRO),
            )
            cro = cro_result.output
            tokens += cro_result.input_tokens + cro_result.output_tokens
            # M3.1 HIGH_CONCERN escalation (ADR-023, PO Mandatory Modification #1)
            # HIGH_CONCERN overrides majority — risk is not democratic.
            committee_actions: dict[str, CommitteeAdvisoryAction] = {
                r["output"]["committee_code"]: CommitteeAdvisoryAction(
                    r["output"].get("advisory_action", CommitteeAdvisoryAction.WATCH)
                )
                for r in reviews
                if r["symbol"] == symbol and r.get("output", {}).get("advisory_action")
            }
            cro_advisory_action = aggregate_cro_advisory(committee_actions)

            # Identify HIGH_CONCERN originating committees for CRO narrative
            high_concern_committees = [
                code for code, action in committee_actions.items()
                if action == CommitteeAdvisoryAction.HIGH_CONCERN
            ]

            cro_outputs.append(
                {
                    "symbol": symbol,
                    "stock_id": next(r["stock_id"] for r in reviews if r["symbol"] == symbol),
                    "model": cro_result.model,
                    "input_tokens": cro_result.input_tokens,
                    "output_tokens": cro_result.output_tokens,
                    # M3.1 advisory fields
                    "cro_advisory_action": cro_advisory_action.value,
                    "high_concern_committees": high_concern_committees,
                    "aggregation": {
                        "aggregation_snapshot": cro.aggregation_snapshot,
                        "rationale": cro.rationale,
                        "dissent_summary": cro.dissent_summary,
                        "confidence": cro.confidence,
                        "summary": cro.summary,
                        "structured": cro.structured,
                        "evidence_refs": cro.evidence_refs,
                    },
                }
            )
        return {
            **state,
            "cro_outputs": cro_outputs,
            "token_usage_total": tokens,
            "phase": "completed",
        }


def _packet_dict(packet: InvestmentReviewPacket) -> dict[str, Any]:
    return {
        "symbol": packet.symbol,
        "stock_id": str(packet.stock_id),
        "ranking_run_id": str(packet.ranking_run_id),
        "ranking_result_id": str(packet.ranking_result_id),
        "packet_hash": packet.packet_hash,
        "payload": packet.payload,
        "packet_version": packet.packet_version,
    }


def _packet_from_dict(data: dict[str, Any]) -> InvestmentReviewPacket:
    return InvestmentReviewPacket(
        symbol=data["symbol"],
        stock_id=UUID(str(data["stock_id"])),
        ranking_run_id=UUID(str(data["ranking_run_id"])),
        ranking_result_id=UUID(str(data["ranking_result_id"])),
        payload=data["payload"],
        packet_hash=data["packet_hash"],
        packet_version=data.get("packet_version", "1.0.0"),
    )


def _review_output_dict(output: CommitteeReviewOutput) -> dict[str, Any]:
    advisory_action = label_to_advisory_action(output.research_label)
    return {
        "committee_code": output.committee_code,
        "committee_version": output.committee_version,
        "findings": output.findings,
        "strengths": output.strengths,
        "risks": output.risks,
        "supporting_evidence": output.supporting_evidence,
        "confidence": output.confidence,
        "extensions": output.extensions,
        "research_label": output.research_label,
        # M3.1 Investment Committee — advisory fields
        "advisory_action": advisory_action.value,
        "high_concern": advisory_action == CommitteeAdvisoryAction.HIGH_CONCERN,
        "high_concern_reason": None,  # populated by plugin if HIGH_CONCERN
    }


def _review_output_from_dict(data: dict[str, Any]) -> CommitteeReviewOutput:
    return CommitteeReviewOutput(
        committee_code=data["committee_code"],
        committee_version=data["committee_version"],
        findings=data["findings"],
        strengths=list(data.get("strengths") or []),
        risks=list(data.get("risks") or []),
        supporting_evidence=list(data.get("supporting_evidence") or []),
        confidence=float(data.get("confidence", 0.5)),
        extensions=dict(data.get("extensions") or {}),
        research_label=str(data.get("research_label", "neutral")),
    )
