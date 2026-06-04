"""Unit tests for committee evidence scope enforcement (Phase 2)."""

from __future__ import annotations

import pytest

from app.args.committee_evidence_enforcement import (
    ref_matches_committee_allowlist,
    ref_unique_to_committee,
    validate_committee_evidence_scope,
)
from app.args.plugins.committee_llm_base import _assert_minimum_quality


def test_tarc_allowlist_accepts_technical_refs():
    assert ref_matches_committee_allowlist("technical_factors:volume_surge", "TARC")
    assert ref_matches_committee_allowlist("ranking:rank", "TARC")


def test_tarc_allowlist_rejects_validation_refs():
    assert not ref_matches_committee_allowlist("validation:status", "TARC")


def test_qrc_unique_ref_not_shared_with_tarc():
    assert ref_unique_to_committee("validation:status", "QRC")
    assert not ref_unique_to_committee("regime:regime_label", "QRC")


def test_validate_scope_requires_unique_ref():
    ok, reason = validate_committee_evidence_scope(
        "QRC",
        [
            {"ref": "regime:regime_label"},
            {"ref": "regime:regime_label"},
            {"ref": "regime:regime_label"},
        ],
    )
    assert not ok
    assert "unique" in reason.lower()


def test_validate_scope_passes_with_mandate_unique_ref():
    ok, reason = validate_committee_evidence_scope(
        "QRC",
        [
            {"ref": "validation:status"},
            {"ref": "quant_evidence:factor_ic"},
            {"ref": "regime:regime_label"},
        ],
    )
    assert ok
    assert reason == ""


def test_validate_scope_rejects_out_of_mandate_ref():
    ok, reason = validate_committee_evidence_scope(
        "NRCC",
        [
            {"ref": "news_snapshot:status"},
            {"ref": "ranking:rank"},
            {"ref": "news_snapshot:items"},
        ],
    )
    assert not ok
    assert "ranking:rank" in reason


def test_contrarian_view_required_in_parse():
    with pytest.raises(ValueError, match="contrarian_view"):
        _assert_minimum_quality(
            {
                "findings": "word " * 160,
                "strengths": ["a", "b", "c"],
                "risks": ["x", "y", "z"],
                "supporting_evidence": [{"ref": "a"}, {"ref": "b"}, {"ref": "c"}],
                "confidence": 0.5,
            },
            committee_code="TARC",
        )


def test_contrarian_view_accepts_valid_sentence():
    _assert_minimum_quality(
        {
            "findings": "word " * 160,
            "strengths": ["a", "b", "c"],
            "risks": ["x", "y", "z"],
            "supporting_evidence": [{"ref": "a"}, {"ref": "b"}, {"ref": "c"}],
            "confidence": 0.5,
            "contrarian_view": "QRC validation weakness challenges uncritical TARC rank enthusiasm today.",
        },
        committee_code="TARC",
    )
