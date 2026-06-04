"""Unit tests for build_qrc_sqe_brief and SQE payload wiring."""

from __future__ import annotations

import json

import pytest

from app.args.plugins.qrc_sqe_brief import build_qrc_sqe_brief
from app.args.plugins.quant_payload import build_qrc_user_payload
from app.args.plugins.quant_research_brief import build_quant_research_brief
from app.args.plugins.stock_quality_evidence import build_stock_quality_evidence
from app.core.config import get_settings
from app.validation.constants import VALIDATION_STATUS_PENDING


def _breakout_packet(
    *,
    symbol: str,
    rank: int,
    see_score: float,
    qualifying: int,
    win_rate: float,
    median_return: float,
    score_components: dict,
) -> dict:
    return {
        "ranking": {
            "ranking_run_id": "b8e993e4-a049-4f3a-bcd0-29574a0f7e47",
            "as_of_date": "2026-06-02",
            "rank": rank,
            "composite_score": 0.88,
            "score_components": score_components,
        },
        "validation": {
            "status": VALIDATION_STATUS_PENDING,
            "database_status": "insufficient_data",
            "regime_label": "BEAR_LOW_VOL",
        },
        "historical_validation_context": {
            "recent_completed_validations": [
                {
                    "as_of_date": "2026-05-11",
                    "report_id": "hist-1",
                    "regime_label": "BEAR_LOW_VOL",
                    "horizon_metrics": [
                        {"horizon": 5, "sample_size": 347, "rank_ic_spearman": 0.14}
                    ],
                    "decile_metrics": [
                        {"horizon": 5, "decile": 10, "avg_return": 0.02},
                        {"horizon": 5, "decile": 1, "avg_return": -0.03},
                    ],
                }
            ],
        },
        "regime": {
            "strategy_regime_performance": [
                {
                    "regime_label": "BEAR_LOW_VOL",
                    "horizon": 5,
                    "avg_ic": -0.091,
                    "avg_spread": -0.032,
                    "sample_count": 116,
                    "is_current_regime": True,
                }
            ]
        },
        "quant_evidence": {
            "factor_ic": [
                {"factor_name": "high_proximity", "ic_spearman": -0.146, "regime_label": "BEAR_LOW_VOL"},
                {"factor_name": "relative_strength", "ic_spearman": -0.141, "regime_label": "BEAR_LOW_VOL"},
            ],
            "exit_research": [{"hit_rate": 0.55, "sample_size": 400, "mean_return": 0.01}],
        },
        "stock_setup_evidence": {
            "status": "completed",
            "setup_evidence_score": see_score,
            "qualifying_matches": qualifying,
            "total_matches": qualifying + 5,
            "regime_statistics": [
                {
                    "regime_label": "BEAR_LOW_VOL",
                    "sample_size": max(qualifying, 8),
                    "win_rate_20d": win_rate,
                    "median_return_20d": median_return,
                }
            ],
        },
    }


_HFCL_COMPONENTS = {
    "volatility_adjusted_momentum": {"normalized": "1.0", "weighted": "0.20"},
    "relative_strength": {"normalized": "1.0", "weighted": "0.15"},
    "high_proximity": {"normalized": "0.992", "weighted": "0.149"},
}


def test_qrc_sqe_brief_structure_and_no_raw_ic():
    payload = _breakout_packet(
        symbol="HFCL.NS",
        rank=1,
        see_score=62.89,
        qualifying=97,
        win_rate=0.429,
        median_return=-0.037,
        score_components=_HFCL_COMPONENTS,
    )
    brief = build_quant_research_brief(payload, "HFCL.NS")
    sqe = build_stock_quality_evidence(payload, "HFCL.NS")
    condensed = build_qrc_sqe_brief(brief, sqe)

    required = (
        "strategy_quality",
        "current_regime",
        "regime_alignment_score",
        "top_positive_factors",
        "top_negative_factors",
        "see_evidence",
        "sqe_score",
        "validation_status",
        "legacy_overall_quant_confidence",
    )
    for key in required:
        assert key in condensed

    assert condensed["sqe_score"] == sqe["overall_stock_quality_score"]
    assert condensed["strategy_quality"]["quality_score"] == brief["historical_strategy_assessment"][
        "quality_score"
    ]
    assert condensed["current_regime"]["regime_label"] == brief["current_regime_assessment"][
        "current_regime_label"
    ]
    assert condensed["regime_alignment_score"] == sqe["C_regime_alignment"]["alignment_score"]

    for factor_row in condensed["top_positive_factors"] + condensed["top_negative_factors"]:
        assert set(factor_row.keys()) == {"factor", "signed_contribution"}
        assert "ic" not in factor_row

    serialized = json.dumps(condensed)
    assert "ic_spearman" not in serialized
    assert "strategy_regime_performance" not in serialized


def test_build_qrc_user_payload_flag_off_unchanged(monkeypatch):
    monkeypatch.delenv("ARGS_QRC_USE_SQE", raising=False)
    get_settings.cache_clear()

    payload = _breakout_packet(
        symbol="HFCL.NS",
        rank=1,
        see_score=62.89,
        qualifying=97,
        win_rate=0.429,
        median_return=-0.037,
        score_components=_HFCL_COMPONENTS,
    )
    payload["stock_quality_evidence"] = build_stock_quality_evidence(payload, "HFCL.NS")

    user = build_qrc_user_payload(payload, "HFCL.NS")
    assert "qrc_sqe_brief" not in user
    assert "overall_stock_quality_score" not in user
    assert user["overall_quant_confidence"] == user["quant_research_brief"]["overall_quant_confidence"]
    assert "quant_research_brief" in user["instructions"].lower()


@pytest.fixture
def sqe_flag_on(monkeypatch):
    monkeypatch.setenv("ARGS_QRC_USE_SQE", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("ARGS_QRC_USE_SQE", raising=False)
    get_settings.cache_clear()


def test_build_qrc_user_payload_flag_on_attaches_sqe_brief(sqe_flag_on):
    assert get_settings().args_qrc_use_sqe is True

    payload = _breakout_packet(
        symbol="WOCKPHARMA.NS",
        rank=2,
        see_score=71.54,
        qualifying=110,
        win_rate=0.625,
        median_return=0.015,
        score_components=_HFCL_COMPONENTS,
    )
    payload["stock_quality_evidence"] = build_stock_quality_evidence(payload, "WOCKPHARMA.NS")

    user = build_qrc_user_payload(payload, "WOCKPHARMA.NS")
    assert "qrc_sqe_brief" in user
    assert user["overall_stock_quality_score"] == user["qrc_sqe_brief"]["sqe_score"]
    assert user["overall_quant_confidence"] == user["quant_research_brief"]["overall_quant_confidence"]
    assert "qrc_sqe_brief" in user["instructions"].lower()
    assert user["overall_stock_quality_score"] != user["overall_quant_confidence"]
