from __future__ import annotations

from app.args.llm.config import AgentLlmConfig
from app.args.llm.port import LlmCompletion, LlmPort, MockLlmPort


class NamedMockLlmPort:
    """Mock port tagged with agent code for observability."""

    def __init__(self, agent_code: str, inner: LlmPort | None = None) -> None:
        self._agent_code = agent_code
        self._inner = inner or MockLlmPort()

    def complete(self, *, system: str, user: str, model: str | None = None) -> LlmCompletion:
        completion = self._inner.complete(system=system, user=user, model=model)
        return LlmCompletion(
            content=completion.content,
            model=f"mock-{self._agent_code.lower()}",
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
        )


def build_mock_port(cfg: AgentLlmConfig, *, shared: LlmPort | None = None) -> LlmPort:
    return NamedMockLlmPort(cfg.agent_code, shared or MockLlmPort())
