"""Source protocol + a static (fixture/backfill) source.

Live HTTP is deliberately decoupled from parsing: concrete sources take a
``fetch`` callable that returns the raw payload, so every parser is unit-testable
with recorded fixtures and live access can be gated behind the daily-batch phase
flag at integration time.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from app.fil.schemas import RawNewsItem


class NewsSource(Protocol):
    """Pulls raw, un-extracted news items for a given trading date."""

    def fetch(self, as_of: date) -> list[RawNewsItem]: ...


class StaticNewsSource:
    """A fixed list of items — used for tests and historical backfill (Option B)."""

    def __init__(self, items: list[RawNewsItem]) -> None:
        self._items = list(items)

    def fetch(self, as_of: date) -> list[RawNewsItem]:
        return [i for i in self._items if i.event_date <= as_of]
