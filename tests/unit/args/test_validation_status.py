from app.args.validation_status import (
    is_current_validation_pending,
    normalize_validation_status_for_packet,
)
from app.validation.constants import (
    VALIDATION_STATUS_COMPLETED,
    VALIDATION_STATUS_INSUFFICIENT_DATA,
    VALIDATION_STATUS_PENDING,
)


def test_insufficient_data_maps_to_pending_for_packet():
    status, db_status, reason = normalize_validation_status_for_packet(
        VALIDATION_STATUS_INSUFFICIENT_DATA
    )
    assert status == VALIDATION_STATUS_PENDING
    assert db_status == VALIDATION_STATUS_INSUFFICIENT_DATA
    assert reason is not None


def test_completed_status_unchanged():
    status, db_status, reason = normalize_validation_status_for_packet(
        VALIDATION_STATUS_COMPLETED
    )
    assert status == VALIDATION_STATUS_COMPLETED
    assert db_status == VALIDATION_STATUS_COMPLETED
    assert reason is None


def test_is_pending_for_packet_and_legacy_shapes():
    assert is_current_validation_pending({"status": VALIDATION_STATUS_PENDING})
    assert is_current_validation_pending(
        {
            "status": VALIDATION_STATUS_COMPLETED,
            "database_status": VALIDATION_STATUS_INSUFFICIENT_DATA,
        }
    )
    assert not is_current_validation_pending({"status": VALIDATION_STATUS_COMPLETED})
