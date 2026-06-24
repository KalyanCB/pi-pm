"""Watch-list lifecycle logic (ADR-039) — pure functions, no DB.

The service layer maps these decisions onto ``fil_watch_list`` rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.fil.schemas import ExtractedEvent


@dataclass(frozen=True)
class WatchListCandidate:
    """A confirmed event that should produce a watch-list entry."""

    event: ExtractedEvent
    added_date: date
    expires_date: date


def compute_expiry(added_date: date, catalyst_duration_days: int) -> date:
    return added_date + timedelta(days=catalyst_duration_days)


def candidate_from_event(event: ExtractedEvent, *, added_date: date) -> WatchListCandidate | None:
    """Return a watch-list candidate for a confirmed event, else None.

    Only confirmed (confidence >= floor) events enter the watch list. UNCONFIRMED
    events are stored in company_news_events for analysis but never watch-listed.
    """
    if not event.is_confirmed:
        return None
    return WatchListCandidate(
        event=event,
        added_date=added_date,
        expires_date=compute_expiry(added_date, event.catalyst_duration_days),
    )


def is_expired(expires_date: date, *, as_of: date) -> bool:
    return expires_date < as_of
