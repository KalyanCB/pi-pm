"""Tests for FIL sector intelligence logic (ADR-039 Phase 3)."""

from __future__ import annotations

import uuid
from datetime import date

from app.fil.constants import (
    SECTOR_PROPAGATION_HAIRCUT,
    CatalystCategory,
    CatalystMagnitude,
    CatalystSentiment,
    NewsEventSource,
)
from app.fil.schemas import ExtractedEvent, SectorSignal
from app.fil.sector import (
    build_signal_sets,
    detect_rotation,
    propagate_to_sector,
)


def _sector_event(sentiment: CatalystSentiment, sector="Railways") -> ExtractedEvent:
    return ExtractedEvent(
        source=NewsEventSource.PIB_PRESS,
        event_date=date(2026, 6, 22),
        category=CatalystCategory.SECTOR_TAILWIND,
        sentiment=sentiment,
        magnitude=CatalystMagnitude.HIGH,
        confidence=0.92,
        catalyst_duration_days=60,
        summary="Railway capex hike.",
        sector=sector,
    )


def test_propagation_applies_haircut():
    sig = propagate_to_sector(_sector_event(CatalystSentiment.POSITIVE))
    assert sig is not None
    assert sig.propagated_confidence == round(0.92 * SECTOR_PROPAGATION_HAIRCUT, 3)
    assert sig.base_confidence == 0.92


def test_propagation_none_without_sector():
    ev = _sector_event(CatalystSentiment.POSITIVE)
    ev = ExtractedEvent(**{**ev.__dict__, "sector": None})
    assert propagate_to_sector(ev) is None


def test_build_signal_sets_splits_by_sentiment():
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    members = {"Railways": [a, b], "Pharma": [c]}
    signals = [
        SectorSignal("Railways", CatalystCategory.SECTOR_TAILWIND, CatalystSentiment.POSITIVE,
                     CatalystMagnitude.HIGH, 0.9, 0.63, date(2026, 6, 22)),
        SectorSignal("Pharma", CatalystCategory.SECTOR_HEADWIND, CatalystSentiment.NEGATIVE,
                     CatalystMagnitude.HIGH, 0.9, 0.63, date(2026, 6, 22)),
    ]
    sets = build_signal_sets(signals, members)
    assert sets.tailwind_stock_ids == frozenset({a, b})
    assert sets.headwind_stock_ids == frozenset({c})


def test_detect_rotation_flags_sector_above_threshold():
    ids = [uuid.uuid4() for _ in range(5)]
    stock_sector = {
        ids[0]: "Railways",
        ids[1]: "Railways",
        ids[2]: "Railways",
        ids[3]: "Pharma",
        ids[4]: "IT Services",
    }
    alerts = detect_rotation(ids, stock_sector, tailwind_sectors={"Railways"})
    assert len(alerts) == 1
    assert alerts[0].sector == "Railways"
    assert alerts[0].stock_count == 3
    assert alerts[0].has_active_tailwind is True


def test_detect_rotation_below_threshold_no_alert():
    ids = [uuid.uuid4() for _ in range(2)]
    stock_sector = {ids[0]: "Railways", ids[1]: "Railways"}
    assert detect_rotation(ids, stock_sector, tailwind_sectors=set()) == []


def test_detect_rotation_without_tailwind_flag_false():
    ids = [uuid.uuid4() for _ in range(3)]
    stock_sector = {i: "Metals" for i in ids}
    alerts = detect_rotation(ids, stock_sector, tailwind_sectors=set())
    assert len(alerts) == 1
    assert alerts[0].has_active_tailwind is False
