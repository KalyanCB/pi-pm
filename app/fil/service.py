"""FundamentalIntelligenceService — orchestrates the daily FIL pipeline (ADR-039).

    fetch raw items → resolve to universe → dedup → AI extract → persist →
    update watch list → expire stale entries

Standalone: nothing here is called by the daily batch or recommendation engine yet.
Dependencies are injected so the whole pipeline is unit-testable without a network
or a live LLM (use StaticNewsSource + MockLlmPort).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from app.db.repositories.fil_watch_list_repository import FilWatchListRepository
from app.db.repositories.news_event_repository import CompanyNewsEventRepository
from app.db.repositories.sector_news_event_repository import SectorNewsEventRepository
from app.db.repositories.stock_repository import StockRepository
from app.fil.constants import WatchListDeactivationReason
from app.fil.extraction import CatalystExtractor
from app.fil.schemas import RawNewsItem
from app.fil.sources.base import NewsSource
from app.fil.watch_list import candidate_from_event

logger = logging.getLogger(__name__)


@dataclass
class FilRunResult:
    as_of: date
    raw_fetched: int = 0
    skipped_non_universe: int = 0
    skipped_duplicate: int = 0
    discarded: int = 0
    company_events_written: int = 0
    sector_events_written: int = 0
    watch_list_added: int = 0
    watch_list_expired: int = 0
    errors: list[str] = field(default_factory=list)


class FundamentalIntelligenceService:
    def __init__(
        self,
        *,
        stock_repo: StockRepository,
        news_event_repo: CompanyNewsEventRepository,
        watch_list_repo: FilWatchListRepository,
        sector_news_repo: SectorNewsEventRepository,
        extractor: CatalystExtractor,
        company_sources: list[NewsSource] | None = None,
        sector_sources: list[NewsSource] | None = None,
    ) -> None:
        self._stocks = stock_repo
        self._events = news_event_repo
        self._watch = watch_list_repo
        self._sector_events = sector_news_repo
        self._extractor = extractor
        self._company_sources = company_sources or []
        self._sector_sources = sector_sources or []

    def run(self, as_of: date) -> FilRunResult:
        result = FilRunResult(as_of=as_of)
        symbol_to_id = {s.symbol.upper(): s.id for s in self._stocks.list_stocks()}

        for source in self._company_sources:
            self._ingest_company_source(source, as_of, symbol_to_id, result)

        for source in self._sector_sources:
            self._ingest_sector_source(source, as_of, result)

        result.watch_list_expired = self._watch.expire_due(
            as_of=as_of, reason=WatchListDeactivationReason.EXPIRED.value
        )
        return result

    # ── Company-level ───────────────────────────────────────────────────────
    def _ingest_company_source(
        self,
        source: NewsSource,
        as_of: date,
        symbol_to_id: dict[str, str],
        result: FilRunResult,
    ) -> None:
        for item in self._safe_fetch(source, as_of, result):
            result.raw_fetched += 1
            symbol = (item.symbol or "").upper()
            stock_id = symbol_to_id.get(symbol)
            if stock_id is None:
                result.skipped_non_universe += 1
                continue
            if item.external_id and self._events.exists(
                source=item.source.value, external_id=item.external_id
            ):
                result.skipped_duplicate += 1
                continue

            extracted = self._extractor.extract(item)
            if extracted is None:
                result.discarded += 1
                continue

            event = self._events.add(
                stock_id=stock_id,
                event_date=extracted.event_date,
                source=extracted.source.value,
                category=extracted.category.value,
                sentiment=extracted.sentiment.value,
                magnitude=extracted.magnitude.value,
                confidence=extracted.confidence,
                catalyst_duration_days=extracted.catalyst_duration_days,
                summary=extracted.summary,
                raw_excerpt=extracted.raw_excerpt,
                flags={"tags": extracted.flags} if extracted.flags else None,
                is_confirmed=extracted.is_confirmed,
                external_id=item.external_id,
            )
            result.company_events_written += 1

            candidate = candidate_from_event(extracted, added_date=as_of)
            if candidate is not None:
                self._watch.add(
                    stock_id=stock_id,
                    news_event_id=event.id,
                    added_date=candidate.added_date,
                    expires_date=candidate.expires_date,
                    catalyst_type=extracted.category.value,
                    sentiment=extracted.sentiment.value,
                    confidence=extracted.confidence,
                )
                result.watch_list_added += 1

    # ── Sector-level ────────────────────────────────────────────────────────
    def _ingest_sector_source(
        self, source: NewsSource, as_of: date, result: FilRunResult
    ) -> None:
        for item in self._safe_fetch(source, as_of, result):
            result.raw_fetched += 1
            if not item.sector:
                result.skipped_non_universe += 1
                continue
            if item.external_id and self._sector_events.exists(
                source=item.source.value, external_id=item.external_id
            ):
                result.skipped_duplicate += 1
                continue

            extracted = self._extractor.extract(item)
            if extracted is None:
                result.discarded += 1
                continue

            self._sector_events.add(
                event_date=extracted.event_date,
                sector=item.sector,
                source=extracted.source.value,
                category=extracted.category.value,
                sentiment=extracted.sentiment.value,
                magnitude=extracted.magnitude.value,
                confidence=extracted.confidence,
                catalyst_duration_days=extracted.catalyst_duration_days,
                summary=extracted.summary,
                raw_excerpt=extracted.raw_excerpt,
                external_id=item.external_id,
            )
            result.sector_events_written += 1

    def _safe_fetch(
        self, source: NewsSource, as_of: date, result: FilRunResult
    ) -> list[RawNewsItem]:
        try:
            return source.fetch(as_of)
        except Exception as exc:  # one bad feed must not abort the batch
            logger.exception("FIL source fetch failed: %s", type(source).__name__)
            result.errors.append(f"{type(source).__name__}: {exc}")
            return []
