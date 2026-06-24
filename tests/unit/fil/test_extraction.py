"""Tests for the FIL AI extraction layer (ADR-039)."""

from __future__ import annotations

import json
from datetime import date

from app.args.llm.port import LlmCompletion
from app.fil.constants import (
    CatalystCategory,
    CatalystMagnitude,
    CatalystSentiment,
    NewsEventSource,
    default_duration_days,
)
from app.fil.extraction import CatalystExtractor
from app.fil.schemas import RawNewsItem


class _StubLlm:
    """Returns a fixed completion regardless of prompt."""

    def __init__(self, content: str) -> None:
        self._content = content

    def complete(self, *, system: str, user: str, model=None) -> LlmCompletion:
        return LlmCompletion(content=self._content, model=model or "stub", input_tokens=1, output_tokens=1)


class _BoomLlm:
    def complete(self, *, system: str, user: str, model=None) -> LlmCompletion:
        raise RuntimeError("provider down")


def _item(**kw) -> RawNewsItem:
    defaults = dict(
        source=NewsEventSource.BSE_ANNOUNCEMENT,
        event_date=date(2026, 6, 22),
        headline="Q3 results",
        body="PAT up 18% YoY, order book at 5-year high.",
        symbol="RVNL",
    )
    defaults.update(kw)
    return RawNewsItem(**defaults)


def _payload(**kw) -> str:
    base = {
        "category": "EARNINGS_BEAT",
        "sentiment": "POSITIVE",
        "magnitude": "HIGH",
        "confidence": 0.91,
        "catalyst_duration_days": 0,
        "summary": "Q3 PAT beat estimates by 18%.",
        "flags": ["ORDER_BOOK_HIGH"],
    }
    base.update(kw)
    return json.dumps(base)


def test_extracts_confirmed_event_with_default_duration():
    extractor = CatalystExtractor(_StubLlm(_payload()))
    event = extractor.extract(_item())
    assert event is not None
    assert event.category == CatalystCategory.EARNINGS_BEAT
    assert event.sentiment == CatalystSentiment.POSITIVE
    assert event.magnitude == CatalystMagnitude.HIGH
    assert event.confidence == 0.91
    # duration 0 in payload → category default
    assert event.catalyst_duration_days == default_duration_days(CatalystCategory.EARNINGS_BEAT)
    assert event.is_confirmed is True
    assert event.is_conviction_eligible is True
    assert event.flags == ["ORDER_BOOK_HIGH"]
    assert event.symbol == "RVNL"


def test_explicit_duration_overrides_default():
    extractor = CatalystExtractor(_StubLlm(_payload(catalyst_duration_days=12)))
    event = extractor.extract(_item())
    assert event is not None
    assert event.catalyst_duration_days == 12


def test_unconfirmed_band_is_kept_but_not_conviction_eligible():
    extractor = CatalystExtractor(_StubLlm(_payload(confidence=0.78)))
    event = extractor.extract(_item())
    assert event is not None
    assert event.is_confirmed is False
    assert event.is_conviction_eligible is False


def test_below_discard_floor_returns_none():
    extractor = CatalystExtractor(_StubLlm(_payload(confidence=0.4)))
    assert extractor.extract(_item()) is None


def test_low_magnitude_not_conviction_eligible_even_if_confirmed():
    extractor = CatalystExtractor(_StubLlm(_payload(magnitude="LOW", confidence=0.9)))
    event = extractor.extract(_item())
    assert event is not None
    assert event.is_confirmed is True
    assert event.is_conviction_eligible is False


def test_unparseable_json_returns_none():
    extractor = CatalystExtractor(_StubLlm("not json at all"))
    assert extractor.extract(_item()) is None


def test_unknown_category_returns_none():
    extractor = CatalystExtractor(_StubLlm(_payload(category="ROCKET_SHIP")))
    assert extractor.extract(_item()) is None


def test_llm_failure_is_swallowed():
    extractor = CatalystExtractor(_BoomLlm())
    assert extractor.extract(_item()) is None


def test_confidence_is_clamped():
    extractor = CatalystExtractor(_StubLlm(_payload(confidence=1.5)))
    event = extractor.extract(_item())
    assert event is not None
    assert event.confidence == 1.0
