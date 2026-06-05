"""Lineage helpers — every Copilot source_ref traces to auditable entity IDs."""

from __future__ import annotations

from typing import Any


def source_ref(
    table: str,
    entity_id: str,
    *,
    recommendation_run_id: str | None = None,
    recommendation_id: str | None = None,
    portfolio_position_id: str | None = None,
    committee_review_id: str | None = None,
    **extra: str,
) -> dict[str, str]:
    """Build a structured audit ref for copilot_query_logs.retrieved_ids."""
    ref: dict[str, str] = {"table": table, "id": entity_id}
    if recommendation_run_id:
        ref["recommendation_run_id"] = recommendation_run_id
    if recommendation_id:
        ref["recommendation_id"] = recommendation_id
    if portfolio_position_id:
        ref["portfolio_position_id"] = portfolio_position_id
    if committee_review_id:
        ref["committee_review_id"] = committee_review_id
    ref.update({k: v for k, v in extra.items() if v})
    return ref


def lineage_summary(source_refs: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Collapse retrieved_ids into lineage buckets for audit export."""
    buckets: dict[str, list[str]] = {
        "recommendation_run_ids": [],
        "recommendation_ids": [],
        "portfolio_position_ids": [],
        "committee_review_ids": [],
    }
    for ref in source_refs:
        for key, bucket in (
            ("recommendation_run_id", "recommendation_run_ids"),
            ("recommendation_id", "recommendation_ids"),
            ("portfolio_position_id", "portfolio_position_ids"),
            ("committee_review_id", "committee_review_ids"),
        ):
            val = ref.get(key)
            if val and val not in buckets[bucket]:
                buckets[bucket].append(val)
    return buckets
