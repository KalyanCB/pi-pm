"""Integration tests for FundamentalIntelligenceService against sqlite (ADR-039)."""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy.orm import Session

from app.args.llm.port import LlmCompletion
from app.db.repositories.fil_watch_list_repository import FilWatchListRepository
from app.db.repositories.news_event_repository import CompanyNewsEventRepository
from app.db.repositories.sector_news_event_repository import SectorNewsEventRepository
from app.db.repositories.stock_repository import StockRepository
from app.fil.constants import NewsEventSource
from app.fil.extraction import CatalystExtractor
from app.fil.schemas import RawNewsItem
from app.fil.service import FundamentalIntelligenceService
from app.fil.sources.base import StaticNewsSource
from app.models.fil import CompanyNewsEvent, FilWatchListEntry, SectorNewsEvent
from app.models.stock import Stock


class _MapLlm:
    """Returns a payload chosen by a token found in the user prompt."""

    def __init__(self, by_symbol: dict[str, dict]) -> None:
        self._by_symbol = by_symbol

    def complete(self, *, system: str, user: str, model=None) -> LlmCompletion:
        for token, payload in self._by_symbol.items():
            if token in user:
                return LlmCompletion(
                    content=json.dumps(payload), model="map", input_tokens=1, output_tokens=1
                )
        return LlmCompletion(content="{}", model="map", input_tokens=1, output_tokens=1)


def _seed_stocks(db: Session) -> None:
    db.add(Stock(symbol="RVNL", name="Rail Vikas", exchange="NSE"))
    db.add(Stock(symbol="IRFC", name="Indian Railway Finance", exchange="NSE"))
    db.flush()


def _build_service(db: Session, llm, company_sources=None, sector_sources=None):
    return FundamentalIntelligenceService(
        stock_repo=StockRepository(db),
        news_event_repo=CompanyNewsEventRepository(db),
        watch_list_repo=FilWatchListRepository(db),
        sector_news_repo=SectorNewsEventRepository(db),
        extractor=CatalystExtractor(llm),
        company_sources=company_sources or [],
        sector_sources=sector_sources or [],
    )


def test_confirmed_company_event_writes_event_and_watch_entry(db_session: Session):
    _seed_stocks(db_session)
    items = [
        RawNewsItem(
            source=NewsEventSource.BSE_ANNOUNCEMENT,
            event_date=date(2026, 6, 22),
            headline="RVNL bags order",
            body="RVNL wins Rs.900 Cr railway order.",
            symbol="RVNL",
            external_id="bse-1",
        )
    ]
    llm = _MapLlm(
        {
            "RVNL": {
                "category": "ORDER_WIN",
                "sentiment": "POSITIVE",
                "magnitude": "HIGH",
                "confidence": 0.9,
                "summary": "Rs.900 Cr order win.",
            }
        }
    )
    svc = _build_service(db_session, llm, company_sources=[StaticNewsSource(items)])

    result = svc.run(date(2026, 6, 22))

    assert result.company_events_written == 1
    assert result.watch_list_added == 1
    assert db_session.query(CompanyNewsEvent).count() == 1
    entry = db_session.query(FilWatchListEntry).one()
    assert entry.catalyst_type == "ORDER_WIN"
    assert entry.is_active is True
    assert entry.expires_date > entry.added_date


def test_unconfirmed_event_written_but_not_watch_listed(db_session: Session):
    _seed_stocks(db_session)
    items = [
        RawNewsItem(
            source=NewsEventSource.BSE_ANNOUNCEMENT,
            event_date=date(2026, 6, 22),
            headline="RVNL note",
            body="Minor update.",
            symbol="RVNL",
            external_id="bse-2",
        )
    ]
    llm = _MapLlm(
        {
            "RVNL": {
                "category": "ANALYST_UPGRADE",
                "sentiment": "POSITIVE",
                "magnitude": "MEDIUM",
                "confidence": 0.78,
                "summary": "Soft upgrade.",
            }
        }
    )
    svc = _build_service(db_session, llm, company_sources=[StaticNewsSource(items)])

    result = svc.run(date(2026, 6, 22))

    assert result.company_events_written == 1
    assert result.watch_list_added == 0
    assert db_session.query(CompanyNewsEvent).one().is_confirmed is False
    assert db_session.query(FilWatchListEntry).count() == 0


def test_non_universe_symbol_skipped(db_session: Session):
    _seed_stocks(db_session)
    items = [
        RawNewsItem(
            source=NewsEventSource.BSE_ANNOUNCEMENT,
            event_date=date(2026, 6, 22),
            headline="Unknown co",
            body="Something",
            symbol="NOTINUNIVERSE",
            external_id="bse-3",
        )
    ]
    svc = _build_service(db_session, _MapLlm({}), company_sources=[StaticNewsSource(items)])
    result = svc.run(date(2026, 6, 22))
    assert result.skipped_non_universe == 1
    assert result.company_events_written == 0


def test_duplicate_external_id_skipped_on_second_run(db_session: Session):
    _seed_stocks(db_session)
    items = [
        RawNewsItem(
            source=NewsEventSource.BSE_ANNOUNCEMENT,
            event_date=date(2026, 6, 22),
            headline="RVNL order",
            body="Order win.",
            symbol="RVNL",
            external_id="bse-dup",
        )
    ]
    llm = _MapLlm(
        {
            "RVNL": {
                "category": "ORDER_WIN",
                "sentiment": "POSITIVE",
                "magnitude": "HIGH",
                "confidence": 0.9,
                "summary": "Order.",
            }
        }
    )
    svc = _build_service(db_session, llm, company_sources=[StaticNewsSource(items)])
    svc.run(date(2026, 6, 22))
    second = svc.run(date(2026, 6, 23))
    assert second.skipped_duplicate == 1
    assert db_session.query(CompanyNewsEvent).count() == 1


def test_expiry_deactivates_stale_watch_entries(db_session: Session):
    _seed_stocks(db_session)
    items = [
        RawNewsItem(
            source=NewsEventSource.BSE_ANNOUNCEMENT,
            event_date=date(2026, 6, 22),
            headline="Analyst upgrade RVNL",
            body="Upgrade.",
            symbol="RVNL",
            external_id="bse-exp",
        )
    ]
    llm = _MapLlm(
        {
            "RVNL": {
                "category": "ANALYST_UPGRADE",  # short default duration (7d)
                "sentiment": "POSITIVE",
                "magnitude": "HIGH",
                "confidence": 0.9,
                "summary": "Upgrade with target raise.",
                "catalyst_duration_days": 5,
            }
        }
    )
    svc = _build_service(db_session, llm, company_sources=[StaticNewsSource(items)])
    svc.run(date(2026, 6, 22))  # expires 2026-06-27
    entry = db_session.query(FilWatchListEntry).one()
    assert entry.is_active is True

    later = _build_service(db_session, _MapLlm({}), company_sources=[])
    result = later.run(date(2026, 7, 1))
    assert result.watch_list_expired == 1
    db_session.refresh(entry)
    assert entry.is_active is False
    assert entry.deactivation_reason == "EXPIRED"


def test_sector_source_writes_sector_event(db_session: Session):
    _seed_stocks(db_session)
    items = [
        RawNewsItem(
            source=NewsEventSource.PIB_PRESS,
            event_date=date(2026, 6, 22),
            headline="Railway capex hike",
            body="Government raises railway capex.",
            sector="Railways",
            external_id="pib-1",
        )
    ]
    llm = _MapLlm(
        {
            "Railways": {
                "category": "SECTOR_TAILWIND",
                "sentiment": "POSITIVE",
                "magnitude": "HIGH",
                "confidence": 0.9,
                "summary": "Railway capex hike.",
            }
        }
    )
    svc = _build_service(db_session, llm, sector_sources=[StaticNewsSource(items)])
    result = svc.run(date(2026, 6, 22))
    assert result.sector_events_written == 1
    assert db_session.query(SectorNewsEvent).one().sector == "Railways"


def test_failing_source_does_not_abort_run(db_session: Session):
    _seed_stocks(db_session)

    class _BoomSource:
        def fetch(self, as_of):
            raise RuntimeError("feed down")

    svc = _build_service(db_session, _MapLlm({}), company_sources=[_BoomSource()])
    result = svc.run(date(2026, 6, 22))
    assert result.errors
    assert result.company_events_written == 0
