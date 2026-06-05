#!/usr/bin/env python3
"""Read-only committee overlap / uniqueness analysis for ARGS research runs."""

from __future__ import annotations

import argparse
import json
from datetime import date
from uuid import UUID

from sqlalchemy import select

from app.args.analytics.committee_effectiveness import (
    compute_packet_metrics,
    confidence_clustering_by_committee,
    load_research_run_reviews,
    summarize_run_metrics,
)
from app.core.constants import ResearchRunStatus
from app.db.session import get_session_factory
from app.models.args import ResearchRun


def _resolve_run_id(db, run_id: str | None, strategy: str | None, as_of: str | None) -> UUID:
    if run_id:
        return UUID(run_id)
    stmt = (
        select(ResearchRun.id)
        .where(ResearchRun.status == ResearchRunStatus.COMPLETED.value)
        .order_by(ResearchRun.completed_at.desc())
    )
    if strategy:
        stmt = stmt.where(ResearchRun.strategy_name == strategy)
    if as_of:
        stmt = stmt.where(ResearchRun.as_of_date == date.fromisoformat(as_of))
    resolved = db.scalar(stmt.limit(1))
    if resolved is None:
        raise SystemExit("No matching completed research run found")
    return resolved


def _print_run_summary(
    run: ResearchRun,
    summary: dict,
    clustering: dict,
    by_packet: dict,
    *,
    example_symbol: str | None,
) -> None:
    print(f"\n{'=' * 72}")
    print(f"Research run: {run.id}")
    print(f"Strategy: {run.strategy_name} @ {run.strategy_version}  as_of={run.as_of_date}")
    print(f"Status: {run.status}  completed_at={run.completed_at}")
    print(f"{'=' * 72}")
    print(f"Packets: {summary['packet_count']}  Reviews: {summary['review_count']}")
    print(f"Mean finding Jaccard (higher = more overlap): {summary['mean_finding_jaccard']}")
    print(f"Mean evidence overlap: {summary['mean_evidence_overlap']}")
    print(f"Mean confidence std (per packet): {summary['mean_confidence_std']}")
    print(f"Mean composite uniqueness: {summary['mean_composite_uniqueness']}")
    print(f"Mean disagreement score: {summary.get('mean_disagreement_score', 'n/a')}")
    print(f"Mean agreement echo score: {summary.get('mean_agreement_echo_score', 'n/a')}")
    print(
        f"Headline disagreement rate (packets >= threshold): "
        f"{summary['headline_disagreement_rate']}"
    )
    print(
        f"Strict independence packet rate: {summary.get('strict_independence_packet_rate', 'n/a')}"
    )
    print(f"Effective independence rate: {summary.get('effective_independence_rate', 'n/a')}")
    print(f"Degraded review fraction: {summary['degraded_review_fraction']}")

    print("\nTop shared evidence refs:")
    for ref, count in summary["top_shared_evidence_refs"]:
        print(f"  {ref}: {count}")

    print("\nConfidence clustering by committee:")
    for code, stats in clustering.items():
        print(
            f"  {code}: mean={stats['mean']} std={stats['std']} "
            f"unique_vals={stats['unique_rounded_values']} n={stats['count']}"
        )

    if example_symbol:
        for packet_id, reviews in by_packet.items():
            if reviews and reviews[0].symbol == example_symbol:
                metrics = compute_packet_metrics(reviews)
                print(f"\nExample packet: {example_symbol} ({packet_id})")
                print(json.dumps(metrics["per_committee_uniqueness"], indent=2))
                return
        print(f"\n(No packet found for symbol {example_symbol})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="ARGS research_run UUID")
    parser.add_argument("--strategy", help="e.g. breakout_v1, momentum_v1")
    parser.add_argument("--as-of", help="YYYY-MM-DD filter")
    parser.add_argument(
        "--json-out",
        help="Write full summary JSON to path (for doc generation)",
    )
    parser.add_argument(
        "--example-symbol",
        help="Print per-committee uniqueness for this symbol",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as db:
        run_ids: list[UUID] = []
        if args.run_id:
            run_ids.append(_resolve_run_id(db, args.run_id, None, None))
        elif args.strategy or args.as_of:
            run_ids.append(_resolve_run_id(db, None, args.strategy, args.as_of))
        else:
            for strategy in ("breakout_v1", "momentum_v1"):
                run_ids.append(_resolve_run_id(db, None, strategy, args.as_of or "2026-06-02"))

        all_summaries: dict[str, object] = {}
        for rid in run_ids:
            run, by_packet, _cro = load_research_run_reviews(db, rid)
            summary = summarize_run_metrics(by_packet)
            clustering = confidence_clustering_by_committee(by_packet)
            _print_run_summary(
                run,
                summary,
                clustering,
                by_packet,
                example_symbol=args.example_symbol,
            )
            all_summaries[str(rid)] = {
                "strategy": run.strategy_name,
                "as_of_date": str(run.as_of_date),
                "summary": {k: v for k, v in summary.items() if k != "per_packet"},
                "clustering": clustering,
            }

        if args.json_out:
            path = args.json_out
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(all_summaries, fh, indent=2)
            print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
