"""Unit tests for Stock Quality Evidence (SQE) builder."""

from __future__ import annotations

from app.args.plugins.stock_quality_evidence import (
    SCHEMA_VERSION,
    build_stock_quality_evidence,
)
from app.validation.constants import VALIDATION_STATUS_PENDING


def _breakout_bear_packet(
    *,
    symbol: str,
    rank: int,
    composite: float,
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
            "composite_score": composite,
            "score_components": score_components,
        },
        "validation": {
            "status": VALIDATION_STATUS_PENDING,
            "database_status": "insufficient_data",
            "regime_label": "BEAR_LOW_VOL",
        },
        "historical_validation_context": {
            "completed_reports_in_window": 3,
            "recent_completed_validations": [
                {
                    "as_of_date": "2026-05-11",
                    "report_id": "hist-1",
                    "regime_label": "BEAR_LOW_VOL",
                    "horizon_metrics": [
                        {
                            "horizon": 5,
                            "sample_size": 347,
                            "rank_ic_spearman": 0.14,
                            "hit_rate": 0.54,
                        }
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
                },
                {
                    "regime_label": "BULL_LOW_VOL",
                    "horizon": 5,
                    "avg_ic": 0.038,
                    "avg_spread": 0.016,
                    "sample_count": 98,
                    "is_current_regime": False,
                },
            ]
        },
        "quant_evidence": {
            "factor_ic": [
                {
                    "factor_name": "high_proximity",
                    "ic_spearman": -0.146,
                    "regime_label": "BEAR_LOW_VOL",
                },
                {
                    "factor_name": "relative_strength",
                    "ic_spearman": -0.141,
                    "regime_label": "BEAR_LOW_VOL",
                },
                {
                    "factor_name": "relative_strength_acceleration",
                    "ic_spearman": 0.024,
                    "regime_label": "BEAR_LOW_VOL",
                },
                {
                    "factor_name": "volatility_adjusted_momentum",
                    "ic_spearman": -0.12,
                    "regime_label": "BEAR_LOW_VOL",
                },
                {
                    "factor_name": "consolidation_breakout",
                    "ic_spearman": -0.08,
                    "regime_label": "BEAR_LOW_VOL",
                },
            ],
            "exit_research": [
                {
                    "policy_family": "FIXED_HOLD",
                    "policy_variant": "60",
                    "mean_return": 0.047,
                    "hit_rate": 0.637,
                    "sample_size": 400,
                },
                {
                    "policy_family": "TRAILING_STOP",
                    "policy_variant": "10",
                    "mean_return": -0.01,
                    "hit_rate": 0.42,
                    "sample_size": 200,
                },
            ],
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
                    "avg_return_20d": 0.035 if win_rate >= 0.5 else -0.005,
                    "median_return_20d": median_return,
                    "avg_max_drawdown_20d": 0.139,
                    "avg_max_runup_20d": 0.125,
                }
            ],
        },
    }


_HFCL_COMPONENTS = {
    "volatility_adjusted_momentum": {"normalized": "1.0", "weighted": "0.20"},
    "relative_strength": {"normalized": "1.0", "weighted": "0.15"},
    "high_proximity": {"normalized": "0.992", "weighted": "0.149"},
    "consolidation_breakout": {"normalized": "0.031", "weighted": "0.003"},
}

_THERMAX_COMPONENTS = {
    "volatility_adjusted_momentum": {"normalized": "0.95", "weighted": "0.19"},
    "relative_strength": {"normalized": "0.92", "weighted": "0.14"},
    "high_proximity": {"normalized": "0.88", "weighted": "0.13"},
    "consolidation_breakout": {"normalized": "0.279", "weighted": "0.028"},
}


def test_sqe_schema_and_required_sections():
    payload = _breakout_bear_packet(
        symbol="HFCL.NS",
        rank=1,
        composite=0.8873,
        see_score=62.89,
        qualifying=97,
        win_rate=0.429,
        median_return=-0.037,
        score_components=_HFCL_COMPONENTS,
    )
    sqe = build_stock_quality_evidence(payload, "HFCL.NS")

    assert sqe["schema_version"] == SCHEMA_VERSION
    assert sqe["symbol"] == "HFCL.NS"
    for key in (
        "A_ranking_attribution",
        "B_factor_attribution",
        "C_regime_alignment",
        "D_historical_analog",
        "E_exit_profile",
        "F_validation_context",
        "strategy_context",
        "overall_stock_quality_score",
        "component_weights",
        "legacy_overall_quant_confidence",
    ):
        assert key in sqe
    assert sqe["A_ranking_attribution"]["evidence_ref"] == "ranking:score_components"
    assert sqe["F_validation_context"]["scope"] == "strategy"
    assert sqe["strategy_context"]["_from"] == "build_quant_research_brief"


def test_hfcl_vs_thermax_differentiation():
    hfcl = build_stock_quality_evidence(
        _breakout_bear_packet(
            symbol="HFCL.NS",
            rank=1,
            composite=0.8873,
            see_score=62.89,
            qualifying=97,
            win_rate=0.429,
            median_return=-0.037,
            score_components=_HFCL_COMPONENTS,
        ),
        "HFCL.NS",
    )
    thermax = build_stock_quality_evidence(
        _breakout_bear_packet(
            symbol="THERMAX.NS",
            rank=3,
            composite=0.886,
            see_score=59.88,
            qualifying=40,
            win_rate=0.40,
            median_return=-0.02,
            score_components=_THERMAX_COMPONENTS,
        ),
        "THERMAX.NS",
    )

    assert hfcl["overall_stock_quality_score"] != thermax["overall_stock_quality_score"]
    assert (
        hfcl["D_historical_analog"]["setup_evidence_score"]
        > thermax["D_historical_analog"]["setup_evidence_score"]
    )
    assert hfcl["A_ranking_attribution"]["rank"] == 1
    assert thermax["A_ranking_attribution"]["rank"] == 3


def test_wockpharma_beats_hfcl_on_stock_quality_despite_similar_rank():
    hfcl = build_stock_quality_evidence(
        _breakout_bear_packet(
            symbol="HFCL.NS",
            rank=1,
            composite=0.887,
            see_score=62.89,
            qualifying=97,
            win_rate=0.429,
            median_return=-0.037,
            score_components=_HFCL_COMPONENTS,
        ),
        "HFCL.NS",
    )
    wock = build_stock_quality_evidence(
        _breakout_bear_packet(
            symbol="WOCKPHARMA.NS",
            rank=2,
            composite=0.887,
            see_score=71.54,
            qualifying=110,
            win_rate=0.625,
            median_return=0.015,
            score_components=_HFCL_COMPONENTS,
        ),
        "WOCKPHARMA.NS",
    )

    assert wock["overall_stock_quality_score"] > hfcl["overall_stock_quality_score"]
    assert (
        wock["D_historical_analog"]["quality_score"] > hfcl["D_historical_analog"]["quality_score"]
    )


def test_triturbine_vs_thermax_see_ordering():
    triturbine = build_stock_quality_evidence(
        _breakout_bear_packet(
            symbol="TRITURBINE.NS",
            rank=12,
            composite=0.842,
            see_score=62.04,
            qualifying=50,
            win_rate=0.375,
            median_return=-0.01,
            score_components=_THERMAX_COMPONENTS,
        ),
        "TRITURBINE.NS",
    )
    thermax = build_stock_quality_evidence(
        _breakout_bear_packet(
            symbol="THERMAX.NS",
            rank=3,
            composite=0.886,
            see_score=59.88,
            qualifying=40,
            win_rate=0.40,
            median_return=-0.02,
            score_components=_THERMAX_COMPONENTS,
        ),
        "THERMAX.NS",
    )

    assert (
        triturbine["D_historical_analog"]["quality_score"]
        >= thermax["D_historical_analog"]["quality_score"]
    )


def test_pending_validation_neutral_in_section_f():
    sqe = build_stock_quality_evidence(
        _breakout_bear_packet(
            symbol="HFCL.NS",
            rank=1,
            composite=0.887,
            see_score=62.0,
            qualifying=50,
            win_rate=0.5,
            median_return=0.0,
            score_components=_HFCL_COMPONENTS,
        ),
        "HFCL.NS",
    )

    assert sqe["F_validation_context"]["pending_neutral"] is True
    assert sqe["F_validation_context"]["informational_score"] == 0.50
    assert sqe["F_validation_context"]["current_run_status"] == VALIDATION_STATUS_PENDING
