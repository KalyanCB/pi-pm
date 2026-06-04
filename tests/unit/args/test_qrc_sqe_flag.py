"""QRC plugin respects ARGS_QRC_USE_SQE flag (legacy default)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.args.llm.port import MockLlmPort
from app.args.plugins.qrc import QrcCommitteePlugin
from app.args.plugins.stock_quality_evidence import build_stock_quality_evidence
from app.core.config import get_settings
from app.validation.constants import VALIDATION_STATUS_PENDING
from app.workspace_args.models import InvestmentReviewPacket


def _packet_payload(*, see_score: float) -> dict:
    base = {
        "validation": {
            "status": VALIDATION_STATUS_PENDING,
            "regime_label": "BEAR_LOW_VOL",
        },
        "historical_validation_context": {
            "recent_completed_validations": [
                {
                    "as_of_date": "2026-05-11",
                    "horizon_metrics": [{"horizon": 5, "sample_size": 300, "rank_ic_spearman": 0.1}],
                    "decile_metrics": [{"horizon": 5, "decile": 10, "avg_return": 0.02}],
                }
            ],
        },
        "quant_evidence": {
            "factor_ic": [{"factor_name": "momentum", "ic_spearman": 0.05}],
            "exit_research": [{"hit_rate": 0.5, "sample_size": 200, "mean_return": 0.01}],
        },
        "regime": {
            "strategy_regime_performance": [
                {"regime_label": "BEAR_LOW_VOL", "avg_ic": 0.02, "sample_count": 10, "is_current_regime": True}
            ]
        },
        "ranking": {
            "rank": 1,
            "score_components": {
                "momentum": {"normalized": "0.9", "weighted": "0.18"},
            },
        },
        "stock_setup_evidence": {
            "status": "completed",
            "setup_evidence_score": see_score,
            "qualifying_matches": 10,
            "regime_statistics": [
                {"regime_label": "BEAR_LOW_VOL", "win_rate_20d": 0.55, "sample_size": 10}
            ],
        },
    }
    base["stock_quality_evidence"] = build_stock_quality_evidence(base, "HFCL.NS")
    return base


def _review_packet(payload: dict) -> InvestmentReviewPacket:
    return InvestmentReviewPacket(
        symbol="HFCL.NS",
        stock_id=uuid4(),
        ranking_run_id=uuid4(),
        ranking_result_id=uuid4(),
        payload=payload,
        packet_hash="test-hash",
    )


@pytest.fixture
def sqe_flag_on(monkeypatch):
    monkeypatch.setenv("ARGS_QRC_USE_SQE", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("ARGS_QRC_USE_SQE", raising=False)
    get_settings.cache_clear()


def test_qrc_plugin_legacy_mode_when_flag_false(monkeypatch):
    monkeypatch.delenv("ARGS_QRC_USE_SQE", raising=False)
    get_settings.cache_clear()
    assert get_settings().args_qrc_use_sqe is False

    plugin = QrcCommitteePlugin()
    result = plugin.execute(_review_packet(_packet_payload(see_score=70)), MockLlmPort())

    assert result.output.extensions["qrc_evidence_mode"] == "legacy"
    assert "qrc_sqe_brief" not in result.output.extensions
    assert result.output.extensions["confidence_rubric"]["mode"] == "legacy"
    assert result.output.confidence == pytest.approx(
        result.output.extensions["quant_research_brief"]["overall_quant_confidence"],
        rel=0,
        abs=0.01,
    )


def test_qrc_plugin_sqe_mode_when_flag_true(sqe_flag_on):
    plugin = QrcCommitteePlugin()
    payload = _packet_payload(see_score=70)
    sqe_score = payload["stock_quality_evidence"]["overall_stock_quality_score"]

    result = plugin.execute(_review_packet(payload), MockLlmPort())

    assert result.output.extensions["qrc_evidence_mode"] == "sqe_experiment"
    assert "qrc_sqe_brief" in result.output.extensions
    assert result.output.extensions["confidence_rubric"]["mode"] == "sqe_experiment"
    assert result.output.confidence == pytest.approx(sqe_score, rel=0, abs=0.01)
