#!/usr/bin/env python3
"""Generate docs/args-packet-evidence-audit.md from DB source counts and packet coverage."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from app.args.builders.packet_evidence_coverage import (
    derive_evidence_confidence,
    score_packet_evidence,
)
from app.db.session import get_session_factory
from app.models.args import InvestmentReviewPacket as InvestmentReviewPacketModel, ResearchRun
from app.models.exit_research import ExitResearchPolicyMetric
from app.models.factor_analytics import FactorDailyMetric, FactorPerformanceMetric
from app.models.platform_traceability import StrategyRegimePerformance
from app.models.ranking_run import RankingRun
from app.models.research_intelligence import ResearchIntelligenceReport, ResearchIntelligenceRun


def _table_count(db, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _packet_field_stats(packets: list) -> dict:
    n = len(packets) or 1
    factor_ic_nonempty = 0
    exit_nonempty = 0
    regime_nonempty = 0
    research_notes_nonempty = 0
    historical_nonempty = 0
    factor_daily_nonempty = 0
    scores: list[int] = []
    confidences: list[float] = []

    for pkt in packets:
        payload = pkt.payload or {}
        quant = payload.get("quant_evidence") or {}
        if quant.get("factor_ic"):
            factor_ic_nonempty += 1
        if quant.get("exit_research"):
            exit_nonempty += 1
        if quant.get("factor_daily"):
            factor_daily_nonempty += 1
        regime = payload.get("regime") or {}
        if regime.get("strategy_regime_performance"):
            regime_nonempty += 1
        research = payload.get("research_context") or {}
        if research.get("notes"):
            research_notes_nonempty += 1
        historical = payload.get("historical_validation_context") or {}
        if historical.get("recent_completed_validations"):
            historical_nonempty += 1
        coverage = payload.get("evidence_coverage") or score_packet_evidence(payload)
        scores.append(int(coverage.get("score", 0)))
        conf = payload.get("evidence_confidence")
        if conf is None:
            conf = derive_evidence_confidence(payload, coverage)
        confidences.append(float(conf))

    conf_counter = Counter(round(c, 4) for c in confidences)
    return {
        "packet_count": len(packets),
        "factor_ic_populated_pct": round(100 * factor_ic_nonempty / n, 1),
        "exit_research_populated_pct": round(100 * exit_nonempty / n, 1),
        "factor_daily_populated_pct": round(100 * factor_daily_nonempty / n, 1),
        "regime_performance_populated_pct": round(100 * regime_nonempty / n, 1),
        "research_notes_populated_pct": round(100 * research_notes_nonempty / n, 1),
        "historical_validation_populated_pct": round(100 * historical_nonempty / n, 1),
        "evidence_coverage_score_avg": round(sum(scores) / n, 1) if scores else 0,
        "evidence_coverage_score_min": min(scores) if scores else 0,
        "evidence_coverage_score_max": max(scores) if scores else 0,
        "evidence_confidence_unique_values": len(conf_counter),
        "evidence_confidence_distribution": dict(sorted(conf_counter.items())),
    }


def _sample_packet_summary(pkt) -> dict:
    payload = pkt.payload or {}
    quant = payload.get("quant_evidence") or {}
    return {
        "symbol": pkt.symbol,
        "evidence_coverage_score": (payload.get("evidence_coverage") or {}).get("score"),
        "evidence_confidence": payload.get("evidence_confidence"),
        "factor_ic_rows": len(quant.get("factor_ic") or []),
        "exit_research_rows": len(quant.get("exit_research") or []),
        "factor_daily_rows": len(quant.get("factor_daily") or []),
        "regime_rows": len((payload.get("regime") or {}).get("strategy_regime_performance") or []),
        "research_notes": len((payload.get("research_context") or {}).get("notes") or []),
        "historical_validations": len(
            (payload.get("historical_validation_context") or {}).get(
                "recent_completed_validations"
            )
            or []
        ),
        "missing": (payload.get("evidence_coverage") or {}).get("missing") or [],
    }


def build_markdown(
    *,
    source_counts: dict,
    packet_stats: dict,
    samples: list[dict],
    research_run_id: str | None,
    ranking_run_id: str | None,
    rebuild_sample: dict | None = None,
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# ARGS packet evidence audit",
        "",
        f"Generated: {now}",
        "",
        "## Scope",
        "",
        "Evidence ingestion into `InvestmentReviewPacket` (no prompt or committee logic changes).",
        "",
        "## Source table counts",
        "",
        "| Table | Row count |",
        "|-------|-----------|",
    ]
    for table, count in source_counts.items():
        if isinstance(count, int):
            lines.append(f"| `{table}` | {count:,} |")
        else:
            lines.append(f"| `{table}` | {count} |")

    lines.extend(
        [
            "",
            "## Packet coverage",
            "",
            f"- Research run audited: `{research_run_id or 'latest'}`",
            f"- Ranking run: `{ranking_run_id or 'n/a'}`",
            f"- Packets analyzed: **{packet_stats['packet_count']}**",
            "",
            "Persisted packets reflect the builder version at ARGS run time. Use **Post-fix builder sample** "
            "(with `--rebuild-sample`) to verify current ingestion without re-running ARGS.",
            "",
            "| Field | Populated % |",
            "|-------|-------------|",
            f"| `quant_evidence.factor_ic` | {packet_stats['factor_ic_populated_pct']}% |",
            f"| `quant_evidence.exit_research` | {packet_stats['exit_research_populated_pct']}% |",
            f"| `quant_evidence.factor_daily` | {packet_stats['factor_daily_populated_pct']}% |",
            f"| `regime.strategy_regime_performance` | {packet_stats['regime_performance_populated_pct']}% |",
            f"| `research_context.notes` | {packet_stats['research_notes_populated_pct']}% |",
            f"| `historical_validation_context` | {packet_stats['historical_validation_populated_pct']}% |",
            "",
            "### Evidence coverage score (0–100)",
            "",
            f"- Average: **{packet_stats['evidence_coverage_score_avg']}**",
            f"- Min: {packet_stats['evidence_coverage_score_min']}",
            f"- Max: {packet_stats['evidence_coverage_score_max']}",
            "",
            "### Evidence confidence distribution",
            "",
            f"- Unique values: {packet_stats['evidence_confidence_unique_values']}",
            f"- Distribution: `{json.dumps(packet_stats['evidence_confidence_distribution'])}`",
            "",
            "## Missing evidence (typical)",
            "",
        ]
    )
    if samples:
        missing_union: Counter = Counter()
        for s in samples:
            for m in s.get("missing") or []:
                missing_union[m] += 1
        for item, count in missing_union.most_common():
            lines.append(f"- `{item}` ({count} sample packets)")
    else:
        lines.append("- No packets sampled.")

    lines.extend(["", "## Persisted packets (sample)", "", "```json"])
    lines.append(json.dumps(samples[:5], indent=2))
    lines.extend(["```", ""])
    if rebuild_sample:
        lines.extend(
            [
                "## Post-fix builder sample (not persisted)",
                "",
                "One packet rebuilt with current `InvestmentReviewPacketBuilder` for the same ranking run:",
                "",
                "```json",
                json.dumps(rebuild_sample, indent=2),
                "```",
                "",
            ]
        )
    lines.extend(["## Confidence calculation path", ""])
    lines.extend(
        [
            "1. **Packet build** (`InvestmentReviewPacketBuilder`): loads factor IC (latest window with `as_of_date_end <= ranking as_of`), exit research, regime performance, research intelligence, historical completed validations, factor daily for `ranking_run_id`.",
            "2. **Coverage score** (`score_packet_evidence`): weighted 0–100 across validation (current + historical), factor IC, factor daily, regime, exit research, research notes.",
            "3. **Evidence confidence** (`derive_evidence_confidence`): `coverage_score/100` plus bonuses for completed validation, historical validations, |IC|, regime rows, exit rows, research notes (clamped 0.15–0.95).",
            "4. **Governance confidence** (`derive_governance_confidence` at persist): `0.6 * evidence_confidence + 0.4 * committee_avg` when committee scores exist; else evidence confidence only. Stored on `cro_reviews` and `governance_research_reports` (CRO LLM default 0.75 is not used at persist).",
            "",
            "## Loader fixes applied",
            "",
            "- Factor IC: `list_metrics_covering_as_of` (no longer exact `as_of_date_end == ranking as_of`).",
            "- Exit research: `list_policy_metrics_covering_as_of`.",
            "- Research context: latest `research_intelligence_reports` run → `notes` + compact `reports`.",
            "- Historical validation: `list_completed_with_runs` lookback for QRC context when current run is `insufficient_data`.",
            "",
        ]
    )
    return "\n".join(lines)


def _rebuild_sample_packet(db, ranking_run_id: str) -> dict | None:
    from app.args.builders.investment_review_packet_builder import InvestmentReviewPacketBuilder
    from app.db.repositories.ranking_validation_repository import RankingValidationRepository
    from app.models.ranking_result import RankingResult
    from app.models.ranking_run import RankingRun
    from app.models.stock import Stock

    run = db.get(RankingRun, UUID(ranking_run_id))
    if run is None:
        return None
    result = db.scalar(
        select(RankingResult)
        .where(RankingResult.ranking_run_id == run.id)
        .order_by(RankingResult.rank)
        .limit(1)
    )
    if result is None:
        return None
    stock = db.get(Stock, result.stock_id)
    if stock is None:
        return None
    pkt = InvestmentReviewPacketBuilder(db, RankingValidationRepository(db)).build(
        ranking_run=run,
        result=result,
        stock=stock,
    )
    return _sample_packet_summary(
        type("Pkt", (), {"symbol": pkt.symbol, "payload": pkt.payload})()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-run-id", type=str, default=None)
    parser.add_argument(
        "--rebuild-sample",
        action="store_true",
        help="Include one freshly built packet (post-fix builder) in the audit.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "args-packet-evidence-audit.md",
    )
    args = parser.parse_args()

    db = get_session_factory()()
    try:
        source_counts = {
            "factor_performance_metrics": _table_count(db, FactorPerformanceMetric),
            "factor_daily_metrics": _table_count(db, FactorDailyMetric),
            "strategy_regime_performance": _table_count(db, StrategyRegimePerformance),
            "research_intelligence_reports": _table_count(db, ResearchIntelligenceReport),
            "research_intelligence_runs": _table_count(db, ResearchIntelligenceRun),
            "exit_research_policy_metrics": _table_count(db, ExitResearchPolicyMetric),
        }

        research_run_id = args.research_run_id
        ranking_run_id = None

        def _primary_ranking_run_id(run: ResearchRun) -> str | None:
            ids = run.ranking_run_ids or []
            return str(ids[0]) if ids else None

        if research_run_id:
            run = db.get(ResearchRun, UUID(research_run_id))
            if run is None:
                print(f"Research run not found: {research_run_id}", file=sys.stderr)
                return 1
            ranking_run_id = _primary_ranking_run_id(run)
            packets = list(
                db.scalars(
                    select(InvestmentReviewPacketModel).where(
                        InvestmentReviewPacketModel.research_run_id == run.id
                    )
                ).all()
            )
        else:
            latest = db.scalar(
                select(ResearchRun).order_by(ResearchRun.created_at.desc()).limit(1)
            )
            if latest is None:
                packets = []
            else:
                research_run_id = str(latest.id)
                ranking_run_id = _primary_ranking_run_id(latest)
                packets = list(
                    db.scalars(
                        select(InvestmentReviewPacketModel).where(
                            InvestmentReviewPacketModel.research_run_id == latest.id
                        )
                    ).all()
                )

        packet_stats = _packet_field_stats(packets)
        samples = [_sample_packet_summary(p) for p in packets[:20]]

        if ranking_run_id:
            rr = db.get(RankingRun, UUID(ranking_run_id))
            if rr:
                source_counts["ranking_run_as_of"] = rr.as_of_date.isoformat()
                source_counts["ranking_run_strategy"] = f"{rr.strategy_name}/{rr.strategy_version}"

        rebuild_sample = None
        if args.rebuild_sample and ranking_run_id:
            rebuild_sample = _rebuild_sample_packet(db, ranking_run_id)

        md = build_markdown(
            source_counts=source_counts,
            packet_stats=packet_stats,
            samples=samples,
            research_run_id=research_run_id,
            ranking_run_id=ranking_run_id,
            rebuild_sample=rebuild_sample,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(md, encoding="utf-8")
        print(f"Wrote {args.output}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
