import pytest

from app.execution.constants import ExecutionStatus
from app.execution.state_machine import InvalidExecutionTransition, validate_transition


def test_valid_pending_to_submitted():
    validate_transition(ExecutionStatus.EXECUTION_PENDING, ExecutionStatus.SUBMITTED)


def test_valid_submitted_to_accepted_to_filled():
    validate_transition(ExecutionStatus.SUBMITTED, ExecutionStatus.ACCEPTED)
    validate_transition(ExecutionStatus.ACCEPTED, ExecutionStatus.FILLED)


def test_invalid_filled_to_submitted():
    with pytest.raises(InvalidExecutionTransition):
        validate_transition(ExecutionStatus.FILLED, ExecutionStatus.SUBMITTED)


def test_invalid_pending_to_filled():
    with pytest.raises(InvalidExecutionTransition):
        validate_transition(ExecutionStatus.EXECUTION_PENDING, ExecutionStatus.FILLED)
