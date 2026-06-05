import pytest

from app.workspace_args.committee_contracts import CommitteeReviewOutput
from app.workspace_args.evidence_validator import (
    validate_committee_output,
    validate_supporting_evidence,
)

PACKET = {
    "ranking": {"rank": 1, "composite_score": 0.9},
    "validation": {"status": "completed", "horizon_metrics": [{"horizon": 20}]},
    "quant_evidence": {"factor_ic": [{"id": "f1", "factor_name": "momentum"}]},
}


def test_valid_evidence_ref():
    evidence = validate_supporting_evidence(PACKET, [{"ref": "validation:status"}], findings="ok")
    assert evidence[0]["ref"] == "validation:status"


def test_invalid_evidence_ref_raises():
    with pytest.raises(ValueError, match="not found"):
        validate_supporting_evidence(PACKET, [{"ref": "validation:horizon:99"}])


def test_findings_require_evidence():
    with pytest.raises(ValueError, match="empty"):
        validate_supporting_evidence(PACKET, [], findings="IC is 0.05")


def test_trade_field_rejected():
    with pytest.raises(ValueError, match="Forbidden"):
        validate_committee_output(
            PACKET,
            CommitteeReviewOutput(
                committee_code="TARC",
                committee_version="1.0.0",
                findings="",
                strengths=[],
                risks=[],
                supporting_evidence=[],
                confidence=0.5,
                extensions={"recommendation_label": "BUY"},
            ),
        )
