from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LlmCompletion:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class LlmPort(Protocol):
    def complete(self, *, system: str, user: str, model: str | None = None) -> LlmCompletion: ...


class MockLlmPort:
    """Deterministic mock for tests — returns structured JSON snippets."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self._responses = responses or {}

    def complete(self, *, system: str, user: str, model: str | None = None) -> LlmCompletion:
        key = system[:32]
        content = self._responses.get(key) or self._default_response(system, user)
        return LlmCompletion(
            content=content,
            model=model or "mock-llm",
            input_tokens=len(user) // 4,
            output_tokens=len(content) // 4,
        )

    def _default_response(self, system: str, user: str) -> str:
        if "TARC" in system or "technical" in system.lower():
            return (
                '{"findings":"Technical factors align with ranking.",'
                '"strengths":["momentum","volume"],"risks":["volatility"],'
                '"supporting_evidence":[{"ref":"ranking:rank"}],'
                '"confidence":0.85,"research_label":"supportive"}'
            )
        if "QRC" in system or "quant" in system.lower():
            return (
                '{"findings":"Validation block present for review.",'
                '"strengths":["validation_status"],"risks":["sample_size"],'
                '"supporting_evidence":[{"ref":"validation:status"}],'
                '"confidence":0.82,"research_label":"supportive"}'
            )
        if "CRO" in system:
            return (
                '{"rationale":"Committees largely agree on evidence quality.",'
                '"dissent_summary":{"disagreements":[]},'
                '"confidence":0.8,"summary":"Research synthesis complete.",'
                '"structured":{"consensus":["TARC","QRC"]}}'
            )
        if "FRC" in system or "fundamental" in system.lower():
            return (
                '{"findings":"Sector context reviewed from market snapshot.",'
                '"strengths":["sector_identified"],'
                '"risks":["limited_fundamental_data"],'
                '"supporting_evidence":[{"ref":"market_snapshot:sector"}],'
                '"confidence":0.55,"research_label":"neutral"}'
            )
        if "NRCC" in system or "news" in system.lower():
            return (
                '{"findings":"No material catalysts in packet news feed.",'
                '"strengths":[],"risks":["headline_uncertainty"],'
                '"supporting_evidence":[{"ref":"news_snapshot:status"}],'
                '"confidence":0.5,"research_label":"neutral"}'
            )
        if "RC" in system or "risk research" in system.lower():
            return (
                '{"findings":"Risk profile reviewed from validation and history.",'
                '"strengths":["rank_visibility"],'
                '"risks":["volatility"],'
                '"supporting_evidence":[{"ref":"ranking:rank"}],'
                '"confidence":0.7,"research_label":"neutral"}'
            )
        return (
            '{"findings":"Committee review complete.",'
            '"strengths":[],"risks":["data_gap"],'
            '"supporting_evidence":[],"confidence":0.5,"research_label":"neutral"}'
        )
