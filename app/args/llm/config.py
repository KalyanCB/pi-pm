from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings
from app.workspace_args.constants import (
    COMMITTEE_CRO,
    COMMITTEE_FRC,
    COMMITTEE_NRCC,
    COMMITTEE_QRC,
    COMMITTEE_RC,
    COMMITTEE_TARC,
)

ALL_COMMITTEE_LLM_CODES = (
    COMMITTEE_TARC,
    COMMITTEE_FRC,
    COMMITTEE_QRC,
    COMMITTEE_NRCC,
    COMMITTEE_RC,
    COMMITTEE_CRO,
)

_AGENT_SETTINGS_KEYS: dict[str, str] = {
    COMMITTEE_TARC: "tarc",
    COMMITTEE_FRC: "frc",
    COMMITTEE_QRC: "qrc",
    COMMITTEE_NRCC: "nrcc",
    COMMITTEE_RC: "rc",
    COMMITTEE_CRO: "cro",
}


@dataclass(frozen=True)
class AgentLlmConfig:
    agent_code: str
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None
    timeout_seconds: int = 60
    extra_headers: dict[str, str] = field(default_factory=dict)
    request_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArgsLlmSettings:
    """Resolved per-agent LLM routing from environment / Settings."""

    agents: dict[str, AgentLlmConfig]

    def for_agent(self, agent_code: str) -> AgentLlmConfig:
        return self.agents[agent_code]

    @classmethod
    def from_settings(cls, settings: Settings) -> ArgsLlmSettings:
        agents = {code: _resolve_agent_config(settings, code) for code in ALL_COMMITTEE_LLM_CODES}
        return cls(agents=agents)


def _resolve_agent_config(settings: Settings, agent_code: str) -> AgentLlmConfig:
    key = _AGENT_SETTINGS_KEYS[agent_code]
    provider = _coalesce(
        getattr(settings, f"args_llm_{key}_provider", ""),
        settings.args_llm_provider,
        default="mock",
    )
    model = _coalesce(
        getattr(settings, f"args_llm_{key}_model", ""),
        settings.args_llm_default_model,
        default="gpt-4o-mini",
    )
    api_key = _coalesce(
        getattr(settings, f"args_llm_{key}_api_key", ""),
        settings.args_llm_openai_api_key,
        settings.openai_api_key,
        default=None,
    )
    base_url = _coalesce(
        getattr(settings, f"args_llm_{key}_base_url", ""),
        settings.args_llm_openai_base_url,
        default="https://api.openai.com/v1",
    )
    agent_timeout = int(getattr(settings, f"args_llm_{key}_timeout_seconds", 0) or 0)
    timeout = agent_timeout if agent_timeout > 0 else settings.args_llm_timeout_seconds
    return AgentLlmConfig(
        agent_code=agent_code,
        provider=provider.lower(),
        model=model,
        api_key=api_key or None,
        base_url=base_url.rstrip("/") if base_url else None,
        timeout_seconds=timeout,
    )


def _coalesce(*values: str, default: str | None = None) -> str:
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return default or ""
