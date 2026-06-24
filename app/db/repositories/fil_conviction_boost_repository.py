"""Repository for ADR-039 fil_conviction_boosts (Phase 2 audit trail).

Written once the recommendation engine is wired to apply boosts. Provided now so
the persistence surface is complete and testable.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.fil import FilConvictionBoost


class FilConvictionBoostRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        recommendation_result_id: UUID | None,
        fil_watch_list_id: UUID | None,
        original_conviction_band: str | None,
        boosted_conviction_band: str | None,
        boost_applied: bool,
        reason: str | None,
    ) -> FilConvictionBoost:
        boost = FilConvictionBoost(
            recommendation_result_id=recommendation_result_id,
            fil_watch_list_id=fil_watch_list_id,
            original_conviction_band=original_conviction_band,
            boosted_conviction_band=boosted_conviction_band,
            boost_applied=boost_applied,
            reason=reason,
        )
        self.db.add(boost)
        self.db.flush()
        return boost
