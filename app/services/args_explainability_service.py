from __future__ import annotations

from uuid import UUID

from app.core.constants import LineageEntityType
from app.core.exceptions import NotFoundError
from app.db.repositories.committee_review_repository import CommitteeReviewRepository
from app.db.repositories.cro_review_repository import CroReviewRepository
from app.db.repositories.governance_research_report_repository import (
    GovernanceResearchReportRepository,
)
from app.db.repositories.investment_review_packet_repository import (
    InvestmentReviewPacketRepository,
)
from app.db.repositories.research_run_repository import ResearchRunRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository


class ArgsExplainabilityService:
    def __init__(
        self,
        research_run_repo: ResearchRunRepository,
        packet_repo: InvestmentReviewPacketRepository,
        committee_review_repo: CommitteeReviewRepository,
        cro_review_repo: CroReviewRepository,
        governance_report_repo: GovernanceResearchReportRepository,
        lineage_repo: RunLineageRepository,
    ) -> None:
        self.research_run_repo = research_run_repo
        self.packet_repo = packet_repo
        self.committee_review_repo = committee_review_repo
        self.cro_review_repo = cro_review_repo
        self.governance_report_repo = governance_report_repo
        self.lineage_repo = lineage_repo

    def explain_run(self, run_id: UUID) -> dict:
        run = self.research_run_repo.get_by_id(run_id)
        if run is None:
            raise NotFoundError(f"Research run not found: {run_id}")

        packets = self.packet_repo.list_for_run(run_id)
        reviews = self.committee_review_repo.list_for_run(run_id)
        cro_reviews = self.cro_review_repo.list_for_run(run_id)
        reports = self.governance_report_repo.list_for_run(run_id)

        return {
            "research_run_id": str(run_id),
            "status": run.status,
            "as_of_date": run.as_of_date.isoformat(),
            "ranking_run_ids": run.ranking_run_ids,
            "committee_reviews": [
                {
                    "committee_code": r.committee_code,
                    "symbol": next((p.symbol for p in packets if p.id == r.packet_id), None),
                    "findings": r.findings,
                    "confidence": float(r.confidence) if r.confidence is not None else None,
                    "supporting_evidence": r.supporting_evidence,
                }
                for r in reviews
            ],
            "cro_reviews": [
                {
                    "symbol": next((p.symbol for p in packets if p.id == c.packet_id), None),
                    "rationale": c.rationale,
                    "dissent_summary": c.dissent_summary,
                    "confidence": float(c.confidence) if c.confidence is not None else None,
                }
                for c in cro_reviews
            ],
            "governance_reports": [
                {
                    "report_id": str(g.id),
                    "symbol": g.symbol,
                    "summary": g.summary,
                }
                for g in reports
            ],
            "packet_count": len(packets),
        }

    def lineage_for_run(self, run_id: UUID) -> dict:
        run = self.research_run_repo.get_by_id(run_id)
        if run is None:
            raise NotFoundError(f"Research run not found: {run_id}")

        seen: set[tuple] = set()
        edges: list[dict] = []
        queue: list[tuple[str, UUID]] = [(LineageEntityType.RESEARCH_RUN.value, run_id)]

        while queue:
            entity_type, entity_id = queue.pop(0)
            for rec in self.lineage_repo.list_for_entity(entity_type, entity_id):
                key = (
                    rec.child_entity_type,
                    rec.child_entity_id,
                    rec.parent_entity_type,
                    rec.parent_entity_id,
                    rec.relationship_type,
                )
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    {
                        "child_entity_type": rec.child_entity_type,
                        "child_entity_id": str(rec.child_entity_id),
                        "parent_entity_type": rec.parent_entity_type,
                        "parent_entity_id": str(rec.parent_entity_id),
                        "relationship_type": rec.relationship_type,
                    }
                )
                queue.append((rec.parent_entity_type, rec.parent_entity_id))
                if rec.child_entity_type != entity_type or rec.child_entity_id != entity_id:
                    queue.append((rec.child_entity_type, rec.child_entity_id))

        packets = self.packet_repo.list_for_run(run_id)
        for packet in packets:
            if (LineageEntityType.INVESTMENT_REVIEW_PACKET.value, packet.id) not in {
                (e["child_entity_type"], UUID(e["child_entity_id"])) for e in edges
            }:
                for rec in self.lineage_repo.list_for_entity(
                    LineageEntityType.INVESTMENT_REVIEW_PACKET.value, packet.id
                ):
                    key = (
                        rec.child_entity_type,
                        rec.child_entity_id,
                        rec.parent_entity_type,
                        rec.parent_entity_id,
                        rec.relationship_type,
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    edges.append(
                        {
                            "child_entity_type": rec.child_entity_type,
                            "child_entity_id": str(rec.child_entity_id),
                            "parent_entity_type": rec.parent_entity_type,
                            "parent_entity_id": str(rec.parent_entity_id),
                            "relationship_type": rec.relationship_type,
                        }
                    )

        for review in self.committee_review_repo.list_for_run(run_id):
            for rec in self.lineage_repo.list_for_entity(
                LineageEntityType.COMMITTEE_REVIEW.value, review.id
            ):
                key = (
                    rec.child_entity_type,
                    rec.child_entity_id,
                    rec.parent_entity_type,
                    rec.parent_entity_id,
                    rec.relationship_type,
                )
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    {
                        "child_entity_type": rec.child_entity_type,
                        "child_entity_id": str(rec.child_entity_id),
                        "parent_entity_type": rec.parent_entity_type,
                        "parent_entity_id": str(rec.parent_entity_id),
                        "relationship_type": rec.relationship_type,
                    }
                )

        for cro in self.cro_review_repo.list_for_run(run_id):
            for rec in self.lineage_repo.list_for_entity(
                LineageEntityType.CRO_REVIEW.value, cro.id
            ):
                key = (
                    rec.child_entity_type,
                    rec.child_entity_id,
                    rec.parent_entity_type,
                    rec.parent_entity_id,
                    rec.relationship_type,
                )
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    {
                        "child_entity_type": rec.child_entity_type,
                        "child_entity_id": str(rec.child_entity_id),
                        "parent_entity_type": rec.parent_entity_type,
                        "parent_entity_id": str(rec.parent_entity_id),
                        "relationship_type": rec.relationship_type,
                    }
                )

        for report in self.governance_report_repo.list_for_run(run_id):
            for rec in self.lineage_repo.list_for_entity(
                LineageEntityType.GOVERNANCE_RESEARCH_REPORT.value, report.id
            ):
                key = (
                    rec.child_entity_type,
                    rec.child_entity_id,
                    rec.parent_entity_type,
                    rec.parent_entity_id,
                    rec.relationship_type,
                )
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    {
                        "child_entity_type": rec.child_entity_type,
                        "child_entity_id": str(rec.child_entity_id),
                        "parent_entity_type": rec.parent_entity_type,
                        "parent_entity_id": str(rec.parent_entity_id),
                        "relationship_type": rec.relationship_type,
                    }
                )

        return {"research_run_id": str(run_id), "edges": edges}
