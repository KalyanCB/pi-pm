from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.args.builders.investment_review_packet_builder import InvestmentReviewPacketBuilder
from app.args.builders.packet_evidence_coverage import derive_governance_confidence
from app.args.graph.workflow import ArgsResearchWorkflow
from app.args.llm.registry import CommitteeLlmRegistry
from app.args.loaders.ranking_candidate_loader import RankingCandidateLoader
from app.args.plugins.registry import CommitteeRegistry
from app.core.constants import (
    CommitteeReviewStatus,
    LineageEntityType,
    LineageRelationshipType,
    ResearchRunStatus,
)
from app.core.exceptions import NotFoundError
from app.db.repositories.args_prompt_version_repository import ArgsPromptVersionRepository
from app.db.repositories.committee_review_repository import CommitteeReviewRepository
from app.db.repositories.cro_review_repository import CroReviewRepository
from app.db.repositories.governance_research_report_repository import (
    GovernanceResearchReportRepository,
)
from app.db.repositories.investment_review_packet_repository import (
    InvestmentReviewPacketRepository,
)
from app.db.repositories.llm_execution_record_repository import LlmExecutionRecordRepository
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.research_run_repository import ResearchRunRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.services.stock_setup_research_service import StockSetupResearchService
from app.models.args import (
    CommitteeReview,
    CroReview,
    GovernanceResearchReport,
    GovernanceResearchReportEvidence,
    InvestmentReviewPacket,
)
from app.workspace_args.constants import COMMITTEE_CRO, DEFAULT_COMMITTEE_CODES


class ArgsResearchRunService:
    def __init__(
        self,
        db: Session,
        *,
        research_run_repo: ResearchRunRepository,
        packet_repo: InvestmentReviewPacketRepository,
        committee_review_repo: CommitteeReviewRepository,
        cro_review_repo: CroReviewRepository,
        governance_report_repo: GovernanceResearchReportRepository,
        lineage_repo: RunLineageRepository,
        prompt_repo: ArgsPromptVersionRepository,
        llm_record_repo: LlmExecutionRecordRepository,
        ranking_run_repo: RankingRunRepository,
        ranking_result_repo: RankingResultRepository,
        validation_repo: RankingValidationRepository,
        stock_repo: StockRepository,
        stock_setup_service: StockSetupResearchService | None = None,
        llm_registry: CommitteeLlmRegistry | None = None,
        registry: CommitteeRegistry | None = None,
    ) -> None:
        self.db = db
        self.research_run_repo = research_run_repo
        self.packet_repo = packet_repo
        self.committee_review_repo = committee_review_repo
        self.cro_review_repo = cro_review_repo
        self.governance_report_repo = governance_report_repo
        self.lineage_repo = lineage_repo
        self.prompt_repo = prompt_repo
        self.llm_record_repo = llm_record_repo
        self.validation_repo = validation_repo
        self.loader = RankingCandidateLoader(
            db, ranking_run_repo, ranking_result_repo, validation_repo
        )
        self.packet_builder = InvestmentReviewPacketBuilder(
            db,
            validation_repo,
            stock_setup_service=stock_setup_service,
        )
        self.stock_repo = stock_repo
        self.llm_registry = llm_registry or CommitteeLlmRegistry.from_settings()
        self.registry = registry or CommitteeRegistry()
        self.workflow = ArgsResearchWorkflow(self.registry, self.llm_registry)

    def run(
        self,
        *,
        ranking_run_id: UUID,
        top_n: int = 20,
        committee_codes: list[str] | None = None,
        trigger_mode: str = "on_demand",
        require_completed_validation: bool = True,
        dry_run: bool = False,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
    ) -> dict:
        ranking_run, candidates = self.loader.load(
            ranking_run_id,
            top_n=top_n,
            require_completed_validation=require_completed_validation,
        )
        codes = committee_codes or list(DEFAULT_COMMITTEE_CODES)
        run = self.research_run_repo.create(
            trigger_mode=trigger_mode,
            universe_code=universe_code or ranking_run.universe_code,
            strategy_name=strategy_name or ranking_run.strategy_name,
            strategy_version=strategy_version or ranking_run.strategy_version,
            as_of_date=ranking_run.as_of_date,
            top_n=top_n,
            committee_codes=codes,
            config_snapshot={
                "require_completed_validation": require_completed_validation,
                "dry_run": dry_run,
            },
            ranking_run_ids=[str(ranking_run_id)],
        )
        self.research_run_repo.mark_running(run, phase="build_packets")

        in_memory_packets: list = []
        persisted_packets: list[InvestmentReviewPacket] = []
        for result in candidates:
            stock = self.stock_repo.get_by_id(result.stock_id)
            if stock is None:
                continue
            packet = self.packet_builder.build(
                ranking_run=ranking_run, result=result, stock=stock
            )
            in_memory_packets.append(packet)
            if not dry_run:
                row = InvestmentReviewPacket(
                    research_run_id=run.id,
                    ranking_run_id=ranking_run.id,
                    stock_id=result.stock_id,
                    symbol=stock.symbol,
                    packet_version=packet.packet_version,
                    packet_hash=packet.packet_hash,
                    payload=_json_safe(packet.payload),
                    built_at=datetime.now(UTC),
                )
                persisted_packets.append(self.packet_repo.add(row))
                validation_report = self.validation_repo.get_by_ranking_run_id(ranking_run.id)
                self._link_packet_lineage(
                    run.id,
                    ranking_run.id,
                    row,
                    ranking_result_id=result.id,
                    validation_report_id=validation_report.id if validation_report else None,
                )

        if dry_run:
            self.research_run_repo.complete(run, status=ResearchRunStatus.COMPLETED.value)
            self.db.commit()
            return self._run_summary(run, candidates_reviewed=len(in_memory_packets), dry_run=True)

        self.research_run_repo.mark_running(run, phase="committees")
        reviews_data, cro_data, token_total = self.workflow.run_committees_and_cro(
            in_memory_packets, codes
        )
        review_rows = self._persist_reviews(run, persisted_packets, reviews_data)
        reports_issued = self._persist_cro_and_reports(
            run, ranking_run, persisted_packets, cro_data, review_rows
        )
        run.checkpoint_ref = f"memory:{run.id}"
        self.research_run_repo.complete(
            run,
            status=ResearchRunStatus.COMPLETED.value,
            phase="completed",
        )
        self.lineage_repo.link(
            child_entity_type=LineageEntityType.RESEARCH_RUN.value,
            child_entity_id=run.id,
            parent_entity_type=LineageEntityType.RANKING_RUN.value,
            parent_entity_id=ranking_run.id,
            relationship_type=LineageRelationshipType.RANKING_PRODUCES_PACKET.value,
        )
        self.db.commit()
        return self._run_summary(
            run,
            candidates_reviewed=len(persisted_packets),
            reports_issued=reports_issued,
            token_usage_total=token_total,
            dry_run=False,
        )

    def get_run(self, run_id: UUID) -> dict:
        run = self.research_run_repo.get_by_id(run_id)
        if run is None:
            raise NotFoundError(f"Research run not found: {run_id}")
        return self._run_detail(run)

    def get_latest(
        self,
        *,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        as_of_date=None,
    ) -> dict | None:
        run = self.research_run_repo.get_latest(
            universe_code=universe_code,
            strategy_name=strategy_name,
            as_of_date=as_of_date,
        )
        if run is None:
            return None
        return self._run_detail(run)

    def get_packet_for_run(self, run_id: UUID, symbol: str | None = None) -> list[dict]:
        packets = self.packet_repo.list_for_run(run_id)
        if symbol:
            packets = [p for p in packets if p.symbol == symbol]
        return [_packet_read(p) for p in packets]

    def _persist_reviews(
        self,
        run,
        packets: list[InvestmentReviewPacket],
        reviews_data: list[dict],
    ) -> dict[str, list[CommitteeReview]]:
        packet_by_symbol = {p.symbol: p for p in packets}
        reviews_by_symbol: dict[str, list[CommitteeReview]] = {}
        for row in reviews_data:
            packet = packet_by_symbol.get(row["symbol"])
            if packet is None:
                continue
            prompt = self.prompt_repo.get_or_create_stub(row["committee_code"])
            llm_rec = self.llm_record_repo.record(
                model=row.get("model", "mock"),
                input_tokens=row.get("input_tokens", 0),
                output_tokens=row.get("output_tokens", 0),
            )
            output = row["output"]
            review = CommitteeReview(
                research_run_id=run.id,
                packet_id=packet.id,
                committee_code=output["committee_code"],
                committee_version=output["committee_version"],
                status=(
                    CommitteeReviewStatus.DEGRADED.value
                    if (output.get("extensions") or {}).get("degraded")
                    else CommitteeReviewStatus.COMPLETED.value
                ),
                findings=output["findings"],
                strengths=output.get("strengths"),
                risks=output.get("risks"),
                supporting_evidence=output.get("supporting_evidence"),
                confidence=output.get("confidence"),
                extensions=output.get("extensions"),
                prompt_version_id=prompt.id,
                llm_execution_id=llm_rec.id,
                created_at=datetime.now(UTC),
            )
            self.committee_review_repo.add(review)
            reviews_by_symbol.setdefault(packet.symbol, []).append(review)
            self.lineage_repo.link(
                child_entity_type=LineageEntityType.COMMITTEE_REVIEW.value,
                child_entity_id=review.id,
                parent_entity_type=LineageEntityType.INVESTMENT_REVIEW_PACKET.value,
                parent_entity_id=packet.id,
                relationship_type=LineageRelationshipType.PACKET_REVIEWED_BY_COMMITTEE.value,
            )
        return reviews_by_symbol

    def _persist_cro_and_reports(
        self,
        run,
        ranking_run,
        packets: list[InvestmentReviewPacket],
        cro_data: list[dict],
        reviews_by_symbol: dict[str, list[CommitteeReview]],
    ) -> int:
        packet_by_symbol = {p.symbol: p for p in packets}
        count = 0
        cro_prompt = self.prompt_repo.get_or_create_stub(COMMITTEE_CRO)
        for row in cro_data:
            packet = packet_by_symbol.get(row["symbol"])
            if packet is None:
                continue
            agg = row["aggregation"]
            committee_confs = [
                float(cr.confidence)
                for cr in reviews_by_symbol.get(packet.symbol, [])
                if cr.confidence is not None
            ]
            governance_confidence = derive_governance_confidence(
                packet.payload,
                committee_confidences=committee_confs or None,
            )
            llm_rec = self.llm_record_repo.record(
                model=row.get("model", "mock-cro"),
                input_tokens=row.get("input_tokens", 0),
                output_tokens=row.get("output_tokens", 0),
            )
            cro = CroReview(
                research_run_id=run.id,
                packet_id=packet.id,
                aggregation_snapshot=agg["aggregation_snapshot"],
                rationale=agg["rationale"],
                dissent_summary=agg.get("dissent_summary"),
                confidence=governance_confidence,
                prompt_version_id=cro_prompt.id,
                llm_execution_id=llm_rec.id,
                created_at=datetime.now(UTC),
            )
            self.cro_review_repo.add(cro)
            self.lineage_repo.link(
                child_entity_type=LineageEntityType.CRO_REVIEW.value,
                child_entity_id=cro.id,
                parent_entity_type=LineageEntityType.INVESTMENT_REVIEW_PACKET.value,
                parent_entity_id=packet.id,
                relationship_type=LineageRelationshipType.REVIEWS_AGGREGATED_TO_CRO.value,
            )
            for committee_review in reviews_by_symbol.get(packet.symbol, []):
                self.lineage_repo.link(
                    child_entity_type=LineageEntityType.CRO_REVIEW.value,
                    child_entity_id=cro.id,
                    parent_entity_type=LineageEntityType.COMMITTEE_REVIEW.value,
                    parent_entity_id=committee_review.id,
                    relationship_type=LineageRelationshipType.COMMITTEE_REVIEW_AGGREGATED_TO_CRO.value,
                )
            report = GovernanceResearchReport(
                cro_review_id=cro.id,
                research_run_id=run.id,
                stock_id=packet.stock_id,
                symbol=packet.symbol,
                as_of_date=ranking_run.as_of_date,
                summary=agg["summary"],
                narrative_md=agg["rationale"],
                structured=_json_safe(agg.get("structured")),
                research_score=None,
                confidence=governance_confidence,
                created_at=datetime.now(UTC),
            )
            self.governance_report_repo.add(report)
            for ev in agg.get("evidence_refs") or []:
                self.db.add(
                    GovernanceResearchReportEvidence(
                        report_id=report.id,
                        evidence_type="committee",
                        evidence_ref=str(ev.get("ref", "unknown")),
                        payload=_json_safe(ev),
                        created_at=datetime.now(UTC),
                    )
                )
            self.lineage_repo.link(
                child_entity_type=LineageEntityType.GOVERNANCE_RESEARCH_REPORT.value,
                child_entity_id=report.id,
                parent_entity_type=LineageEntityType.CRO_REVIEW.value,
                parent_entity_id=cro.id,
                relationship_type=LineageRelationshipType.CRO_ISSUES_GOVERNANCE_REPORT.value,
            )
            count += 1
        return count

    def _link_packet_lineage(
        self,
        run_id: UUID,
        ranking_run_id: UUID,
        packet_row: InvestmentReviewPacket,
        *,
        ranking_result_id: UUID,
        validation_report_id: UUID | None,
    ) -> None:
        self.lineage_repo.link(
            child_entity_type=LineageEntityType.INVESTMENT_REVIEW_PACKET.value,
            child_entity_id=packet_row.id,
            parent_entity_type=LineageEntityType.RANKING_RUN.value,
            parent_entity_id=ranking_run_id,
            relationship_type=LineageRelationshipType.RANKING_PRODUCES_PACKET.value,
        )
        self.lineage_repo.link(
            child_entity_type=LineageEntityType.INVESTMENT_REVIEW_PACKET.value,
            child_entity_id=packet_row.id,
            parent_entity_type=LineageEntityType.RESEARCH_RUN.value,
            parent_entity_id=run_id,
            relationship_type=LineageRelationshipType.RESEARCH_RUN_PRODUCES_PACKET.value,
        )
        self.lineage_repo.link(
            child_entity_type=LineageEntityType.INVESTMENT_REVIEW_PACKET.value,
            child_entity_id=packet_row.id,
            parent_entity_type=LineageEntityType.RANKING_RESULT.value,
            parent_entity_id=ranking_result_id,
            relationship_type=LineageRelationshipType.PACKET_SOURCES_RANKING_RESULT.value,
        )
        if validation_report_id is not None:
            self.lineage_repo.link(
                child_entity_type=LineageEntityType.INVESTMENT_REVIEW_PACKET.value,
                child_entity_id=packet_row.id,
                parent_entity_type=LineageEntityType.VALIDATION_REPORT.value,
                parent_entity_id=validation_report_id,
                relationship_type=LineageRelationshipType.PACKET_SOURCES_VALIDATION_REPORT.value,
            )
        stock_setup_id = (packet_row.payload or {}).get("source_lineage", {}).get(
            "stock_setup_research_id"
        )
        if stock_setup_id:
            try:
                stock_setup_uuid = UUID(stock_setup_id)
            except ValueError:
                stock_setup_uuid = None
            if stock_setup_uuid is not None:
                self.lineage_repo.link(
                    child_entity_type=LineageEntityType.INVESTMENT_REVIEW_PACKET.value,
                    child_entity_id=packet_row.id,
                    parent_entity_type=LineageEntityType.STOCK_SETUP_RESEARCH.value,
                    parent_entity_id=stock_setup_uuid,
                    relationship_type=LineageRelationshipType.PACKET_SRC_STOCK_SETUP.value,
                )

    def _run_summary(
        self,
        run,
        *,
        candidates_reviewed: int,
        reports_issued: int = 0,
        token_usage_total: int = 0,
        dry_run: bool = False,
    ) -> dict:
        return {
            "run_id": str(run.id),
            "status": run.status,
            "as_of_date": run.as_of_date.isoformat(),
            "candidates_reviewed": candidates_reviewed,
            "governance_reports_issued": reports_issued,
            "token_usage_total": token_usage_total,
            "dry_run": dry_run,
            "duration_seconds": float(run.duration_seconds) if run.duration_seconds else None,
        }

    def _run_detail(self, run) -> dict:
        reports = self.governance_report_repo.list_for_run(run.id)
        return {
            **self._run_summary(
                run,
                candidates_reviewed=len(run.packets) if run.packets else 0,
                reports_issued=len(reports),
            ),
            "universe_code": run.universe_code,
            "strategy_name": run.strategy_name,
            "committee_codes": run.committee_codes,
            "ranking_run_ids": run.ranking_run_ids,
            "phase": run.phase,
            "governance_reports": [
                {
                    "report_id": str(r.id),
                    "symbol": r.symbol,
                    "summary": r.summary[:200],
                    "confidence": float(r.confidence) if r.confidence is not None else None,
                }
                for r in reports
            ],
        }


def _packet_read(packet: InvestmentReviewPacket) -> dict:
    return {
        "packet_id": str(packet.id),
        "symbol": packet.symbol,
        "packet_hash": packet.packet_hash,
        "packet_version": packet.packet_version,
        "payload": packet.payload,
        "built_at": packet.built_at.isoformat(),
    }


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    return value
