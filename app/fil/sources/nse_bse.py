"""NSE/BSE corporate-announcement source (Tier-1, company-level).

The fetch transport is injected so the JSON parser can be tested with recorded
fixtures. The default transport raises until live access is configured — FIL is
not wired into the daily batch yet, so no live calls happen by default.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from app.fil.constants import NewsEventSource
from app.fil.schemas import RawNewsItem

logger = logging.getLogger(__name__)

# Transport: (as_of) -> list of raw announcement dicts (source-native shape).
Transport = Callable[[date], list[dict[str, Any]]]


def _not_configured(_as_of: date) -> list[dict[str, Any]]:
    raise RuntimeError(
        "NseBseAnnouncementSource has no live transport configured. "
        "Inject a transport callable, or use StaticNewsSource for tests/backfill."
    )


class NseBseAnnouncementSource:
    def __init__(
        self,
        *,
        source: NewsEventSource = NewsEventSource.BSE_ANNOUNCEMENT,
        transport: Transport | None = None,
    ) -> None:
        self._source = source
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
        """Normalise a source-native announcement dict to a RawNewsItem.

        Tolerant of the differing NSE/BSE field names — falls back across the
        common aliases each feed uses.
        """
        symbol = entry.get("symbol") or entry.get("scrip") or entry.get("sm_symbol")
        headline = entry.get("headline") or entry.get("subject") or entry.get("desc") or ""
        body = entry.get("body") or entry.get("attchmntText") or entry.get("more") or headline
        raw_date = entry.get("event_date") or entry.get("date") or entry.get("an_dt")
        external_id = (
            entry.get("external_id")
            or entry.get("id")
            or entry.get("seq_id")
            or entry.get("attchmntFile")
        )
        if not symbol or not headline:
            return None
        parsed_date = self._parse_date(raw_date)
        if parsed_date is None:
            return None
        return RawNewsItem(
            source=self._source,
            event_date=parsed_date,
            headline=str(headline).strip(),
            body=str(body).strip(),
            symbol=str(symbol).strip().upper(),
            external_id=str(external_id) if external_id else None,
        )

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if isinstance(value, date):
            return value
        if not value:
            return None
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(text[: len(fmt) + 4], fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            logger.warning("FIL NSE/BSE source: unparseable date %r", value)
            return None
