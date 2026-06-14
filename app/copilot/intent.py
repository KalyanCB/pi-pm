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
    # Data-model–level explainability
    EXPLAIN_STOCK = "explain_stock"
    EXPLAIN_MARKET_DATA = "explain_market_data"
    EXPLAIN_FACTOR_IC = "explain_factor_ic"
    EXPLAIN_RCEE = "explain_rcee"
    EXPLAIN_REGIME = "explain_regime"
    EXPLAIN_POSITIONS = "explain_positions"
    EXPLAIN_EXIT_STRATEGY = "explain_exit_strategy"
    REFUSED = "refused"


@dataclass
class ExtractedEntities:
    symbol: str | None = None
    as_of_date: date | None = None
    from_date: date | None = None
    to_date: date | None = None
    strategy_name: str | None = None
    run_id: UUID | None = None
    period_label: str | None = None   # e.g. "1Y", "6M", "3M", "2024", "2025"


@dataclass
class ClassificationResult:
    intent: CopilotIntent
    entities: ExtractedEntities
    refuse_reason: str | None = None
    # True when no specific intent pattern matched and we used the generic
    # fallback (symbol→rank, else→ops). Signals the caller to try the LLM
    # classifier for a better-routed intent.
    low_confidence: bool = False


# ── Refuse patterns (checked first — hard stops) ─────────────────────────────

_REFUSE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"\b(place|execute|send)\s+(?:a\s+)?(?:(?:buy|sell)\s+)?(?:order|trade)\b", re.I
        ),
        "Trade execution is not supported. Use the HITL approval queue.",
    ),
    (
        re.compile(r"\b(?:place|execute|send)\b.{0,30}\b(?:order|trade)\b", re.I),
        "Trade execution is not supported. Use the HITL approval queue.",
    ),
    (
        re.compile(r"\bexecute\s+a?\s*(?:buy|sell)\b", re.I),
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
        re.compile(r"\b(guarantee|promise|certain(ly)?)\s+.{0,20}\b(profit|return|gain|returns)\b", re.I),
        "Return guarantees are not in scope.",
    ),
    (
        re.compile(r"\bsize\s+(?:my\s+)?position\b", re.I),
        "Position sizing is handled by the Portfolio Engine, not the Copilot.",
    ),
    (
        re.compile(r"\b(predict|forecast)\b.{0,30}\b(market|price|stock|nifty|tomorrow|next\s+week)\b", re.I),
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
        # Allow dotted tickers (TRENT.NS) between "why is/was" and "recommended".
        re.compile(r"\bwhy\s+(?:was|is)\b[\w.\s]*\brecommended\b", re.I),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    (
        re.compile(r"\bwhy\s+recommend(?:ed)?\b", re.I),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    (
        # "current recommendation on/for X", "what is the recommendation on X"
        re.compile(r"\b(?:current\s+)?recommendation\s+(?:on|for|of|status)\b", re.I),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    (
        # "what is/are the recommendation(s)", "show recent recommendations"
        re.compile(r"\brecommendations?\b.*\b(today|recent|latest|current|now)\b", re.I),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    (
        re.compile(r"\b(recent|latest|today'?s?|current)\b.*\brecommendations?\b", re.I),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    (
        re.compile(r"\bwhat\s+(?:are|is)\s+(?:the\s+)?(?:recent\s+|latest\s+|current\s+)?recommendations?\b", re.I),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    (
        # "what is the recommendation for X"
        re.compile(r"\bwhat\s+is\s+(?:the\s+)?(?:current\s+)?recommendation\b", re.I),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    (
        # "what action did system give X", "what signal for X"
        re.compile(r"\b(?:recommendation|signal|action)\s+(?:on|for)\b", re.I),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    (
        # "why is X a BUY", "why did X get BUY/WATCH"
        re.compile(r"\bwhy\b[\w.\s']*\b(?:a\s+)?(?:buy|watch)\b", re.I),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    # Watchlist / stocks under watch (before generic positions)
    (
        re.compile(
            r"\b(watch[\s-]?list|stocks?\s+(?:under\s+|on\s+)?watch|under\s+watch|"
            r"buy[\s-]?list|currently\s+(?:on\s+)?watch)\b",
            re.I,
        ),
        CopilotIntent.WHY_RECOMMENDED,
    ),
    # Win rate / hit rate (before generic performance — avoids EXPLAIN_POSITIONS)
    (
        re.compile(r"\b(win[\s-]?rate|hit[\s-]?rate|batting\s+average|success[\s-]?rate)\b", re.I),
        CopilotIntent.EXPLAIN_PERFORMANCE,
    ),
    # Quarter-based performance (before explain_portfolio)
    (
        re.compile(r"\bQ[1-4]\b|\b(first|second|third|fourth)\s+quarter\b", re.I),
        CopilotIntent.EXPLAIN_PERFORMANCE,
    ),
    # YTD
    (
        re.compile(r"\b(ytd|year[\s-]to[\s-]date|so\s+far\s+this\s+year|this\s+year\s+so\s+far)\b", re.I),
        CopilotIntent.EXPLAIN_PERFORMANCE,
    ),
    # Month + year → monthly performance (before generic portfolio)
    (
        re.compile(
            r"\b(january|february|march|april|june|july|august|september|october|november|december)\b"
            r".*\b20\d{2}\b|\b20\d{2}\b.*"
            r"\b(january|february|march|april|june|july|august|september|october|november|december)\b",
            re.I,
        ),
        CopilotIntent.EXPLAIN_PERFORMANCE,
    ),
    # Exit STRATEGY / policy / framework (before specific exit-signal patterns)
    (
        re.compile(
            r"\b(exit|stop|trailing|time[\s-]?stop|alpha\s+decay)\b.*"
            r"\b(strateg\w*|polic\w*|framework|rule|research|study|backtest|decay)\b",
            re.I,
        ),
        CopilotIntent.EXPLAIN_EXIT_STRATEGY,
    ),
    (
        re.compile(r"\bexit\s+(?:strateg\w*|polic\w*|framework|rule|research)\b", re.I),
        CopilotIntent.EXPLAIN_EXIT_STRATEGY,
    ),
    (
        re.compile(r"\b(trailing\s+stop|time\s+stop|stop[\s-]?loss\s+polic\w*|alpha\s+decay)\b", re.I),
        CopilotIntent.EXPLAIN_EXIT_STRATEGY,
    ),
    # Exit (specific signal — before generic rank/recommend patterns)
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
    # Stock profile / setup evidence (SEE v2)
    (
        re.compile(
            r"\b(stock\s+setup|setup\s+evidence|similar\s+setups?|setup\s+score|"
            r"stock\s+(?:info|related|profile|details?|overview|summary)|"
            r"fundamentals?|company\s+profile|see[\s_]?v2|which\s+sector|what\s+sector|industry)\b",
            re.I,
        ),
        CopilotIntent.EXPLAIN_STOCK,
    ),
    # Market data / OHLCV / price
    (
        re.compile(
            r"\b(market\s+data|ohlc\w*|price\s+(?:data|history)|closing\s+price|"
            r"last\s+close|candles?|daily\s+bars?|traded\s+volume|"
            r"adj(?:usted)?\s+close|open(?:ing)?\s+price)\b",
            re.I,
        ),
        CopilotIntent.EXPLAIN_MARKET_DATA,
    ),
    # Factor IC (before validation's generic "ic")
    (
        re.compile(r"\bfactors?\b|\bfactor\s+(?:ic|performance|contribution|spread)\b", re.I),
        CopilotIntent.EXPLAIN_FACTOR_IC,
    ),
    # RCEE — Regime Coverage Edge Engine (before generic regime)
    (
        re.compile(
            r"\b(rcee|edge|regime\s+coverage|coverage\s+edge|expectancy)\b",
            re.I,
        ),
        CopilotIntent.EXPLAIN_RCEE,
    ),
    # Regime (current regime + onset)
    (
        re.compile(
            r"\b(regime|trend\s+regime|vol(?:atility)?\s+regime|market\s+regime|"
            r"bull[_\s]?(?:low|high)|bear[_\s]?(?:low|high))\b",
            re.I,
        ),
        CopilotIntent.EXPLAIN_REGIME,
    ),
    # Closed / profitable past positions → performance outcomes (before open-position patterns)
    (
        re.compile(
            r"\b(profitable|best|top)\b.*\b(positions?|trades?|holdings?|recommendation)\b",
            re.I,
        ),
        CopilotIntent.EXPLAIN_PERFORMANCE,
    ),
    (
        re.compile(r"\b(closed|past|exited|historical)\b.*\b(positions?|trades?|holdings?)\b", re.I),
        CopilotIntent.EXPLAIN_PERFORMANCE,
    ),
    # "positions closed at loss/win" or "how many closed at a loss"
    (
        re.compile(r"\bclosed?\b.*\b(loss|win|profit|gain)\b|\b(loss|win|profit)\b.*\bclosed?\b", re.I),
        CopilotIntent.EXPLAIN_PERFORMANCE,
    ),
    # Worst recommendation / outcome
    (
        re.compile(r"\b(worst|best)\b.*\b(recommendation|trade|outcome|result)\b", re.I),
        CopilotIntent.EXPLAIN_PERFORMANCE,
    ),
    # Open positions (before portfolio)
    (
        re.compile(r"\b(positions?|holdings?)\b", re.I),
        CopilotIntent.EXPLAIN_POSITIONS,
    ),
    # Portfolio performance / returns / PnL — must come BEFORE generic portfolio pattern
    (
        re.compile(
            r"\bportfolio\b.*\b(perform\w*|return\w*|pnl|profit|loss|alpha|gain|growth|"
            r"how\s+did|track\s+record|result\w*|month\w*|year\w*|week\w*|period|history|trend)\b",
            re.I,
        ),
        CopilotIntent.EXPLAIN_PERFORMANCE,
    ),
    (
        re.compile(
            r"\b(perform\w*|return\w*|pnl|alpha|gain|growth|track\s+record)\b.*\bportfolio\b",
            re.I,
        ),
        CopilotIntent.EXPLAIN_PERFORMANCE,
    ),
    # Portfolio state (NAV, positions, config, exposure)
    (
        re.compile(
            r"\b(portfolio|allocation|exposure|nav|equity|cash|deployable|"
            r"single[\s-]?name\s+cap|sector\s+cap|cap\s+pct)\b",
            re.I,
        ),
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

# Explicit ".NS"-suffixed ticker (any case) — strongest signal.
_SYMBOL_WITH_SUFFIX = re.compile(r"\b([A-Za-z][A-Za-z0-9&-]{1,15})\.NS\b", re.I)
# Bare ticker — only ALL-CAPS tokens in the ORIGINAL question, so lowercase
# words like "Explain"/"about" are never mistaken for a symbol.
_SYMBOL_UPPER = re.compile(r"\b([A-Z][A-Z0-9&-]{1,15})\b")
_DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
# Natural-language dates: "1-Jun", "10 June", "Jun 1", "June 10".
_MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
        start=1,
    )
}
_DAYMON_PATTERN = re.compile(r"\b(\d{1,2})[\s-]+([A-Za-z]{3,9})\b")  # 1-Jun / 10 June
_MONDAY_PATTERN = re.compile(r"\b([A-Za-z]{3,9})[\s-]+(\d{1,2})\b")  # Jun 1 / June 10
_YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")


def _extract_dates(question: str) -> list[date]:
    """All dates found in the question, in order of appearance (deduped).

    Accepts ISO (2026-06-01) and natural forms (1-Jun, June 10), inferring the
    year from a 4-digit year in the question, else the current year.
    """
    year_m = _YEAR_PATTERN.search(question)
    year = int(year_m.group(1)) if year_m else date.today().year
    found: list[tuple[int, date]] = []
    for m in _DATE_PATTERN.finditer(question):
        try:
            found.append((m.start(), date.fromisoformat(m.group(1))))
        except ValueError:
            pass
    for rx, day_first in ((_DAYMON_PATTERN, True), (_MONDAY_PATTERN, False)):
        for m in rx.finditer(question):
            day_s, mon_s = (m.group(1), m.group(2)) if day_first else (m.group(2), m.group(1))
            month = _MONTHS.get(mon_s[:3].lower())
            if not month:
                continue
            try:
                found.append((m.start(), date(year, month, int(day_s))))
            except ValueError:
                pass
    seen: set[date] = set()
    out: list[date] = []
    for _, dt in sorted(found, key=lambda x: x[0]):
        if dt not in seen:
            seen.add(dt)
            out.append(dt)
    return out
_STRATEGY_PATTERN = re.compile(
    r"\b(momentum_v1|breakout_v1|reversal_v1|low_vol_v1)\b", re.I
)

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
    # Data-model / domain keywords — never tickers
    "REGIME",
    "RCEE",
    "EDGE",
    "FACTOR",
    "FACTORS",
    "IC",
    "MARKET",
    "PRICE",
    "VOLUME",
    "OHLC",
    "STOCK",
    "SETUP",
    "SECTOR",
    "INDUSTRY",
    "HOLDING",
    "HOLDINGS",
    "POSITION",
    "POSITIONS",
    "PORTFOLIO",
    "STRATEGY",
    "POLICY",
    "BULL",
    "BEAR",
    "NAV",
    "CASH",
    "EQUITY",
}


def _extract_entities(question: str) -> ExtractedEntities:
    entities = ExtractedEntities()

    m = _STRATEGY_PATTERN.search(question)
    if m:
        entities.strategy_name = m.group(1).lower()

    dates = _extract_dates(question)
    if len(dates) >= 2:
        entities.from_date = dates[0]
        entities.to_date = dates[-1]
    elif len(dates) == 1:
        entities.as_of_date = dates[0]

    # 1) Explicit ".NS" suffix wins (e.g. "sbin.ns", "TRENT.NS").
    suffixed = _SYMBOL_WITH_SUFFIX.search(question)
    if suffixed:
        entities.symbol = f"{suffixed.group(1).upper()}.NS"
        return entities

    # 2) Otherwise pick the first ALL-CAPS token (a real ticker like SBIN),
    #    matched against the original case so verbs/question words are excluded.
    for c in _SYMBOL_UPPER.findall(question):
        if len(c) >= 2 and c not in _STOP_WORDS:
            entities.symbol = f"{c}.NS"
            break

    # 3) Extract period label for performance queries
    entities.period_label = _extract_period(question)

    return entities


_CALENDAR_YEAR = re.compile(r"\b(20\d{2})\b")
_ROLLING_PERIOD = re.compile(
    r"\b(?:last|past|previous|trailing)\s+"
    r"(one|two|three|six|1|2|3|6|12)\s*(year|month|week)s?\b",
    re.I,
)
_QUARTER_PATTERN = re.compile(
    r"\bQ([1-4])\b.*\b(20\d{2})\b|\b(20\d{2})\b.*\bQ([1-4])\b|"
    r"\b(first|second|third|fourth)\s+quarter\b.*\b(20\d{2})\b|\b(20\d{2})\b.*\b(first|second|third|fourth)\s+quarter\b",
    re.I,
)
_MONTH_YEAR_PATTERN = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b"
    r"[\s,]+\b(20\d{2})\b|\b(20\d{2})\b[\s,]+\b(january|february|march|april|may|june|july|august|"
    r"september|october|november|december)\b",
    re.I,
)
_MONTH_NAMES = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}
_QUARTER_ORDINALS = {"first": "1", "second": "2", "third": "3", "fourth": "4"}
_PERIOD_KEYWORDS = {
    "one year": "1Y", "1 year": "1Y", "12 month": "1Y", "12months": "1Y",
    "six month": "6M", "6 month": "6M", "half year": "6M",
    "three month": "3M", "3 month": "3M",
    "one month": "1M", "1 month": "1M",
    "two year": "2Y", "2 year": "2Y",
    "three year": "3Y", "3 year": "3Y",
    "ytd": "YTD", "year to date": "YTD", "year-to-date": "YTD",
}
_WORD_TO_NUM = {"one": "1", "two": "2", "three": "3", "six": "6", "twelve": "12"}


def _extract_period(question: str) -> str | None:
    q = question.lower()

    # YTD keywords (check before calendar year so "this year" wins)
    if any(kw in q for kw in ("ytd", "year to date", "year-to-date", "so far this year", "this year so far")):
        return "YTD"

    # Quarter: "Q1 2025", "first quarter 2024"
    m = _QUARTER_PATTERN.search(question)
    if m:
        groups = m.groups()
        yr = next((g for g in groups if g and re.match(r"20\d{2}", g)), None)
        q_num = next((g for g in groups if g and re.match(r"[1-4]", g)), None)
        if q_num is None:
            ordinal = next((g for g in groups if g and g.lower() in _QUARTER_ORDINALS), None)
            if ordinal:
                q_num = _QUARTER_ORDINALS[ordinal.lower()]
        if q_num and yr:
            return f"Q{q_num}-{yr}"

    # Month + year: "March 2025", "2024 June"
    m = _MONTH_YEAR_PATTERN.search(question)
    if m:
        groups = m.groups()
        month_str = next((g for g in groups if g and g.lower() in _MONTH_NAMES), None)
        yr_str = next((g for g in groups if g and re.match(r"20\d{2}", g)), None)
        if month_str and yr_str:
            return f"{yr_str}-{_MONTH_NAMES[month_str.lower()]}"

    # Calendar year (e.g. "in 2024", "for 2025")
    m = _CALENDAR_YEAR.search(question)
    if m:
        return m.group(1)

    # Rolling period (e.g. "last one year", "past 6 months")
    m = _ROLLING_PERIOD.search(q)
    if m:
        num_word = m.group(1).lower()
        num = _WORD_TO_NUM.get(num_word, num_word)
        unit = m.group(2).lower()
        unit_map = {"year": "Y", "month": "M", "week": "W"}
        return f"{num}{unit_map.get(unit, unit[0].upper())}"

    # Keyword scan
    for kw, label in _PERIOD_KEYWORDS.items():
        if kw in q:
            return label
    return None


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
        return ClassificationResult(
            intent=CopilotIntent.EXPLAIN_RANK, entities=entities, low_confidence=True
        )

    return ClassificationResult(
        intent=CopilotIntent.OPS_STATUS, entities=entities, low_confidence=True
    )
