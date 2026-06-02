from uuid import uuid4

from app.core.constants import LineageEntityType, LineageRelationshipType
from app.db.repositories.run_lineage_repository import RunLineageRepository


def test_research_lineage_entity_types_exist():
    assert LineageEntityType.RESEARCH_RUN.value == "research_run"
    assert LineageRelationshipType.CRO_ISSUES_GOVERNANCE_REPORT.value == (
        "cro_issues_governance_report"
    )


def test_lineage_link_idempotent(db_session):
    repo = RunLineageRepository(db_session)
    child = uuid4()
    parent = uuid4()
    r1 = repo.link(
        child_entity_type=LineageEntityType.RESEARCH_RUN.value,
        child_entity_id=child,
        parent_entity_type=LineageEntityType.RANKING_RUN.value,
        parent_entity_id=parent,
        relationship_type=LineageRelationshipType.RANKING_PRODUCES_PACKET.value,
    )
    r2 = repo.link(
        child_entity_type=LineageEntityType.RESEARCH_RUN.value,
        child_entity_id=child,
        parent_entity_type=LineageEntityType.RANKING_RUN.value,
        parent_entity_id=parent,
        relationship_type=LineageRelationshipType.RANKING_PRODUCES_PACKET.value,
    )
    assert r1.id == r2.id
