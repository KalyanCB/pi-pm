"""Execution platform constants — Track K."""
from __future__ import annotations

from enum import StrEnum


class ExecutionMode(StrEnum):
    PAPER = "PAPER"
    LIVE = "LIVE"


class ExecutionStatus(StrEnum):
    """Auditable order lifecycle states."""

    EXECUTION_PENDING = "EXECUTION_PENDING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


TERMINAL_STATUSES = frozenset(
    {
        ExecutionStatus.FILLED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.REJECTED,
        ExecutionStatus.FAILED,
    }
)

PORTFOLIO_ELIGIBLE_STATUSES = frozenset({ExecutionStatus.FILLED})
