from __future__ import annotations

from app.args.llm.config import ALL_COMMITTEE_LLM_CODES, ArgsLlmSettings
from app.args.llm.port import LlmPort
from app.args.llm.providers.factory import build_llm_port
from app.core.config import Settings, get_settings


class CommitteeLlmRegistry:
    """Resolves a loosely-coupled LlmPort per committee / CRO agent."""

    def __init__(self, ports: dict[str, LlmPort]) -> None:
        self._ports = ports

    def get(self, agent_code: str) -> LlmPort:
        port = self._ports.get(agent_code)
        if port is None:
            raise KeyError(f"No LLM port configured for agent: {agent_code}")
        return port

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> CommitteeLlmRegistry:
        llm_settings = ArgsLlmSettings.from_settings(settings or get_settings())
        ports = {
            code: build_llm_port(llm_settings.for_agent(code)) for code in ALL_COMMITTEE_LLM_CODES
        }
        return cls(ports)
