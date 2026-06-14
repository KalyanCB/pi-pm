from __future__ import annotations

from collections.abc import Callable

from app.args.llm.config import AgentLlmConfig
from app.args.llm.port import LlmPort
from app.args.llm.providers.mock import build_mock_port
from app.args.llm.providers.openai_compatible import OpenAiCompatibleLlmPort

LlmPortBuilder = Callable[[AgentLlmConfig], LlmPort]

_PROVIDERS: dict[str, LlmPortBuilder] = {}
_DEFAULT_MOCK_SHARED: LlmPort | None = None


def register_llm_provider(name: str, builder: LlmPortBuilder) -> None:
    """Register a provider implementation (e.g. openai, anthropic, mock)."""
    _PROVIDERS[name.strip().lower()] = builder


def list_llm_providers() -> list[str]:
    return sorted(_PROVIDERS.keys())


def build_llm_port(cfg: AgentLlmConfig) -> LlmPort:
    provider = (cfg.provider or "mock").strip().lower()
    builder = _PROVIDERS.get(provider)
    if builder is None:
        known = ", ".join(list_llm_providers()) or "(none)"
        raise ValueError(
            f"Unknown LLM provider '{provider}' for agent {cfg.agent_code}. "
            f"Known providers: {known}. Register custom providers via register_llm_provider()."
        )
    return builder(cfg)


def _build_openai_port(cfg: AgentLlmConfig) -> LlmPort:
    # Copilot produces prose answers — skip JSON mode so the model writes plain text.
    text_mode = cfg.agent_code == "copilot"
    return OpenAiCompatibleLlmPort(
        api_key=cfg.api_key or "",
        model=cfg.model,
        base_url=cfg.base_url or "https://api.openai.com/v1",
        timeout_seconds=cfg.timeout_seconds,
        extra_headers=cfg.extra_headers,
        request_overrides=cfg.request_overrides,
        text_mode=text_mode,
    )


def _build_mock_port(cfg: AgentLlmConfig) -> LlmPort:
    global _DEFAULT_MOCK_SHARED
    from app.args.llm.port import MockLlmPort

    if _DEFAULT_MOCK_SHARED is None:
        _DEFAULT_MOCK_SHARED = MockLlmPort()
    return build_mock_port(cfg, shared=_DEFAULT_MOCK_SHARED)


def _register_builtins() -> None:
    if _PROVIDERS:
        return
    register_llm_provider("mock", _build_mock_port)
    register_llm_provider("openai", _build_openai_port)
    register_llm_provider("openai_compatible", _build_openai_port)


_register_builtins()
