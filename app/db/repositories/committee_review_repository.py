from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.args import CommitteeReview


class CommitteeReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, review: CommitteeReview) -> CommitteeReview:
        self.db.add(review)
        self.db.flush()
        return review

    def list_for_run(self, research_run_id: UUID) -> list[CommitteeReview]:
        return list(
            self.db.scalars(
                select(CommitteeReview).where(CommitteeReview.research_run_id == research_run_id)
            ).all()
        )

    def list_for_packet(self, packet_id: UUID) -> list[CommitteeReview]:
        return list(
            self.db.scalars(
                select(CommitteeReview).where(CommitteeReview.packet_id == packet_id)
            ).all()
        )
