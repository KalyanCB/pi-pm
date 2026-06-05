"""Unit tests for committee packet views (Phase 2 prompt isolation)."""

from __future__ import annotations

from app.args.committee_packet_views import (
    build_frc_view,
    build_nrcc_view,
    build_qrc_view,
    build_rc_view,
    build_tarc_view,
)


def _full_payload() -> dict:
    return {
        "symbol": "TEST.NS",
        "ranking": {
            "rank": 2,
            "composite_score": 0.88,
            "score_components": {"volume_surge": {"normalized": 0.9}},
        },
        "technical_factors": {
            "trend_quality": {"normalized": 0.8},
            "volume_surge": {"normalized": 0.85},
        },
        "validation": {
            "status": "pending",
            "horizon_metrics": [{"horizon": 5, "sample_size": 100}],
        },
        "historical_validation_context": {"completed_reports_in_window": 2},
        "quant_evidence": {"factor_ic": [{"factor_name": "momentum", "ic_spearman": 0.1}]},
        "regime": {"regime_label": "BEAR_LOW_VOL", "strategy_regime_performance": []},
        "historical_performance": {"return_5d": 0.02},
        "fundamental_snapshot": {},
        "news_snapshot": {"status": "unavailable", "items": []},
        "market_snapshot": {"sector": "Pharma", "avg_volume": 1_000_000},
        "portfolio_context": {"existing_position": False},
        "research_context": {"notes": ["Sector stable."]},
        "stock_setup_evidence": {"setup_evidence_score": 0.6, "status": "completed"},
        "stock_quality_evidence": {"overall_stock_quality_score": 0.7},
    }


def test_tarc_view_excludes_validation_and_news():
    view = build_tarc_view(_full_payload())
    assert "ranking" in view
    assert "technical_factors" in view
    assert "validation" not in view
    assert "quant_evidence" not in view
    assert "fundamental_snapshot" not in view
    assert "news_snapshot" not in view
    assert "stock_setup_evidence" not in view
    assert "stock_quality_evidence" not in view


def test_qrc_view_excludes_technical_factors_and_news():
    view = build_qrc_view(_full_payload(), "TEST.NS")
    assert "validation" in view
    assert "factor_ic_summary" in view
    assert "stock_setup_evidence" in view
    assert "technical_factors" not in view
    assert "news_snapshot" not in view
    assert "fundamental_snapshot" not in view


def test_frc_view_flags_insufficient_fundamentals():
    view = build_frc_view(_full_payload())
    assert view["fundamental_evidence_status"] == "insufficient"
    assert "fundamental_snapshot" in view
    assert "ranking" not in view


def test_nrcc_view_flags_no_news():
    view = build_nrcc_view(_full_payload())
    assert view["news_evidence_status"] == "no_news_evidence"
    assert "news_snapshot" in view
    assert "ranking" not in view


def test_rc_view_includes_risk_blocks_not_validation():
    view = build_rc_view(_full_payload())
    assert view["risk_evidence_status"] == "sufficient"
    assert "risk_drawdown" in view
    assert "market_snapshot" in view
    assert "concentration_context" in view
    assert "regime_risk" in view
    assert "validation" not in view
    assert "fundamental_snapshot" not in view
