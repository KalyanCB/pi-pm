"""AI extraction of structured catalysts from raw news/filings (ADR-039).

Uses the existing ``LlmPort`` abstraction (``app.args.llm``) so the same
provider/credentials/audit path is reused. Per the build decision the
``openai_compatible`` provider is the runtime backend; tests use ``MockLlmPort``.

The extractor is intentionally DB-free: it turns a ``RawNewsItem`` into an
``ExtractedEvent`` (or ``None`` when the item is junk / below the discard floor).
Persistence and watch-list effects happen in ``FundamentalIntelligenceService``.
"""

from __future__ import annotations

import json
import logging

from app.args.llm.port import LlmPort
from app.fil.constants import (
    UNCONFIRMED_CONFIDENCE_FLOOR,
    CatalystCategory,
    CatalystMagnitude,
    CatalystSentiment,
    default_duration_days,
)
from app.fil.schemas import ExtractedEvent, RawNewsItem

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a financial filing analyst for an Indian-equities trading system.
Extract ONE structured catalyst from the company announcement below. Respond with a
single JSON object and nothing else.

Schema:
{
  "category": one of [EARNINGS_BEAT, EARNINGS_MISS, ORDER_WIN, REGULATORY_APPROVAL,
    REGULATORY_RISK, PROMOTER_BUYING, PROMOTER_SELLING, DEBT_REDUCTION, DEBT_CONCERN,
    CAPEX_ANNOUNCEMENT, SECTOR_TAILWIND, SECTOR_HEADWIND, ANALYST_UPGRADE,
    ANALYST_DOWNGRADE, MANAGEMENT_CHANGE, MERGER_ACQUISITION],
  "sentiment": one of [POSITIVE, NEGATIVE, NEUTRAL, CONTEXT],
  "magnitude": one of [HIGH, MEDIUM, LOW],
  "confidence": float 0.0-1.0,
  "catalyst_duration_days": integer (omit or 0 to use the category default),
  "summary": one-sentence factual summary,
  "flags": optional array of short tags (e.g. ["ORDER_BOOK_HIGH","MARGIN_EXPANSION"])
}

Rules:
- magnitude HIGH only for material events (PAT beat >15%, order >Rs.500 Cr, USFDA
  approval, promoter buy >1%). Be conservative.
- If the text is routine/administrative with no trading catalyst, set confidence < 0.5.
- Never invent numbers not present in the text.
"""


class CatalystExtractor:
    def __init__(self, llm: LlmPort, *, model: str | None = None) -> None:
        self._llm = llm
        self._model = model

    def extract(self, item: RawNewsItem) -> ExtractedEvent | None:
        """Return a structured event, or None to discard (junk / below floor)."""
        user = self._build_user_prompt(item)
        try:
            completion = self._llm.complete(system=SYSTEM_PROMPT, user=user, model=self._model)
        except Exception:  # network/provider failure — skip this item, don't crash batch
            logger.exception("FIL extraction LLM call failed for %s", item.external_id)
            return None

        parsed = self._parse(completion.content)
        if parsed is None:
            return None

        confidence = parsed["confidence"]
        if confidence < UNCONFIRMED_CONFIDENCE_FLOOR:
            return None  # discarded per ADR confidence policy

        category = parsed["category"]
        duration = parsed["catalyst_duration_days"] or default_duration_days(category)

        return ExtractedEvent(
            source=item.source,
            event_date=item.event_date,
            category=category,
            sentiment=parsed["sentiment"],
            magnitude=parsed["magnitude"],
            confidence=confidence,
            catalyst_duration_days=duration,
            summary=parsed["summary"],
            raw_excerpt=item.body[:2000] if item.body else None,
            flags=parsed["flags"],
            symbol=item.symbol,
            sector=item.sector,
        )

    @staticmethod
    def _build_user_prompt(item: RawNewsItem) -> str:
        lines = [
            f"Date: {item.event_date.isoformat()}",
            f"Source: {item.source.value}",
        ]
        if item.symbol:
            lines.append(f"Symbol: {item.symbol}")
        if item.sector:
            lines.append(f"Sector: {item.sector}")
        lines.append(f"Headline: {item.headline}")
        lines.append(f"Body: {item.body}")
        return "\n".join(lines)

    @staticmethod
    def _parse(content: str) -> dict | None:
        try:
            raw = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            logger.warning("FIL extraction returned non-JSON content")
            return None
        try:
            category = CatalystCategory(str(raw["category"]).strip().upper())
            sentiment = CatalystSentiment(str(raw["sentiment"]).strip().upper())
            magnitude = CatalystMagnitude(str(raw["magnitude"]).strip().upper())
            confidence = float(raw["confidence"])
            summary = str(raw["summary"]).strip()
        except (KeyError, ValueError, TypeError):
            logger.warning("FIL extraction JSON missing/invalid required fields: %s", content[:200])
            return None

        duration_raw = raw.get("catalyst_duration_days") or 0
        try:
            duration = int(duration_raw)
        except (ValueError, TypeError):
            duration = 0

        flags = raw.get("flags") or []
        if not isinstance(flags, list):
            flags = []

        return {
            "category": category,
            "sentiment": sentiment,
            "magnitude": magnitude,
            "confidence": max(0.0, min(1.0, confidence)),
            "summary": summary,
            "catalyst_duration_days": duration,
            "flags": [str(f) for f in flags],
        }
