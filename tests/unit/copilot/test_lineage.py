"""Tests for Copilot lineage helpers."""

from app.copilot.lineage import lineage_summary, source_ref


def test_source_ref_includes_lineage_ids():
    ref = source_ref(
        "recommendation_results",
        "abc-123",
        recommendation_run_id="run-1",
        recommendation_id="abc-123",
        portfolio_position_id="pos-9",
        committee_review_id="cr-7",
    )
    assert ref["table"] == "recommendation_results"
    assert ref["recommendation_run_id"] == "run-1"
    assert ref["recommendation_id"] == "abc-123"
    assert ref["portfolio_position_id"] == "pos-9"
    assert ref["committee_review_id"] == "cr-7"


def test_lineage_summary_deduplicates():
    refs = [
        source_ref(
            "recommendation_results", "r1", recommendation_run_id="run-1", recommendation_id="r1"
        ),
        source_ref(
            "recommendation_results", "r2", recommendation_run_id="run-1", recommendation_id="r2"
        ),
        source_ref("committee_reviews", "c1", committee_review_id="c1"),
    ]
    summary = lineage_summary(refs)
    assert summary["recommendation_run_ids"] == ["run-1"]
    assert summary["recommendation_ids"] == ["r1", "r2"]
    assert summary["committee_review_ids"] == ["c1"]
