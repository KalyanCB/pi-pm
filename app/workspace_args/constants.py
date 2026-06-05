from enum import StrEnum

PACKET_VERSION = "1.0.0"

DEFAULT_COMMITTEE_CODES = ("TARC", "FRC", "QRC", "NRCC", "RC")

COMMITTEE_TARC = "TARC"
COMMITTEE_FRC = "FRC"
COMMITTEE_QRC = "QRC"
COMMITTEE_NRCC = "NRCC"
COMMITTEE_RC = "RC"
COMMITTEE_CRO = "CRO"


class CommitteeResearchLabel(StrEnum):
    """Research-only stance labels — not trade actions.

    Preserved for backward compatibility. New code should use CommitteeAdvisoryAction.
    """

    SUPPORTIVE = "supportive"
    NEUTRAL = "neutral"
    CAUTIOUS = "cautious"


class CommitteeAdvisoryAction(StrEnum):
    """Investor-facing advisory actions emitted by the Investment Committee.

    These are DISPLAY-ONLY. They must never mutate recommendation.action,
    conviction_score, conviction_band, or recommendation reason codes (R-ARGS-04).

    HIGH_CONCERN always overrides majority vote in CRO aggregation (ADR-023).
    """

    APPROVE = "APPROVE"
    WATCH = "WATCH"
    REJECT = "REJECT"
    EXIT_APPROVED = "EXIT_APPROVED"
    HIGH_CONCERN = "HIGH_CONCERN"


# Mapping from legacy research label → investor-facing advisory action
_LABEL_TO_ADVISORY: dict[str, CommitteeAdvisoryAction] = {
    CommitteeResearchLabel.SUPPORTIVE: CommitteeAdvisoryAction.APPROVE,
    CommitteeResearchLabel.NEUTRAL:    CommitteeAdvisoryAction.WATCH,
    CommitteeResearchLabel.CAUTIOUS:   CommitteeAdvisoryAction.REJECT,
}


def label_to_advisory_action(label: str) -> CommitteeAdvisoryAction:
    """Derive CommitteeAdvisoryAction from a legacy CommitteeResearchLabel.

    Falls back to WATCH for unknown values.
    """
    return _LABEL_TO_ADVISORY.get(label, CommitteeAdvisoryAction.WATCH)


def aggregate_cro_advisory(
    committee_actions: dict[str, CommitteeAdvisoryAction],
) -> CommitteeAdvisoryAction:
    """Aggregate committee advisory actions into a CRO advisory action.

    HIGH_CONCERN escalation (ADR-023, PO Mandatory Modification #1):
      IF any committee emits HIGH_CONCERN → cro_advisory_action = HIGH_CONCERN
      ELSE → majority vote among remaining actions

    Risk concerns are NOT democratic. A single HIGH_CONCERN from any committee
    overrides all APPROVE votes.
    """
    actions = list(committee_actions.values())

    if CommitteeAdvisoryAction.HIGH_CONCERN in actions:
        return CommitteeAdvisoryAction.HIGH_CONCERN

    # Majority vote for non-HIGH_CONCERN cases
    counts: dict[CommitteeAdvisoryAction, int] = {}
    for action in actions:
        counts[action] = counts.get(action, 0) + 1

    if not counts:
        return CommitteeAdvisoryAction.WATCH

    # Tiebreak priority: REJECT > WATCH > APPROVE > EXIT_APPROVED
    priority = [
        CommitteeAdvisoryAction.REJECT,
        CommitteeAdvisoryAction.WATCH,
        CommitteeAdvisoryAction.APPROVE,
        CommitteeAdvisoryAction.EXIT_APPROVED,
    ]
    max_count = max(counts.values())
    top = [a for a in priority if counts.get(a, 0) == max_count]
    return top[0]


# Investor-facing display names (PO approved 2026-06-05)
COMMITTEE_DISPLAY_NAMES: dict[str, str] = {
    COMMITTEE_TARC: "Technical Analysis Committee",
    COMMITTEE_FRC:  "Fundamentals & Risk Committee",
    COMMITTEE_QRC:  "Quantitative Research Committee",
    COMMITTEE_NRCC: "News & Events Committee",
    COMMITTEE_RC:   "Risk & Compliance Committee",
    COMMITTEE_CRO:  "Investment Committee Chair",
}

# Internal → external terminology map (presentation layer only)
INTERNAL_TO_EXTERNAL_TERMS: dict[str, str] = {
    "ARGS research run":   "Investment Committee review",
    "committee_label":     "advisory_action",
    "cro_synthesis":       "committee_report",
    "governance_report":   "investment_committee_report",
    "research_run":        "committee_review",
}
