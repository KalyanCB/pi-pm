"""News/filing source adapters for the FIL ingestion pipeline (ADR-039)."""

from app.fil.sources.base import NewsSource, StaticNewsSource
from app.fil.sources.nse_bse import NseBseAnnouncementSource
from app.fil.sources.sector_feeds import SectorRssSource

__all__ = [
    "NewsSource",
    "StaticNewsSource",
    "NseBseAnnouncementSource",
    "SectorRssSource",
]
