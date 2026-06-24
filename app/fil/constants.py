"""ADR-039 Fundamental Intelligence Layer — enums, thresholds, category metadata.

Kept local to the ``app.fil`` package (rather than ``app.core.constants``) so the
subsystem is fully self-contained and can be wired into the recommendation engine
in a later, separate change. Nothing here is imported by the trading flow yet.
"""

from __future__ import annotations

from enum import StrEnum


class NewsEventSource(StrEnum):
    """Where a raw item originated. Tier-1 sources are official regulatory feeds."""

    BSE_ANNOUNCEMENT = "BSE_ANNOUNCEMENT"
    NSE_FEED = "NSE_FEED"
    SEBI_FILING = "SEBI_FILING"
    SEBI_BULK_BLOCK = "SEBI_BULK_BLOCK"
    # Sector-level (Phase 3)
    PIB_PRESS = "PIB_PRESS"
    RBI_POLICY = "RBI_POLICY"
    DGFT = "DGFT"
    MINISTRY_RAILWAYS = "MINISTRY_RAILWAYS"
    MINISTRY_DEFENCE = "MINISTRY_DEFENCE"
    # Tier-2 (added one at a time, gated to WATCH only at integration time)
    ET_MARKETS_RSS = "ET_MARKETS_RSS"
    MONEYCONTROL_RSS = "MONEYCONTROL_RSS"


class CatalystSentiment(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    CONTEXT = "CONTEXT"  # AI assesses direction from context (e.g. MANAGEMENT_CHANGE)


class CatalystMagnitude(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CatalystCategory(StrEnum):
    EARNINGS_BEAT = "EARNINGS_BEAT"
    EARNINGS_MISS = "EARNINGS_MISS"
    ORDER_WIN = "ORDER_WIN"
    REGULATORY_APPROVAL = "REGULATORY_APPROVAL"
    REGULATORY_RISK = "REGULATORY_RISK"
    PROMOTER_BUYING = "PROMOTER_BUYING"
    PROMOTER_SELLING = "PROMOTER_SELLING"
    DEBT_REDUCTION = "DEBT_REDUCTION"
    DEBT_CONCERN = "DEBT_CONCERN"
    CAPEX_ANNOUNCEMENT = "CAPEX_ANNOUNCEMENT"
    SECTOR_TAILWIND = "SECTOR_TAILWIND"
    SECTOR_HEADWIND = "SECTOR_HEADWIND"
    ANALYST_UPGRADE = "ANALYST_UPGRADE"
    ANALYST_DOWNGRADE = "ANALYST_DOWNGRADE"
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"
    MERGER_ACQUISITION = "MERGER_ACQUISITION"


class WatchListDeactivationReason(StrEnum):
    EXPIRED = "EXPIRED"
    CONTRADICTED = "CONTRADICTED"
    MANUAL = "MANUAL"
    PRICED_IN = "PRICED_IN"


# ── Confidence gating (ADR §"Confidence Threshold") ──────────────────────────
# >= WATCH_LIST_CONFIDENCE_FLOOR        → eligible for watch list (full conviction)
# [UNCONFIRMED_FLOOR, WATCH_LIST_FLOOR) → stored as UNCONFIRMED, analysis only
# < UNCONFIRMED_FLOOR                   → discarded
WATCH_LIST_CONFIDENCE_FLOOR = 0.85
UNCONFIRMED_CONFIDENCE_FLOOR = 0.70

# Sector catalysts are propagated to member stocks at a haircut — a sector-wide
# tailwind is less precise than a company-specific event (ADR §"How Sector
# Signal Propagates to Stocks").
SECTOR_PROPAGATION_HAIRCUT = 0.70

# Sector rotation alert: N+ stocks from one sector in the top pool + active tailwind.
SECTOR_ROTATION_MIN_STOCKS = 3

# Only HIGH / MEDIUM magnitude events are eligible to influence conviction.
CONVICTION_ELIGIBLE_MAGNITUDES = frozenset({CatalystMagnitude.HIGH, CatalystMagnitude.MEDIUM})

# Default catalyst lifetimes (trading-day approximation, in calendar days) used when
# the extractor does not supply an explicit duration. Source: ADR §"Categories".
DEFAULT_CATALYST_DURATION_DAYS: dict[CatalystCategory, int] = {
    CatalystCategory.EARNINGS_BEAT: 20,
    CatalystCategory.EARNINGS_MISS: 15,
    CatalystCategory.ORDER_WIN: 30,
    CatalystCategory.REGULATORY_APPROVAL: 25,
    CatalystCategory.REGULATORY_RISK: 45,
    CatalystCategory.PROMOTER_BUYING: 25,
    CatalystCategory.PROMOTER_SELLING: 18,
    CatalystCategory.DEBT_REDUCTION: 38,
    CatalystCategory.DEBT_CONCERN: 60,
    CatalystCategory.CAPEX_ANNOUNCEMENT: 45,
    CatalystCategory.SECTOR_TAILWIND: 60,
    CatalystCategory.SECTOR_HEADWIND: 45,
    CatalystCategory.ANALYST_UPGRADE: 7,
    CatalystCategory.ANALYST_DOWNGRADE: 7,
    CatalystCategory.MANAGEMENT_CHANGE: 18,
    CatalystCategory.MERGER_ACQUISITION: 45,
}

# Negative catalysts — at integration time these suppress BUYs (downgrade to WATCH).
# Defined here so the classification is owned by the FIL package.
NEGATIVE_CATEGORIES: frozenset[CatalystCategory] = frozenset(
    {
        CatalystCategory.EARNINGS_MISS,
        CatalystCategory.REGULATORY_RISK,
        CatalystCategory.PROMOTER_SELLING,
        CatalystCategory.DEBT_CONCERN,
        CatalystCategory.ANALYST_DOWNGRADE,
        CatalystCategory.SECTOR_HEADWIND,
    }
)


def default_duration_days(category: CatalystCategory) -> int:
    """Fallback catalyst lifetime when the extractor omits one."""
    return DEFAULT_CATALYST_DURATION_DAYS.get(category, 20)
