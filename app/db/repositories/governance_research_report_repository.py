from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.args import GovernanceResearchReport


class GovernanceResearchReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, report: GovernanceResearchReport) -> GovernanceResearchReport:
        self.db.add(report)
        self.db.flush()
        return report

    def list_for_run(self, research_run_id: UUID) -> list[GovernanceResearchReport]:
        return list(
            self.db.scalars(
                select(GovernanceResearchReport)
                .options(selectinload(GovernanceResearchReport.evidence))
                .where(GovernanceResearchReport.research_run_id == research_run_id)
            ).all()
        )

    def get_by_id(self, report_id: UUID) -> GovernanceResearchReport | None:
        return self.db.scalar(
            select(GovernanceResearchReport)
            .options(selectinload(GovernanceResearchReport.evidence))
            .where(GovernanceResearchReport.id == report_id)
        )
