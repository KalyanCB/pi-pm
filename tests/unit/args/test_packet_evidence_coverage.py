from app.args.builders.packet_evidence_coverage import (
    derive_evidence_confidence,
    derive_governance_confidence,
    score_packet_evidence,
)


def _full_payload() -> dict:
    return {
        "validation": {"status": "completed", "horizon_metrics": [{"horizon": 5}]},
        "historical_validation_context": {
            "recent_completed_validations": [{"as_of_date": "2026-05-01"}]
        },
        "quant_evidence": {
            "factor_ic": [{"ic_spearman": 0.08}],
            "factor_daily": [{"ic_spearman": 0.05}],
            "exit_research": [{"hit_rate": 0.6}],
        },
        "regime": {"strategy_regime_performance": [{"regime_label": "BULL"}]},
        "research_context": {"notes": ["IC stable in bull regime."]},
    }


def test_score_packet_evidence_full():
    coverage = score_packet_evidence(_full_payload())
    assert coverage["score"] == 100
    assert coverage["missing"] == []


def test_score_packet_evidence_empty():
    coverage = score_packet_evidence({})
    assert coverage["score"] == 0
    assert len(coverage["missing"]) >= 5


def test_derive_evidence_confidence_varies_with_coverage():
    full = derive_evidence_confidence(_full_payload(), score_packet_evidence(_full_payload()))
    empty = derive_evidence_confidence({}, score_packet_evidence({}))
    assert full > empty
    assert 0.15 <= empty <= 0.95
    assert 0.15 <= full <= 0.95


def test_derive_governance_confidence_blends_committee():
    payload = _full_payload()
    payload["evidence_confidence"] = 0.8
    only_evidence = derive_governance_confidence(payload)
    blended = derive_governance_confidence(payload, committee_confidences=[0.5, 0.7])
    assert only_evidence == 0.8
    assert blended != only_evidence
    assert 0.15 <= blended <= 0.95
