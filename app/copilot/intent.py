"""Intent classifier + entity extractor for the Copilot.

Rule-based — no LLM needed for classification.
Refuse patterns are checked first so they cannot be bypassed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID


class CopilotIntent(StrEnum):
    """Investor explainability intents — Copilot explains, never decides."""

    WHY_RECOMMENDED = "why_recommended"
    WHY_NOT_RECOMMENDED = "why_not_recommended"
    EXPLAIN_EXIT = "explain_exit"
    EXPLAIN_CONVICTION = "explain_conviction"
    EXPLAIN_COMMITTEE = "explain_committee"
    EXPLAIN_PORTFOLIO = "explain_portfolio"
    EXPLAIN_RISK = "explain_risk"
    EXPLAIN_PERFORMANCE = "explain_performance"
    # Supplementary explainability (ranking / validation / ops)
    EXPLAIN_RANK = "explain_rank"
    EXPLAIN_VALIDATION = "explain_validation"
    OPS_STATUS = "ops_status"
    REFUSED = "refused"


@dataclass
class ExtractedEntities:
    symbol: str | None = None
    as_of_date: date | None = None
    strategy_name: str | None = None
    run_id: UUID | None = None


@dataclass
class ClassificationResult:
    intent: CopilotIntent
    entities: ExtractedEntities
    refuse_reason: str | None = None


# ── Refuse patterns (checked first — hard stops) ─────────────────────────────

_REFUSE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"\b(place|execute|send)\s+(?:a\s+)?(?:(?:buy|sell)\s+)?(?:order|trade)\b", re.I
        ),
        "Trade execution is not supported. Use the HITL approval queue.",
    ),
    (
        re.compile(r"\b(?:place|execute)\s+.*\b(?:order|trade)\b", re.I),
        "Trade execution is not supported. Use the HITL approval queue.",
    ),
    (
        re.compile(r"\bpick\s+(?:the\s+)?(?:best|top)\s+stock\b", re.I),
        "Stock picking without data is not in scope. See GET /recommendations/daily.",
    ),
    (
        re.compile(r"\b(?:tell\s+me\s+)?(?:the\s+)?best\s+stock\s+to\s+buy\b", re.I),
        "Stock picking without data is not in scope. See GET /recommendations/daily.",
    ),
    (
        re.compile(r"\boverride\s+(?:validation|ranking|conviction|risk)\b", re.I),
        "Overriding deterministic components is not permitted.",
    ),
    (
        re.compile(
            r"\bignore\s+(?:all\s+)?(?:previous\s+)?(?:instructions?|rules|guidelines|constraints)\b",
            re.I,
        ),
        "Prompt injection attempt detected. Request refused.",
    ),
    (
        re.compile(r"\b(guarantee|promise|certain(ly)?)\s+(profit|return|gain)\b", re.I),
        "Return guarantees are not in scope.",
    ),
    (
        re.compile(r"\bsize\s+(?:my\s+)?position\b", re.I),
        "Position sizing is handled by the Portfolio Engine, not the Copilot.",
    ),
    (
        re.compile(r"\b(predict|forecast)\s+(?:market|price|nifty)\b", re.I),
        "Market prediction is not in the corpus.",
    ),
]

# ── Intent patterns (most specific first) ─────────────────────────────────────

_INTENT_PATTERNS: list[tuple[re.Pattern, CopilotIntent]] = [
    # Why-not before why-recommended (shared "recommend" stem)
    (
        re.compile(r"\bwhy\b.*\bnot\s+recommended\b", re.I),
        CopilotIntent.WHY_NOT_RECOMMENDED,
    ),
    (
        re.compile(
            r"\b(?:why\s+not|why\s+was(?:n't| not)|why\s+did(?:n't| not))\s+.*\brecommend",
            re.I,
        ),
        CopilotIntent.WHY_NOT_RECOMMENDED,
    ),
    (
        re.compile(r"\bwhy\s+(?:was|is)\s+(?:\w+\s+)+recommended\b", re.I),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    (
        re.compile(r"\bwhy\s+recommend\b", re.I),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    # Exit (before generic rank/recommend patterns)
    (
        re.compile(r"\b(exit|sell|close)\b.*\b(reason|why|approved|signal)\b", re.I),
        CopilotIntent.EXPLAIN_EXIT,
    ),
    (re.compile(r"\bexit_approved\b", re.I), CopilotIntent.EXPLAIN_EXIT),
    (re.compile(r"\bwhy\b.*\b(exit|sell|selling)\b", re.I), CopilotIntent.EXPLAIN_EXIT),
    (
        re.compile(r"\brecommend(?:ed|ing|s)?\s+.*\b(sell|selling|exit)\b", re.I),
        CopilotIntent.EXPLAIN_EXIT,
    ),
    (
        re.compile(r"\b(sell|selling|exit)\b.*\brecommend", re.I),
        CopilotIntent.EXPLAIN_EXIT,
    ),
    # Conviction
    (re.compile(r"\bconviction\b", re.I), CopilotIntent.EXPLAIN_CONVICTION),
    (
        re.compile(r"\b(high|medium|low|exceptional|blocked)\s+band\b", re.I),
        CopilotIntent.EXPLAIN_CONVICTION,
    ),
    # Committee / ARGS
    (
        re.compile(r"\b(committee|args|cro|tarc|frc|qrc|nrcc|rc)\b", re.I),
        CopilotIntent.EXPLAIN_COMMITTEE,
    ),
    (
        re.compile(r"\b(supportive|cautious|high.concern)\b", re.I),
        CopilotIntent.EXPLAIN_COMMITTEE,
    ),
    # Portfolio
    (
        re.compile(r"\b(portfolio|holding|holdings|allocation|exposure|nav|position)\b", re.I),
        CopilotIntent.EXPLAIN_PORTFOLIO,
    ),
    # Risk
    (
        re.compile(r"\b(risks?|concern|drawdown|volatility|high_concern)\b", re.I),
        CopilotIntent.EXPLAIN_RISK,
    ),
    # Performance / attribution
    (
        re.compile(
            r"\b(perform(?:ance|s)?|win\s+rate|pnl|returns?|alpha|outcome|attribution)\b",
            re.I,
        ),
        CopilotIntent.EXPLAIN_PERFORMANCE,
    ),
    # Validation
    (re.compile(r"\bvalidat(ed?|ion)\b", re.I), CopilotIntent.EXPLAIN_VALIDATION),
    (re.compile(r"\b(ic|information\s+coefficient)\b", re.I), CopilotIntent.EXPLAIN_VALIDATION),
    (re.compile(r"\bforward\s+return\b", re.I), CopilotIntent.EXPLAIN_VALIDATION),
    # Ops
    (re.compile(r"\b(batch|pipeline|phase|ingest|daily\s+run)\b", re.I), CopilotIntent.OPS_STATUS),
    (
        re.compile(r"\b(yesterday|today)('?s)?\s+(batch|run|pipeline)\b", re.I),
        CopilotIntent.OPS_STATUS,
    ),
    (re.compile(r"\b(pass|fail|status)\b.*\b(batch|run)\b", re.I), CopilotIntent.OPS_STATUS),
    # Rank (broad — last among stock-specific intents)
    (
        re.compile(r"\b(rank(ed|ing)?|score|top\s*\d+|position\s+\d+)\b", re.I),
        CopilotIntent.EXPLAIN_RANK,
    ),
    (re.compile(r"\bwhy\b.*\brank\b", re.I), CopilotIntent.EXPLAIN_RANK),
]

# ── Entity extraction ─────────────────────────────────────────────────────────

_NSE_SYMBOL = re.compile(r"\b([A-Z][A-Z0-9&-]{1,15}(?:\.NS)?)\b")
_DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_STRATEGY_PATTERN = re.compile(r"\b(momentum_v1|breakout_v1)\b", re.I)

_STOP_WORDS = {
    "IS",
    "IT",
    "IN",
    "ON",
    "AT",
    "TO",
    "BE",
    "DO",
    "GO",
    "THE",
    "AND",
    "FOR",
    "WHY",
    "HOW",
    "DID",
    "TOP",
    "HAS",
    "WAS",
    "ARE",
    "CAN",
    "NSE",
    "BSE",
    "NOT",
    "ALL",
    "NOW",
    "BUY",
    "SELL",
    "MY",
    "ME",
    "QRC",
    "FRC",
    "TARC",
    "NRCC",
    "YESTERDAY",
    "TODAY",
    "WHAT",
    "SHOW",
    "PASS",
    "EXIT",
}


def _extract_entities(question: str) -> ExtractedEntities:
    entities = ExtractedEntities()

    m = _STRATEGY_PATTERN.search(question)
    if m:
        entities.strategy_name = m.group(1).lower()

    m = _DATE_PATTERN.search(question)
    if m:
        try:
            entities.as_of_date = date.fromisoformat(m.group(1))
        except ValueError:
            pass

    candidates = _NSE_SYMBOL.findall(question.upper())
    for c in candidates:
        clean = c.replace(".NS", "")
        if len(clean) >= 2 and clean not in _STOP_WORDS:
            entities.symbol = c if c.endswith(".NS") else f"{clean}.NS"
            break

    return entities


def classify(question: str) -> ClassificationResult:
    """Classify a user question into an intent with extracted entities."""

    for pattern, reason in _REFUSE_PATTERNS:
        if pattern.search(question):
            return ClassificationResult(
                intent=CopilotIntent.REFUSED,
                entities=ExtractedEntities(),
                refuse_reason=reason,
            )

    for pattern, intent in _INTENT_PATTERNS:
        if pattern.search(question):
            return ClassificationResult(
                intent=intent,
                entities=_extract_entities(question),
            )

    entities = _extract_entities(question)
    if entities.symbol:
        return ClassificationResult(intent=CopilotIntent.EXPLAIN_RANK, entities=entities)

    return ClassificationResult(intent=CopilotIntent.OPS_STATUS, entities=entities)
