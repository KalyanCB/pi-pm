"""Execution state machine — auditable transitions (Track K)."""
from __future__ import annotations

from app.execution.constants import ExecutionStatus

ALLOWED_TRANSITIONS: dict[ExecutionStatus, frozenset[ExecutionStatus]] = {
    ExecutionStatus.EXECUTION_PENDING: frozenset(
        {ExecutionStatus.SUBMITTED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}
    ),
    ExecutionStatus.SUBMITTED: frozenset(
        {
            ExecutionStatus.ACCEPTED,
            ExecutionStatus.REJECTED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        }
    ),
    ExecutionStatus.ACCEPTED: frozenset(
        {
            ExecutionStatus.PARTIALLY_FILLED,
            ExecutionStatus.FILLED,
            ExecutionStatus.REJECTED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        }
    ),
    ExecutionStatus.PARTIALLY_FILLED: frozenset(
        {ExecutionStatus.FILLED, ExecutionStatus.CANCELLED, ExecutionStatus.FAILED}
    ),
    ExecutionStatus.FILLED: frozenset(),
    ExecutionStatus.CANCELLED: frozenset(),
    ExecutionStatus.REJECTED: frozenset(),
    ExecutionStatus.FAILED: frozenset(),
}


class InvalidExecutionTransition(Exception):
    def __init__(self, current: ExecutionStatus, target: ExecutionStatus) -> None:
        super().__init__(f"Invalid transition {current.value} → {target.value}")
        self.current = current
        self.target = target


def validate_transition(current: ExecutionStatus, target: ExecutionStatus) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidExecutionTransition(current, target)
