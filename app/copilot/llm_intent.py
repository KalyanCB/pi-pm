"""LLM-assisted intent classification — fallback for the rule-based router.

Used only when the deterministic regex classifier is low-confidence (no specific
pattern matched). The refusal regex always runs first and is never delegated to
the LLM, so prompt-injection refusals cannot be bypassed here.
"""

from __future__ import annotations

from app.args.llm.port import LlmPort
from app.copilot.intent import CopilotIntent

# Short, disambiguating description per intent (drives the classify prompt).
_INTENT_DESCRIPTIONS: dict[CopilotIntent, str] = {
    CopilotIntent.WHY_RECOMMENDED: "why a stock got a BUY/WATCH recommendation; its action/reason codes",
    CopilotIntent.WHY_NOT_RECOMMENDED: "why a stock was NOT recommended / rejected",
    CopilotIntent.EXPLAIN_EXIT: "a specific EXIT_APPROVED sell signal on a position",
    CopilotIntent.EXPLAIN_EXIT_STRATEGY: "exit-policy research/backtests (trailing/time stop, alpha decay)",
    CopilotIntent.EXPLAIN_CONVICTION: "conviction score/band and its sub-scores",
    CopilotIntent.EXPLAIN_COMMITTEE: "AI investment committee findings / CRO advisory",
    CopilotIntent.EXPLAIN_STOCK: "a stock's profile: name, sector, industry, exchange, active flag, setup evidence",
    CopilotIntent.EXPLAIN_MARKET_DATA: "OHLCV market/price data for a stock (open/high/low/close/volume/adj close)",
    CopilotIntent.EXPLAIN_FACTOR_IC: "factor information-coefficient (IC) metrics",
    CopilotIntent.EXPLAIN_RCEE: "Regime Coverage Edge Engine: per-regime IC/expectancy/hit-rate edge",
    CopilotIntent.EXPLAIN_REGIME: "current market regime (trend/vol) and since when",
    CopilotIntent.EXPLAIN_POSITIONS: "the open portfolio positions / holdings (qty, weight, P&L)",
    CopilotIntent.EXPLAIN_PORTFOLIO: "portfolio config & NAV: equity, cash, caps, deployable capital",
    CopilotIntent.EXPLAIN_RISK: "risk signals: reason codes, high-concern, exit triggers",
    CopilotIntent.EXPLAIN_PERFORMANCE: "realized performance: pnl, alpha, win rate, attribution",
    CopilotIntent.EXPLAIN_RANK: "a stock's deterministic rank and score components",
    CopilotIntent.EXPLAIN_VALIDATION: "forward-return validation status and IC metrics",
    CopilotIntent.OPS_STATUS: "daily batch / pipeline run status",
}

# Longer intent codes first so substring matching prefers the most specific one
# (e.g. 'explain_exit_strategy' before 'explain_exit').
_ORDERED = sorted(_INTENT_DESCRIPTIONS, key=lambda i: len(i.value), reverse=True)

_SYSTEM = (
    "You are an intent classifier for a quantitative trading platform's copilot. "
    "Map the user's question to exactly ONE intent code from the list. "
    "Reply with ONLY the intent code (e.g. explain_portfolio), nothing else.\n\n"
    "Intents:\n"
    + "\n".join(f"- {i.value}: {desc}" for i, desc in _INTENT_DESCRIPTIONS.items())
)


def llm_classify(question: str, llm: LlmPort) -> CopilotIntent | None:
    """Return the LLM-chosen intent, or None if it can't be resolved."""
    try:
        completion = llm.complete(system=_SYSTEM, user=f"Question: {question}")
    except Exception:
        return None
    text = (completion.content or "").strip().lower()
    if not text:
        return None
    for intent in _ORDERED:
        if intent.value in text:
            return intent
    return None
