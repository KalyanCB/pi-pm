"""Plain dataclasses passed between FIL stages (fetch → extract → persist).

These are transport objects, deliberately decoupled from the SQLAlchemy ORM models
in ``app.models.fil`` so the extraction/logic layers stay DB-free and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.fil.constants import (
    CatalystCategory,
    CatalystMagnitude,
    CatalystSentiment,
    NewsEventSource,
)


@dataclass(frozen=True)
class RawNewsItem:
    """A raw item pulled from a source feed, before AI extraction.

    ``symbol`` is the exchange ticker (resolved to stock_id later). Sector-level
    items carry ``symbol=None`` and set ``sector`` instead.
    """

    source: NewsEventSource
    event_date: date
    headline: str
    body: str
    symbol: str | None = None
    sector: str | None = None
    external_id: str | None = None  # source-native id, for dedup


@dataclass(frozen=True)
class ExtractedEvent:
    """Structured signal produced by the AI extractor for one raw item."""

    source: NewsEventSource
    event_date: date
    category: CatalystCategory
    sentiment: CatalystSentiment
    magnitude: CatalystMagnitude
    confidence: float
    catalyst_duration_days: int
    summary: str
    raw_excerpt: str | None = None
    flags: list[str] = field(default_factory=list)
    symbol: str | None = None
    sector: str | None = None

    @property
    def is_confirmed(self) -> bool:
        from app.fil.constants import WATCH_LIST_CONFIDENCE_FLOOR

        return self.confidence >= WATCH_LIST_CONFIDENCE_FLOOR

    @property
    def is_conviction_eligible(self) -> bool:
        from app.fil.constants import CONVICTION_ELIGIBLE_MAGNITUDES

        return self.is_confirmed and self.magnitude in CONVICTION_ELIGIBLE_MAGNITUDES


@dataclass(frozen=True)
class SectorSignal:
    """A sector-level catalyst after fan-out to member stocks."""

    sector: str
    category: CatalystCategory
    sentiment: CatalystSentiment
    magnitude: CatalystMagnitude
    base_confidence: float
    propagated_confidence: float
    event_date: date
