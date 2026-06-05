from app.args.plugins.quant_payload import (
    build_qrc_user_payload,
    compute_validation_coverage,
    detect_evidence_gaps,
)
from app.validation.constants import VALIDATION_STATUS_PENDING


def _pending_packet_with_historical() -> dict:
    return {
        "validation": {
            "status": VALIDATION_STATUS_PENDING,
            "database_status": "insufficient_data",
            "horizon_metrics": [],
            "decile_metrics": [],
            "regime_label": "BEAR_LOW_VOL",
        },
        "historical_validation_context": {
            "recent_completed_validations": [
                {
                    "as_of_date": "2026-05-26",
                    "report_id": "hist-1",
                    "regime_label": "BEAR_LOW_VOL",
                    "horizon_metrics": [
                        {"horizon": 5, "sample_size": 400, "rank_ic_spearman": 0.04}
                    ],
                    "decile_metrics": [{"horizon": 5, "decile": 10, "avg_return": 0.02}],
                }
            ]
        },
        "quant_evidence": {
            "factor_ic": [{"factor_name": "momentum", "ic_spearman": 0.05, "horizon": 5}],
            "exit_research": [{"hit_rate": 0.55, "sample_size": 500, "mean_return": 0.01}],
        },
        "regime": {
            "strategy_regime_performance": [
                {"regime_label": "BEAR_LOW_VOL", "horizon": 5, "avg_ic": 0.03, "sample_count": 12}
            ]
        },
        "stock_setup_evidence": {
            "status": "completed",
            "setup_evidence_score": 72,
            "qualifying_matches": 8,
        },
    }


def test_coverage_uses_historical_when_current_pending():
    coverage = compute_validation_coverage(_pending_packet_with_historical())
    assert coverage["uses_historical_validation"] is True
    assert coverage["components"]["horizon_metrics"] is True
    assert coverage["components"]["decile_metrics"] is True
    assert coverage["components"]["see_evidence"] is True
    assert coverage["coverage_pct"] > 40.0


def test_gaps_treat_pending_as_neutral_not_missing_current_horizons_only():
    gaps = detect_evidence_gaps(_pending_packet_with_historical())
    assert any("pending" in g.lower() and "neutral" in g.lower() for g in gaps)
    assert not any("No horizon metrics present (current or historical)" in g for g in gaps)


def test_qrc_payload_includes_brief_and_see():
    payload = build_qrc_user_payload(_pending_packet_with_historical(), "TEST.NS")
    assert payload["validation_summary"]["current_run_validation"] == "pending_neutral"
    assert payload["validation_summary"]["historical_validation_as_of"] == "2026-05-26"
    brief = payload["quant_research_brief"]
    assert brief["see_assessment"]["setup_evidence_score"] == 72
    assert brief["overall_quant_confidence"] == payload["overall_quant_confidence"]
    assert "pending" in payload["instructions"].lower()
