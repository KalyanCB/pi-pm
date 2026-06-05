"""Tests for M3.1 Investment Committee advisory logic.

Key invariants:
- HIGH_CONCERN always overrides majority (ADR-023 mandatory modification #1)
- Label→advisory mapping is deterministic
- CRO aggregation uses escalation, not pure democracy
- CommitteeResearchLabel preserved (backward compat)
"""

from app.workspace_args.constants import (
    CommitteeAdvisoryAction,
    CommitteeResearchLabel,
    aggregate_cro_advisory,
    label_to_advisory_action,
)

# ── Label → Advisory mapping ──────────────────────────────────────────────────


def test_supportive_maps_to_approve():
    assert (
        label_to_advisory_action(CommitteeResearchLabel.SUPPORTIVE)
        == CommitteeAdvisoryAction.APPROVE
    )


def test_neutral_maps_to_watch():
    assert label_to_advisory_action(CommitteeResearchLabel.NEUTRAL) == CommitteeAdvisoryAction.WATCH


def test_cautious_maps_to_reject():
    assert (
        label_to_advisory_action(CommitteeResearchLabel.CAUTIOUS) == CommitteeAdvisoryAction.REJECT
    )


def test_unknown_label_maps_to_watch():
    assert label_to_advisory_action("unknown_label") == CommitteeAdvisoryAction.WATCH


def test_mapping_is_deterministic():
    assert label_to_advisory_action("supportive") == label_to_advisory_action("supportive")


# ── HIGH_CONCERN escalation (PO Mandatory Modification #1) ───────────────────


def test_high_concern_overrides_4_approvals():
    """RC raises HIGH_CONCERN — must override 4 APPROVE votes. Not democratic."""
    actions = {
        "TARC": CommitteeAdvisoryAction.APPROVE,
        "FRC": CommitteeAdvisoryAction.APPROVE,
        "QRC": CommitteeAdvisoryAction.APPROVE,
        "NRCC": CommitteeAdvisoryAction.APPROVE,
        "RC": CommitteeAdvisoryAction.HIGH_CONCERN,
    }
    result = aggregate_cro_advisory(actions)
    assert result == CommitteeAdvisoryAction.HIGH_CONCERN


def test_high_concern_overrides_mixed():
    actions = {
        "TARC": CommitteeAdvisoryAction.APPROVE,
        "FRC": CommitteeAdvisoryAction.WATCH,
        "QRC": CommitteeAdvisoryAction.HIGH_CONCERN,
        "NRCC": CommitteeAdvisoryAction.APPROVE,
        "RC": CommitteeAdvisoryAction.REJECT,
    }
    result = aggregate_cro_advisory(actions)
    assert result == CommitteeAdvisoryAction.HIGH_CONCERN


def test_multiple_high_concern_still_high_concern():
    actions = {
        "TARC": CommitteeAdvisoryAction.HIGH_CONCERN,
        "FRC": CommitteeAdvisoryAction.HIGH_CONCERN,
        "QRC": CommitteeAdvisoryAction.APPROVE,
    }
    assert aggregate_cro_advisory(actions) == CommitteeAdvisoryAction.HIGH_CONCERN


# ── Majority voting (no HIGH_CONCERN) ─────────────────────────────────────────


def test_majority_approve():
    actions = {
        "TARC": CommitteeAdvisoryAction.APPROVE,
        "FRC": CommitteeAdvisoryAction.APPROVE,
        "QRC": CommitteeAdvisoryAction.APPROVE,
        "NRCC": CommitteeAdvisoryAction.WATCH,
        "RC": CommitteeAdvisoryAction.REJECT,
    }
    assert aggregate_cro_advisory(actions) == CommitteeAdvisoryAction.APPROVE


def test_majority_reject():
    actions = {
        "TARC": CommitteeAdvisoryAction.REJECT,
        "FRC": CommitteeAdvisoryAction.REJECT,
        "QRC": CommitteeAdvisoryAction.REJECT,
        "NRCC": CommitteeAdvisoryAction.APPROVE,
        "RC": CommitteeAdvisoryAction.WATCH,
    }
    assert aggregate_cro_advisory(actions) == CommitteeAdvisoryAction.REJECT


def test_tiebreak_reject_beats_approve():
    """On tie, REJECT takes priority over APPROVE (conservative)."""
    actions = {
        "TARC": CommitteeAdvisoryAction.APPROVE,
        "FRC": CommitteeAdvisoryAction.APPROVE,
        "QRC": CommitteeAdvisoryAction.REJECT,
        "NRCC": CommitteeAdvisoryAction.REJECT,
        "RC": CommitteeAdvisoryAction.WATCH,
    }
    result = aggregate_cro_advisory(actions)
    assert result == CommitteeAdvisoryAction.REJECT


def test_empty_committees_returns_watch():
    assert aggregate_cro_advisory({}) == CommitteeAdvisoryAction.WATCH


def test_single_committee_returns_its_action():
    assert (
        aggregate_cro_advisory({"RC": CommitteeAdvisoryAction.APPROVE})
        == CommitteeAdvisoryAction.APPROVE
    )


# ── Backward compatibility ─────────────────────────────────────────────────────


def test_research_label_enum_unchanged():
    """CommitteeResearchLabel values must not change — backward compat."""
    assert CommitteeResearchLabel.SUPPORTIVE == "supportive"
    assert CommitteeResearchLabel.NEUTRAL == "neutral"
    assert CommitteeResearchLabel.CAUTIOUS == "cautious"


def test_advisory_action_values():
    assert CommitteeAdvisoryAction.APPROVE == "APPROVE"
    assert CommitteeAdvisoryAction.WATCH == "WATCH"
    assert CommitteeAdvisoryAction.REJECT == "REJECT"
    assert CommitteeAdvisoryAction.EXIT_APPROVED == "EXIT_APPROVED"
    assert CommitteeAdvisoryAction.HIGH_CONCERN == "HIGH_CONCERN"


# ── R-ARGS-04: advisory must not affect recommendation ────────────────────────


def test_advisory_action_is_string_not_recommendation_action():
    """Advisory actions are strings — they cannot be accidentally used as
    RecommendationAction since that's a different enum."""
    from app.core.constants import RecommendationAction

    advisory_values = {a.value for a in CommitteeAdvisoryAction}
    rec_values = {a.value for a in RecommendationAction}
    # They may share some string values (WATCH, REJECT) but the types are separate
    # ensuring no accidental assignment at type-check level
    assert CommitteeAdvisoryAction.HIGH_CONCERN.value not in rec_values
    assert CommitteeAdvisoryAction.APPROVE.value not in rec_values
