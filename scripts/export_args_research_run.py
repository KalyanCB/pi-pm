#!/usr/bin/env python3
"""Export a full ARGS research run to markdown (packets, committees, governance, lineage)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_session_factory
from app.models.args import (
    CommitteeReview,
    CroReview,
    GovernanceResearchReport,
    GovernanceResearchReportEvidence,
    InvestmentReviewPacket,
    LlmExecutionRecord,
    ResearchRun,
)
from app.args.plugins.stock_quality_evidence import condense_stock_quality_evidence
from app.models.platform_traceability import RunLineageRecord


def _json_default(value: object) -> object:
    if isinstance(value, (UUID, date, datetime)):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Not JSON serializable: {type(value)!r}")


def _dump(obj: object) -> str:
    return json.dumps(obj, indent=2, default=_json_default)


def _row_dict(row, *, fields: list[str]) -> dict:
    return {field: getattr(row, field) for field in fields}


def export_run(db: Session, run_id: UUID, output: Path) -> None:
    run = db.scalar(
        select(ResearchRun)
        .where(ResearchRun.id == run_id)
        .options(
            selectinload(ResearchRun.packets),
            selectinload(ResearchRun.committee_reviews),
            selectinload(ResearchRun.cro_reviews),
            selectinload(ResearchRun.governance_reports).selectinload(
                GovernanceResearchReport.evidence
            ),
        )
    )
    if run is None:
        raise SystemExit(f"Research run not found: {run_id}")

    packets = sorted(run.packets, key=lambda p: p.symbol)
    committee_reviews = sorted(
        run.committee_reviews,
        key=lambda r: (r.packet_id, r.committee_code),
    )
    cro_reviews = sorted(run.cro_reviews, key=lambda r: r.packet_id)
    governance_reports = sorted(run.governance_reports, key=lambda r: r.symbol)

    packet_by_id = {p.id: p for p in packets}

    evidence_rows: list[dict] = []
    for report in governance_reports:
        for ev in report.evidence:
            evidence_rows.append(
                {
                    "report_id": str(report.id),
                    "symbol": report.symbol,
                    "evidence_type": ev.evidence_type,
                    "evidence_ref": ev.evidence_ref,
                    "payload": ev.payload,
                    "created_at": ev.created_at,
                }
            )

    child_ids: set[UUID] = set()
    for review in committee_reviews:
        child_ids.add(review.id)
    for review in cro_reviews:
        child_ids.add(review.id)
    for report in governance_reports:
        child_ids.add(report.id)
    for packet in packets:
        child_ids.add(packet.id)

    lineage_edges: list[dict] = []
    if child_ids:
        edges = db.scalars(
            select(RunLineageRecord).where(RunLineageRecord.child_entity_id.in_(child_ids))
        ).all()
        lineage_edges = [
            {
                "child_entity_type": edge.child_entity_type,
                "child_entity_id": str(edge.child_entity_id),
                "parent_entity_type": edge.parent_entity_type,
                "parent_entity_id": str(edge.parent_entity_id),
                "relationship_type": edge.relationship_type,
            }
            for edge in edges
        ]

    llm_ids = {
        review.llm_execution_id
        for review in committee_reviews
        if review.llm_execution_id is not None
    } | {review.llm_execution_id for review in cro_reviews if review.llm_execution_id is not None}
    llm_records: list[dict] = []
    if llm_ids:
        records = db.scalars(
            select(LlmExecutionRecord).where(LlmExecutionRecord.id.in_(llm_ids))
        ).all()
        llm_records = [
            _row_dict(
                rec,
                fields=[
                    "id",
                    "model",
                    "provider",
                    "input_tokens",
                    "output_tokens",
                    "request_ref",
                    "response_ref",
                    "latency_ms",
                    "metadata_",
                    "created_at",
                ],
            )
            for rec in records
        ]

    lines: list[str] = [
        f"# ARGS Research Run Export: `{run_id}`",
        "",
        "## Executive summary",
        "",
        f"- **As of date:** {run.as_of_date.isoformat()}",
        f"- **Universe / strategy:** {run.universe_code} / {run.strategy_name} v{run.strategy_version}",
        f"- **Committees:** {', '.join(run.committee_codes)}",
        f"- **Top N:** {run.top_n}",
        f"- **Status:** {run.status}",
        f"- **Ranking run IDs:** {', '.join(run.ranking_run_ids)}",
        f"- **Packets:** {len(packets)}",
        f"- **Committee reviews:** {len(committee_reviews)}",
        f"- **Governance reports:** {len(governance_reports)}",
        "",
        "| Rank | Symbol | Composite score | Governance confidence |",
        "|------|--------|-----------------|----------------------|",
    ]

    for packet in packets:
        ranking = (packet.payload or {}).get("ranking") or {}
        rank = ranking.get("rank", "")
        score = ranking.get("composite_score", "")
        gov = next((g for g in governance_reports if g.symbol == packet.symbol), None)
        conf = gov.confidence if gov and gov.confidence is not None else ""
        lines.append(f"| {rank} | {packet.symbol} | {score} | {conf} |")

    lines.extend(["", "## 1) Research Run", "", "```json", _dump({
        "id": str(run.id),
        "status": run.status,
        "as_of_date": run.as_of_date.isoformat(),
        "universe_code": run.universe_code,
        "strategy_name": run.strategy_name,
        "strategy_version": run.strategy_version,
        "top_n": run.top_n,
        "committee_codes": run.committee_codes,
        "ranking_run_ids": run.ranking_run_ids,
        "phase": run.phase,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "duration_seconds": str(run.duration_seconds) if run.duration_seconds is not None else None,
        "config_snapshot": run.config_snapshot,
    }), "```", "", "## 2) Investment Review Packets", ""])

    for index, packet in enumerate(packets, start=1):
        lines.extend([
            f"### Packet {index}: `{packet.symbol}`",
            "",
            "```json",
            _dump({
                "id": str(packet.id),
                "symbol": packet.symbol,
                "packet_hash": packet.packet_hash,
                "packet_version": packet.packet_version,
                "built_at": packet.built_at,
                "ranking_run_id": str(packet.ranking_run_id),
                "stock_id": str(packet.stock_id),
                "payload": packet.payload,
            }),
            "```",
            "",
        ])

    lines.extend(["", "## 2b) Stock Quality Evidence (condensed)", ""])
    for index, packet in enumerate(packets, start=1):
        sqe = (packet.payload or {}).get("stock_quality_evidence")
        if not sqe:
            lines.extend([
                f"### SQE {index}: `{packet.symbol}`",
                "",
                "_No stock_quality_evidence on packet._",
                "",
            ])
            continue
        lines.extend([
            f"### SQE {index}: `{packet.symbol}`",
            "",
            "```json",
            _dump(condense_stock_quality_evidence(sqe)),
            "```",
            "",
        ])

    lines.append("## 3) Committee Reviews")
    lines.append("")
    for index, review in enumerate(committee_reviews, start=1):
        packet = packet_by_id.get(review.packet_id)
        symbol = packet.symbol if packet else str(review.packet_id)
        lines.extend([
            f"### Committee Review {index}: `{symbol}` / `{review.committee_code}`",
            "",
            "```json",
            _dump({
                "id": str(review.id),
                "committee_code": review.committee_code,
                "committee_version": review.committee_version,
                "status": review.status,
                "findings": review.findings,
                "strengths": review.strengths,
                "risks": review.risks,
                "supporting_evidence": review.supporting_evidence,
                "confidence": str(review.confidence) if review.confidence is not None else None,
                "extensions": review.extensions,
                "prompt_version_id": str(review.prompt_version_id) if review.prompt_version_id else None,
                "llm_execution_id": str(review.llm_execution_id) if review.llm_execution_id else None,
                "created_at": review.created_at,
            }),
            "```",
            "",
        ])

    lines.extend(["## 4) CRO Reviews", ""])
    if not cro_reviews:
        lines.extend(["```json", "[]", "```", ""])
    for index, review in enumerate(cro_reviews, start=1):
        packet = packet_by_id.get(review.packet_id)
        symbol = packet.symbol if packet else str(review.packet_id)
        lines.extend([
            f"### CRO Review {index}: `{symbol}`",
            "",
            "```json",
            _dump({
                "id": str(review.id),
                "aggregation_snapshot": review.aggregation_snapshot,
                "rationale": review.rationale,
                "dissent_summary": review.dissent_summary,
                "confidence": str(review.confidence) if review.confidence is not None else None,
                "prompt_version_id": str(review.prompt_version_id) if review.prompt_version_id else None,
                "llm_execution_id": str(review.llm_execution_id) if review.llm_execution_id else None,
                "created_at": review.created_at,
            }),
            "```",
            "",
        ])

    lines.extend(["## 5) Governance Research Reports", ""])
    for index, report in enumerate(governance_reports, start=1):
        lines.extend([
            f"### Governance Report {index}: `{report.symbol}`",
            "",
            "```json",
            _dump({
                "id": str(report.id),
                "symbol": report.symbol,
                "as_of_date": report.as_of_date.isoformat(),
                "summary": report.summary,
                "narrative_md": report.narrative_md,
                "structured": report.structured,
                "research_score": str(report.research_score) if report.research_score is not None else None,
                "confidence": str(report.confidence) if report.confidence is not None else None,
                "created_at": report.created_at,
            }),
            "```",
            "",
        ])

    lines.extend([
        "## 6) Governance Evidence Rows",
        "",
        "```json",
        _dump(evidence_rows),
        "```",
        "",
        "## 7) LLM Execution Records",
        "",
        "```json",
        _dump(llm_records),
        "```",
        "",
        "## 8) Lineage Edges",
        "",
        "```json",
        _dump(lineage_edges),
        "```",
        "",
    ])

    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export ARGS research run to markdown")
    parser.add_argument("run_id", type=UUID)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output markdown path (default: docs/args-run-<id>-export.md)",
    )
    args = parser.parse_args()
    output = args.output or Path(f"docs/args-run-{args.run_id}-export.md")
    output.parent.mkdir(parents=True, exist_ok=True)

    Session = get_session_factory()
    with Session() as db:
        export_run(db, args.run_id, output)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
