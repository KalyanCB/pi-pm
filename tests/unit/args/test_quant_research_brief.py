"""Unit tests for per-stock quant research brief and QRC confidence dispersion."""

from __future__ import annotations

import statistics

from app.args.plugins.quant_payload import build_qrc_user_payload
from app.args.plugins.quant_research_brief import build_quant_research_brief
from app.validation.constants import VALIDATION_STATUS_PENDING


def _shared_pending_packet(*, see_score: float, qualifying: int, win_rate: float) -> dict:
    """Strategy-level evidence identical; SEE varies by stock."""
    return {
        "validation": {
            "status": VALIDATION_STATUS_PENDING,
            "database_status": "insufficient_data",
            "horizon_metrics": [],
            "decile_metrics": [],
            "regime_label": "BEAR_LOW_VOL",
        },
        "historical_validation_context": {
            "completed_reports_in_window": 3,
            "recent_completed_validations": [
                {
                    "as_of_date": "2026-05-26",
                    "report_id": "hist-1",
                    "regime_label": "BEAR_LOW_VOL",
                    "horizon_metrics": [
                        {
                            "horizon": 5,
                            "sample_size": 400,
                            "rank_ic_spearman": 0.04,
                            "hit_rate": 0.56,
                        }
                    ],
                    "decile_metrics": [
                        {"horizon": 5, "decile": 10, "avg_return": 0.025},
                        {"horizon": 5, "decile": 1, "avg_return": -0.005},
                    ],
                }
            ],
        },
        "quant_evidence": {
            "factor_ic": [
                {
                    "factor_name": "momentum",
                    "ic_spearman": 0.05,
                    "horizon": 5,
                    "stability_score": 0.72,
                }
            ],
            "exit_research": [{"hit_rate": 0.55, "sample_size": 500, "mean_return": 0.01}],
        },
        "regime": {
            "strategy_regime_performance": [
                {
                    "regime_label": "BEAR_LOW_VOL",
                    "horizon": 5,
                    "avg_ic": 0.03,
                    "avg_spread": 0.012,
                    "sample_count": 12,
                    "is_current_regime": True,
                }
            ]
        },
        "stock_setup_evidence": {
            "status": "completed",
            "setup_evidence_score": see_score,
            "qualifying_matches": qualifying,
            "total_matches": qualifying + 2,
            "regime_statistics": [
                {
                    "regime_label": "BEAR_LOW_VOL",
                    "sample_size": qualifying,
                    "win_rate_20d": win_rate,
                    "avg_return_20d": 0.018 if win_rate > 0.5 else -0.005,
                    "median_return_20d": 0.012 if win_rate > 0.5 else -0.003,
                }
            ],
        },
    }


def test_different_symbols_get_different_confidence_with_same_pending_validation():
    strong = build_quant_research_brief(
        _shared_pending_packet(see_score=88, qualifying=18, win_rate=0.62),
        "HFCL.NS",
    )
    weak = build_quant_research_brief(
        _shared_pending_packet(see_score=41, qualifying=3, win_rate=0.44),
        "WOCKPHARMA.NS",
    )

    assert strong["overall_quant_confidence"] != weak["overall_quant_confidence"]
    assert strong["overall_quant_confidence"] > weak["overall_quant_confidence"]
    assert strong["see_assessment"]["quality_score"] > weak["see_assessment"]["quality_score"]
    assert strong["historical_strategy_assessment"]["quality_score"] == (
        weak["historical_strategy_assessment"]["quality_score"]
    )
    assert strong["validation_status"]["pending_neutral"] is True
    assert weak["validation_status"]["pending_neutral"] is True


def test_pending_validation_does_not_reduce_confidence_vs_neutral_baseline():
    pending = build_quant_research_brief(
        _shared_pending_packet(see_score=55, qualifying=8, win_rate=0.52),
        "TEST.NS",
    )
    assert pending["validation_status"]["informational_score"] == 0.50
    assert pending["overall_quant_confidence"] >= 0.45


def test_qrc_payload_uses_brief_not_raw_factor_rows():
    payload = build_qrc_user_payload(
        _shared_pending_packet(see_score=72, qualifying=8, win_rate=0.55),
        "TEST.NS",
    )
    assert "quant_research_brief" in payload
    assert payload["overall_quant_confidence"] == payload["quant_research_brief"]["overall_quant_confidence"]
    assert "decile_metrics" not in payload
    assert "horizon_metrics" not in payload
    assert "stock_setup_evidence" not in payload
    assert "factor_ic_summary" not in payload
    assert payload["validation_summary"]["current_run_validation"] == "pending_neutral"


def test_confidence_dispersion_across_symbol_batch():
    symbols = [
        ("HFCL.NS", 83, 16, 0.60),
        ("WOCKPHARMA.NS", 91, 22, 0.65),
        ("THERMAX.NS", 48, 4, 0.43),
        ("LAURUSLABS.NS", 67, 10, 0.54),
        ("TRITURBINE.NS", 55, 6, 0.49),
    ]
    confidences = [
        build_quant_research_brief(
            _shared_pending_packet(see_score=s, qualifying=q, win_rate=w),
            sym,
        )["overall_quant_confidence"]
        for sym, s, q, w in symbols
    ]

    assert len(set(confidences)) > 1
    assert statistics.pstdev(confidences) > 0.02
    assert min(confidences) < max(confidences)
