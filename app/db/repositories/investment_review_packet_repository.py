from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.args import InvestmentReviewPacket


class InvestmentReviewPacketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, packet: InvestmentReviewPacket) -> InvestmentReviewPacket:
        self.db.add(packet)
        self.db.flush()
        return packet

    def list_for_run(self, research_run_id: UUID) -> list[InvestmentReviewPacket]:
        return list(
            self.db.scalars(
                select(InvestmentReviewPacket)
                .where(InvestmentReviewPacket.research_run_id == research_run_id)
                .order_by(InvestmentReviewPacket.symbol)
            ).all()
        )

    def get_by_id(self, packet_id: UUID) -> InvestmentReviewPacket | None:
        return self.db.get(InvestmentReviewPacket, packet_id)
