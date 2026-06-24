"""Sector-level RSS sources (ADR-039 Phase 3): PIB / RBI / DGFT / ministries.

Like the company source, the transport is injected. Items carry ``sector`` (and no
``symbol``); the mapping of a feed to its sector is supplied at construction so the
same parser serves every ministry feed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from app.fil.constants import NewsEventSource
from app.fil.schemas import RawNewsItem

logger = logging.getLogger(__name__)

# Transport: (as_of) -> list of raw RSS entry dicts.
Transport = Callable[[date], list[dict[str, Any]]]


def _not_configured(_as_of: date) -> list[dict[str, Any]]:
    raise RuntimeError(
        "SectorRssSource has no live transport configured. "
        "Inject a transport callable, or use StaticNewsSource for tests/backfill."
    )


class SectorRssSource:
    def __init__(
        self,
        *,
        source: NewsEventSource,
        sector: str,
        transport: Transport | None = None,
    ) -> None:
        self._source = source
        self._sector = sector
        self._transport = transport or _not_configured

    def fetch(self, as_of: date) -> list[RawNewsItem]:
        raw = self._transport(as_of)
        items: list[RawNewsItem] = []
        for entry in raw:
            item = self._to_item(entry)
            if item is not None:
                items.append(item)
        return items

    def _to_item(self, entry: dict[str, Any]) -> RawNewsItem | None:
        headline = entry.get("title") or entry.get("headline") or ""
        body = entry.get("summary") or entry.get("description") or entry.get("body") or headline
        raw_date = entry.get("published") or entry.get("pubDate") or entry.get("date")
        external_id = entry.get("guid") or entry.get("link") or entry.get("id")
        if not headline:
            return None
        parsed_date = self._parse_date(raw_date) or as_of_fallback(entry)
        if parsed_date is None:
            return None
        return RawNewsItem(
            source=self._source,
            event_date=parsed_date,
            headline=str(headline).strip(),
            body=str(body).strip(),
            sector=self._sector,
            external_id=str(external_id) if external_id else None,
        )

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if isinstance(value, date):
            return value
        if not value:
            return None
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            logger.warning("FIL sector source: unparseable date %r", value)
            return None


def as_of_fallback(_entry: dict[str, Any]) -> date | None:
    """No usable date on an RSS entry → skip it (don't guess)."""
    return None
