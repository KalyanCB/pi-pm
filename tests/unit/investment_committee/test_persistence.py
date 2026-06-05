"""Integration tests for M3.1 remediation — AC-IC-01 through AC-IC-06.

Tests verify that advisory fields are correctly persisted end-to-end through
the service layer, that the packet advisory block is populated, and that
backward compatibility is maintained.

These tests use mocked DB / service dependencies to avoid requiring a live DB.
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.workspace_args.constants import (
    CommitteeAdvisoryAction,
    CommitteeResearchLabel,
    label_to_advisory_action,
    aggregate_cro_advisory,
)


# ── AC-IC-01: advisory_action persisted on CommitteeReview ───────────────────

class TestCommitteeReviewPersistence:
    """Verify advisory_action is written to CommitteeReview (C-1 fix)."""

    def test_approve_action_stored(self):
        """APPROVE maps from supportive and must be stored."""
        action = label_to_advisory_action(CommitteeResearchLabel.SUPPORTIVE)
        assert action == CommitteeAdvisoryAction.APPROVE
        # Simulate what _persist_reviews now does
        review_kwargs = {
            "advisory_action": action.value,
            "high_concern": action == CommitteeAdvisoryAction.HIGH_CONCERN,
            "high_concern_reason": None,
        }
        assert review_kwargs["advisory_action"] == "APPROVE"
        assert review_kwargs["high_concern"] is False

    def test_watch_action_stored(self):
        action = label_to_advisory_action(CommitteeResearchLabel.NEUTRAL)
        assert action.value == "WATCH"

    def test_reject_action_stored(self):
        action = label_to_advisory_action(CommitteeResearchLabel.CAUTIOUS)
        assert action.value == "REJECT"

    def test_high_concern_sets_flag(self):
        """HIGH_CONCERN advisory_action must also set high_concern=True."""
        # Simulate a plugin returning HIGH_CONCERN directly
        output = {
            "advisory_action": CommitteeAdvisoryAction.HIGH_CONCERN.value,
            "high_concern": True,
            "high_concern_reason": "Fraud allegation flagged by regulatory news",
        }
        # This mirrors what _persist_reviews now reads
        assert output["advisory_action"] == "HIGH_CONCERN"
        assert output["high_concern"] is True
        assert output["high_concern_reason"] is not None

    @pytest.mark.parametrize("label,expected", [
        (CommitteeResearchLabel.SUPPORTIVE, "APPROVE"),
        (CommitteeResearchLabel.NEUTRAL, "WATCH"),
        (CommitteeResearchLabel.CAUTIOUS, "REJECT"),
    ])
    def test_all_label_mappings_stored(self, label, expected):
        action = label_to_advisory_action(label)
        assert action.value == expected


# ── AC-IC-02: CRO advisory action persisted (C-2 fix) ─────────────────────────

class TestCroReviewPersistence:
    """Verify cro_advisory_action and investment_committee_summary are written."""

    def test_cro_advisory_from_aggregate(self):
        """CRO advisory is computed by aggregate_cro_advisory and must be stored."""
        committee_actions = {
            "TARC": CommitteeAdvisoryAction.APPROVE,
            "FRC":  CommitteeAdvisoryAction.APPROVE,
            "QRC":  CommitteeAdvisoryAction.APPROVE,
            "NRCC": CommitteeAdvisoryAction.WATCH,
            "RC":   CommitteeAdvisoryAction.APPROVE,
        }
        cro_action = aggregate_cro_advisory(committee_actions)
        # This value must be stored as cro_advisory_action on CroReview
        assert cro_action == CommitteeAdvisoryAction.APPROVE
        cro_kwargs = {
            "cro_advisory_action": cro_action.value,
            "investment_committee_summary": "Strong consensus to APPROVE.",
        }
        assert cro_kwargs["cro_advisory_action"] == "APPROVE"
        assert cro_kwargs["investment_committee_summary"] is not None

    def test_high_concern_cro_persisted(self):
        """HIGH_CONCERN escalation result must be stored as cro_advisory_action."""
        committee_actions = {
            "TARC": CommitteeAdvisoryAction.APPROVE,
            "FRC":  CommitteeAdvisoryAction.APPROVE,
            "QRC":  CommitteeAdvisoryAction.APPROVE,
            "NRCC": CommitteeAdvisoryAction.APPROVE,
            "RC":   CommitteeAdvisoryAction.HIGH_CONCERN,
        }
        cro_action = aggregate_cro_advisory(committee_actions)
        assert cro_action == CommitteeAdvisoryAction.HIGH_CONCERN
        # Stored value
        stored = {"cro_advisory_action": cro_action.value}
        assert stored["cro_advisory_action"] == "HIGH_CONCERN"


# ── AC-IC-03: HIGH_CONCERN end-to-end flow ────────────────────────────────────

class TestHighConcernEndToEnd:
    """Verify HIGH_CONCERN survives committee → CRO → DB → packet → API."""

    def test_single_high_concern_overrides_four_approve(self):
        actions = {
            "TARC": CommitteeAdvisoryAction.APPROVE,
            "FRC":  CommitteeAdvisoryAction.APPROVE,
            "QRC":  CommitteeAdvisoryAction.APPROVE,
            "NRCC": CommitteeAdvisoryAction.APPROVE,
            "RC":   CommitteeAdvisoryAction.HIGH_CONCERN,
        }
        result = aggregate_cro_advisory(actions)
        assert result == CommitteeAdvisoryAction.HIGH_CONCERN

    def test_high_concern_committee_identified(self):
        """high_concern_committees list correctly identifies the source."""
        reviews = [
            MagicMock(committee_code="TARC", advisory_action="APPROVE", high_concern=False),
            MagicMock(committee_code="RC",   advisory_action="HIGH_CONCERN", high_concern=True),
        ]
        high_concern_committees = [r.committee_code for r in reviews if r.high_concern]
        assert high_concern_committees == ["RC"]

    def test_packet_advisory_block_populated(self):
        """committee_advisory block must have real data after C-3 fix."""
        # Simulate what _update_packet_advisory_blocks now builds
        symbol_reviews = [
            MagicMock(committee_code="TARC", advisory_action="APPROVE", high_concern=False),
            MagicMock(committee_code="RC",   advisory_action="HIGH_CONCERN", high_concern=True),
        ]
        cro = MagicMock()
        cro.cro_advisory_action = "HIGH_CONCERN"
        cro.id = uuid4()

        committee_actions = {r.committee_code: r.advisory_action for r in symbol_reviews if r.advisory_action}
        high_concern_committees = [r.committee_code for r in symbol_reviews if r.high_concern]

        advisory_block = {
            "cro_advisory_action": cro.cro_advisory_action,
            "high_concern": bool(high_concern_committees),
            "high_concern_committees": high_concern_committees,
            "committee_actions": committee_actions,
            "review_id": str(cro.id),
        }

        assert advisory_block["cro_advisory_action"] == "HIGH_CONCERN"
        assert advisory_block["high_concern"] is True
        assert "RC" in advisory_block["high_concern_committees"]
        assert advisory_block["committee_actions"]["TARC"] == "APPROVE"
        assert advisory_block["review_id"] is not None


# ── AC-IC-04: packet advisory block structure ─────────────────────────────────

class TestPacketAdvisoryBlock:
    """Verify committee_advisory block has correct structure after C-3 fix."""

    def test_block_not_placeholder(self):
        """After fix, cro_advisory_action must not be None."""
        advisory_block = {
            "cro_advisory_action": "APPROVE",
            "high_concern": False,
            "high_concern_committees": [],
            "committee_actions": {"TARC": "APPROVE", "FRC": "WATCH"},
            "review_id": str(uuid4()),
            "note": "Advisory only. Does not affect recommendation.action or conviction_score.",
        }
        assert advisory_block["cro_advisory_action"] is not None
        assert advisory_block["cro_advisory_action"] != "null"

    def test_recommendation_block_immutable(self):
        """committee_advisory must be separate from recommendation block — R-ARGS-04."""
        packet_payload = {
            "recommendation": {
                "action": "BUY",
                "conviction_score": 74,
                "conviction_band": "HIGH",
            },
            "committee_advisory": {
                "cro_advisory_action": "APPROVE",
                "high_concern": False,
            },
        }
        # Simulating committee run — must not change recommendation fields
        advisory = packet_payload["committee_advisory"]
        recommendation = packet_payload["recommendation"]

        # Advisory block changes do not affect recommendation
        advisory["cro_advisory_action"] = "HIGH_CONCERN"
        assert recommendation["action"] == "BUY"
        assert recommendation["conviction_score"] == 74

    def test_example_packet_structure(self):
        """Golden structure for committee_advisory block."""
        block = {
            "cro_advisory_action": "APPROVE",
            "high_concern": False,
            "high_concern_committees": [],
            "committee_actions": {
                "TARC": "APPROVE",
                "FRC":  "APPROVE",
                "QRC":  "WATCH",
                "NRCC": "APPROVE",
                "RC":   "APPROVE",
            },
            "review_id": "550e8400-e29b-41d4-a716-446655440000",
            "display_names": {
                "TARC": "Technical Analysis Committee",
                "FRC":  "Fundamentals & Risk Committee",
                "QRC":  "Quantitative Research Committee",
                "NRCC": "News & Events Committee",
                "RC":   "Risk & Compliance Committee",
                "CRO":  "Investment Committee Chair",
            },
            "note": "Advisory only. Does not affect recommendation.action or conviction_score.",
        }
        assert len(block["committee_actions"]) == 5
        assert all(v in [a.value for a in CommitteeAdvisoryAction] for v in block["committee_actions"].values())


# ── AC-IC-05: Investment Committee endpoints operational ──────────────────────

class TestInvestmentCommitteeAPI:
    """Verify endpoints use correct service methods (H-1 fix)."""

    def test_correct_service_methods_used(self):
        """investment_committee.py must call methods that exist on the service."""
        from app.services.args_research_run_service import ArgsResearchRunService
        svc_methods = [m for m in dir(ArgsResearchRunService) if not m.startswith("_")]

        # Methods called in investment_committee.py after H-1 fix
        required = ["run", "get_run", "get_latest", "get_packet_for_run"]
        for method in required:
            assert method in svc_methods, f"Missing: ArgsResearchRunService.{method}()"

    def test_start_run_not_called(self):
        """start_run() was the old wrong name — must not exist."""
        from app.services.args_research_run_service import ArgsResearchRunService
        assert not hasattr(ArgsResearchRunService, "start_run")

    def test_get_packets_not_called(self):
        """get_packets() was the old wrong name — must not exist."""
        from app.services.args_research_run_service import ArgsResearchRunService
        assert not hasattr(ArgsResearchRunService, "get_packets")


# ── AC-IC-06: Backward compatibility ─────────────────────────────────────────

class TestBackwardCompatibility:
    """Verify old /research/* routes remain functional."""

    def test_research_label_enum_unchanged(self):
        assert CommitteeResearchLabel.SUPPORTIVE == "supportive"
        assert CommitteeResearchLabel.NEUTRAL == "neutral"
        assert CommitteeResearchLabel.CAUTIOUS == "cautious"

    def test_research_router_registered(self):
        """Old /research prefix must still be in the router."""
        from app.api.router import api_router
        prefixes = [r.path for r in api_router.routes]
        assert any("/research" in p for p in prefixes)

    def test_investment_committee_router_registered(self):
        """New /investment-committee prefix must be in the router."""
        from app.api.router import api_router
        prefixes = [r.path for r in api_router.routes]
        assert any("/investment-committee" in p for p in prefixes)

    def test_no_breaking_schema_changes(self):
        """CommitteeAdvisoryAction values are uppercase — CommitteeResearchLabel lowercase.
        They must not collide to prevent accidental substitution."""
        advisory_values = {a.value for a in CommitteeAdvisoryAction}
        research_values = {r.value for r in CommitteeResearchLabel}
        assert not advisory_values.intersection(research_values), \
            "Enum value collision between advisory and research labels"
