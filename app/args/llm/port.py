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
                '{"findings":"The security ranks at the top of the candidate set with a high composite score, and the technical profile is positive but not uniformly strong. Momentum and trend-oriented factors are doing most of the lifting, while at least one confirmation factor remains materially weaker, which increases concentration risk. Breadth is therefore moderate rather than broad, because several factors are above useful thresholds yet the distribution is not even across all technical dimensions. Regime context is available, so the signal can be interpreted in the current state rather than in isolation, but regime support should still be treated as conditional until repeated performance confirms stability. Historical performance adds supporting context but does not remove the need to watch for momentum decay. The most important takeaway is that this is a high-quality but partially concentrated setup: upside conviction is supported by strong leaders, while risk management should focus on whether weaker confirmation factors improve or continue to lag over subsequent observations.",'
                '"strengths":["High rank placement","Momentum factor support","Regime context available"],'
                '"risks":["Signal concentration","Volatility sensitivity","Limited horizon history"],'
                '"supporting_evidence":[{"ref":"ranking:rank"},{"ref":"ranking:composite_score"},{"ref":"technical_factors:momentum"}],'
                '"confidence":0.85,"research_label":"supportive",'
                '"contrarian_view":"QRC may cite weak regime IC — rank overstates edge if validation fails."}'
            )
        if "QRC" in system or "quant" in system.lower():
            return (
                '{"findings":"Validation quality is usable but uneven across horizons. Short-horizon metrics exist and show directional efficacy, yet longer-horizon coverage is incomplete, which lowers robustness for horizon transfer. Decile behavior indicates separation at the top of the distribution, although the spread profile should be interpreted with caution when sample depth is limited in specific windows. Rank-correlation evidence is positive enough to justify continued monitoring, but not strong enough to assume persistent predictive power without additional confirmatory runs. Exit-research summaries provide useful policy comparisons and help identify where mean return and hit-rate tradeoffs are strongest, but policy reliability still depends on sample density and regime stability. Regime reliability is therefore moderate rather than high when supporting history is thin or inconsistent. Overall, the quant view supports conditional confidence: the signal is not unsupported, but confidence should be discounted for missing coverage, mixed sample quality across horizons, and sensitivity to regime persistence in subsequent validation cycles.",'
                '"strengths":["Validation status completed","Short-horizon metric present","Regime context included"],'
                '"risks":["Sparse longer-horizon data","Potential sample instability","Dependence on one regime"],'
                '"supporting_evidence":[{"ref":"validation:status"},{"ref":"validation:horizon:5"},{"ref":"quant_evidence:factor_ic"}],'
                '"confidence":0.82,"research_label":"supportive",'
                '"contrarian_view":"TARC rank enthusiasm overstates edge given mixed validation coverage."}'
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
                '{"findings":"Fundamental snapshot reviewed for profitability and balance sheet quality.",'
                '"strengths":["roe_stable","margin_trend_positive","leverage_moderate"],'
                '"risks":["valuation_stretch","earnings_volatility","sector_headwind"],'
                '"supporting_evidence":[{"ref":"fundamental_snapshot:roe"},{"ref":"fundamental:margin"},{"ref":"fundamental_snapshot:pe"}],'
                '"confidence":0.55,"research_label":"neutral",'
                '"contrarian_view":"Technical rank strength is unconfirmed without deeper fundamental evidence."}'
            )
        if "NRCC" in system or "news" in system.lower():
            return (
                '{"findings":"News feed items reviewed for catalyst and sector context.",'
                '"strengths":["headline_present","sector_macro_noted","deterministic_packet_scope"],'
                '"risks":["headline_uncertainty","event_timing_risk","macro_volatility"],'
                '"supporting_evidence":[{"ref":"news_snapshot:status"},{"ref":"news_snapshot:items"},{"ref":"research_context:notes"}],'
                '"confidence":0.5,"research_label":"neutral",'
                '"contrarian_view":"Constructive quant signals lack corroborating news catalyst confirmation."}'
            )
        if "RC" in system or "risk research" in system.lower():
            return (
                '{"findings":"Risk profile reviewed from drawdown, liquidity, and concentration context.",'
                '"strengths":["liquidity_adequate","drawdown_bounded","concentration_monitored"],'
                '"risks":["volatility","tail_event_risk","regime_shift_risk"],'
                '"supporting_evidence":[{"ref":"risk:concentration"},{"ref":"market_snapshot:sector"},{"ref":"portfolio_context:existing_position"}],'
                '"confidence":0.7,"research_label":"neutral",'
                '"contrarian_view":"High technical rank ignores elevated drawdown and liquidity risk stack."}'
            )
        return (
            '{"findings":"Committee review complete.",'
            '"strengths":["packet_available","schema_valid","baseline_context_present"],'
            '"risks":["data_gap","limited_depth","requires_rerun"],'
            '"supporting_evidence":[{"ref":"ranking:rank"},{"ref":"ranking:composite_score"},{"ref":"regime:regime_label"}],'
            '"confidence":0.5,"research_label":"neutral",'
            '"contrarian_view":"Peer committee conclusions should be treated skeptically until mandate-scoped evidence confirms them."}'
        )
