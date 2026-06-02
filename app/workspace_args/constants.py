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
    """Research-only stance labels — not trade actions."""

    SUPPORTIVE = "supportive"
    NEUTRAL = "neutral"
    CAUTIOUS = "cautious"
