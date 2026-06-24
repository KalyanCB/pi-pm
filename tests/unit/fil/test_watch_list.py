"""Tests for FIL watch-list lifecycle logic (ADR-039)."""

from __future__ import annotations

from datetime import date

from app.fil.constants import (
    CatalystCategory,
    CatalystMagnitude,
    CatalystSentiment,
    NewsEventSource,
)
from app.fil.schemas import ExtractedEvent
from app.fil.watch_list import candidate_from_event, compute_expiry, is_expired


def _event(confidence: float, duration: int = 30) -> ExtractedEvent:
    return ExtractedEvent(
        source=NewsEventSource.BSE_ANNOUNCEMENT,
        event_date=date(2026, 6, 22),
        category=CatalystCategory.ORDER_WIN,
        sentiment=CatalystSentiment.POSITIVE,
        magnitude=CatalystMagnitude.HIGH,
        confidence=confidence,
        catalyst_duration_days=duration,
        summary="Large order win.",
        symbol="RVNL",
    )


def test_compute_expiry_adds_duration():
    assert compute_expiry(date(2026, 6, 22), 30) == date(2026, 7, 22)


def test_confirmed_event_becomes_candidate():
    cand = candidate_from_event(_event(0.9), added_date=date(2026, 6, 22))
    assert cand is not None
    assert cand.added_date == date(2026, 6, 22)
    assert cand.expires_date == date(2026, 7, 22)


def test_unconfirmed_event_is_not_watch_listed():
    assert candidate_from_event(_event(0.8), added_date=date(2026, 6, 22)) is None


def test_is_expired():
    assert is_expired(date(2026, 6, 21), as_of=date(2026, 6, 22)) is True
    assert is_expired(date(2026, 6, 22), as_of=date(2026, 6, 22)) is False
    assert is_expired(date(2026, 6, 23), as_of=date(2026, 6, 22)) is False
