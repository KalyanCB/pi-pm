import pytest

from app.args.llm.config import ArgsLlmSettings
from app.args.llm.port import LlmPort
from app.args.llm.providers.factory import build_llm_port, register_llm_provider
from app.args.llm.registry import CommitteeLlmRegistry
from app.core.config import Settings
from app.workspace_args.constants import COMMITTEE_CRO, COMMITTEE_QRC, COMMITTEE_TARC


def test_per_agent_model_override():
    settings = Settings(
        args_llm_provider="mock",
        args_llm_default_model="gpt-4o-mini",
        args_llm_tarc_model="gpt-4o",
        args_llm_qrc_model="claude-3-5-sonnet",
    )
    llm_settings = ArgsLlmSettings.from_settings(settings)
    assert llm_settings.for_agent(COMMITTEE_TARC).model == "gpt-4o"
    assert llm_settings.for_agent(COMMITTEE_QRC).model == "claude-3-5-sonnet"


def test_per_agent_api_key_and_base_url_override():
    settings = Settings(
        args_llm_provider="openai",
        args_llm_openai_api_key="global-key",
        args_llm_openai_base_url="https://global.example/v1",
        args_llm_tarc_api_key="tarc-key",
        args_llm_tarc_base_url="https://tarc.example/v1",
        args_llm_qrc_api_key="qrc-key",
    )
    llm_settings = ArgsLlmSettings.from_settings(settings)
    tarc = llm_settings.for_agent(COMMITTEE_TARC)
    qrc = llm_settings.for_agent(COMMITTEE_QRC)
    cro = llm_settings.for_agent(COMMITTEE_CRO)
    assert tarc.api_key == "tarc-key"
    assert tarc.base_url == "https://tarc.example/v1"
    assert qrc.api_key == "qrc-key"
    assert qrc.base_url == "https://global.example/v1"
    assert cro.api_key == "global-key"


def test_per_agent_provider_override():
    settings = Settings(
        args_llm_provider="mock",
        args_llm_cro_provider="openai",
        args_llm_cro_api_key="cro-key",
        args_llm_cro_model="gpt-4o",
    )
    llm_settings = ArgsLlmSettings.from_settings(settings)
    assert llm_settings.for_agent(COMMITTEE_TARC).provider == "mock"
    assert llm_settings.for_agent(COMMITTEE_CRO).provider == "openai"


def test_registry_exposes_distinct_mock_ports():
    registry = CommitteeLlmRegistry.from_settings(Settings(args_llm_provider="mock"))
    tarc = registry.get(COMMITTEE_TARC)
    qrc = registry.get(COMMITTEE_QRC)
    completion_tarc = tarc.complete(system="TARC test", user="{}")
    completion_qrc = qrc.complete(system="QRC quant", user="{}")
    assert completion_tarc.model == "mock-tarc"
    assert completion_qrc.model == "mock-qrc"


def test_custom_provider_registration():
    class EchoPort:
        def complete(self, *, system: str, user: str, model: str | None = None):
            from app.args.llm.port import LlmCompletion

            return LlmCompletion(content='{"findings":"ok"}', model="echo")

    register_llm_provider("echo", lambda _cfg: EchoPort())
    cfg = ArgsLlmSettings.from_settings(
        Settings(args_llm_provider="echo", args_llm_tarc_provider="echo")
    ).for_agent(COMMITTEE_TARC)
    port = build_llm_port(cfg)
    assert port.complete(system="TARC", user="{}").model == "echo"


def test_unknown_provider_raises():
    cfg = ArgsLlmSettings.from_settings(
        Settings(args_llm_provider="not-a-real-provider")
    ).for_agent(COMMITTEE_TARC)
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        build_llm_port(cfg)
