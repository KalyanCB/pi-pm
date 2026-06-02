from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.args import CroReview


class CroReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, review: CroReview) -> CroReview:
        self.db.add(review)
        self.db.flush()
        return review

    def list_for_run(self, research_run_id: UUID) -> list[CroReview]:
        return list(
            self.db.scalars(
                select(CroReview).where(CroReview.research_run_id == research_run_id)
            ).all()
        )

    def get_for_packet(self, packet_id: UUID) -> CroReview | None:
        return self.db.scalar(select(CroReview).where(CroReview.packet_id == packet_id))
