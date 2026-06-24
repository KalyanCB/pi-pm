"""Sector intelligence logic (ADR-039 Phase 3) — pure functions, no DB.

Covers:
  * fan-out of a sector catalyst to member stocks at a confidence haircut
  * building tailwind / headwind stock-id sets for the (future) engine gate
  * sector-rotation detection for the daily-batch awareness signal
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from app.fil.constants import (
    SECTOR_PROPAGATION_HAIRCUT,
    SECTOR_ROTATION_MIN_STOCKS,
    CatalystSentiment,
)
from app.fil.schemas import ExtractedEvent, SectorSignal


def propagate_to_sector(event: ExtractedEvent) -> SectorSignal | None:
    """Convert a sector-level extracted event into a propagated signal.

    The propagated confidence is haircut (× 0.70) because a sector-wide catalyst is
    less precise for any single stock than a company-specific event.
    """
    if event.sector is None:
        return None
    return SectorSignal(
        sector=event.sector,
        category=event.category,
        sentiment=event.sentiment,
        magnitude=event.magnitude,
        base_confidence=event.confidence,
        propagated_confidence=round(event.confidence * SECTOR_PROPAGATION_HAIRCUT, 3),
        event_date=event.event_date,
    )


@dataclass(frozen=True)
class SectorSignalSets:
    """Stock-id sets the engine will consume at integration time."""

    tailwind_stock_ids: frozenset[UUID]
    headwind_stock_ids: frozenset[UUID]


def build_signal_sets(
    signals: list[SectorSignal],
    sector_members: dict[str, list[UUID]],
) -> SectorSignalSets:
    """Fan active sector signals out to member stock-ids by sentiment.

    ``sector_members`` maps sector name → member stock_ids (from
    sector_classifications). A stock in both a tailwind and headwind sector ends up
    in both sets; the engine's combined-signal matrix resolves precedence later.
    """
    tailwind: set[UUID] = set()
    headwind: set[UUID] = set()
    for sig in signals:
        members = sector_members.get(sig.sector, [])
        if sig.sentiment == CatalystSentiment.POSITIVE:
            tailwind.update(members)
        elif sig.sentiment == CatalystSentiment.NEGATIVE:
            headwind.update(members)
    return SectorSignalSets(
        tailwind_stock_ids=frozenset(tailwind),
        headwind_stock_ids=frozenset(headwind),
    )


@dataclass(frozen=True)
class SectorRotationAlert:
    sector: str
    stock_count: int
    has_active_tailwind: bool


def detect_rotation(
    top_pool_stock_ids: list[UUID],
    stock_sector: dict[UUID, str],
    tailwind_sectors: set[str],
    *,
    min_stocks: int = SECTOR_ROTATION_MIN_STOCKS,
) -> list[SectorRotationAlert]:
    """Flag sectors with >= ``min_stocks`` names in the top pool.

    ``top_pool_stock_ids`` is the union of top-N candidates across strategies.
    An alert is informational (portfolio awareness), not a trade signal. The
    ``has_active_tailwind`` flag marks rotations confirmed by a sector catalyst.
    """
    counts: Counter[str] = Counter()
    for sid in top_pool_stock_ids:
        sector = stock_sector.get(sid)
        if sector is not None:
            counts[sector] += 1

    alerts: list[SectorRotationAlert] = []
    for sector, count in counts.items():
        if count >= min_stocks:
            alerts.append(
                SectorRotationAlert(
                    sector=sector,
                    stock_count=count,
                    has_active_tailwind=sector in tailwind_sectors,
                )
            )
    alerts.sort(key=lambda a: a.stock_count, reverse=True)
    return alerts
