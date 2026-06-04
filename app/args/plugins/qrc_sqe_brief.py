"""Condensed SQE brief for QRC LLM prompts (Phase 3 experiment)."""

from __future__ import annotations

from typing import Any


def _factor_summary(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Strip raw IC / exposure from SQE B tailwind/headwind rows."""
    out: list[dict[str, Any]] = []
    for row in rows or []:
        factor = row.get("factor")
        signed = row.get("signed_contribution")
        if factor is None or signed is None:
            continue
        out.append({"factor": factor, "signed_contribution": signed})
    return out


def _see_summary(section_d: dict[str, Any]) -> dict[str, Any]:
    return {
        "setup_evidence_score": section_d.get("setup_evidence_score"),
        "quality_score": section_d.get("quality_score"),
        "qualifying_matches": section_d.get("qualifying_matches"),
        "sample_size": section_d.get("sample_size"),
        "win_rate_20d": section_d.get("win_rate_20d"),
        "median_return_20d": section_d.get("median_return_20d"),
        "regime_label": section_d.get("regime_label"),
        "evidence_ref": section_d.get("evidence_ref"),
    }


def build_qrc_sqe_brief(
    quant_research_brief: dict[str, Any],
    stock_quality_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Build LLM-facing SQE condensation from brief + packet SQE (no raw IC dumps)."""
    hist = quant_research_brief.get("historical_strategy_assessment") or {}
    regime_brief = quant_research_brief.get("current_regime_assessment") or {}

    section_b = stock_quality_evidence.get("B_factor_attribution") or {}
    section_c = stock_quality_evidence.get("C_regime_alignment") or {}
    section_d = stock_quality_evidence.get("D_historical_analog") or {}
    section_f = stock_quality_evidence.get("F_validation_context") or {}

    return {
        "strategy_quality": {
            "quality_score": hist.get("quality_score"),
            "quality_label": hist.get("quality_label"),
        },
        "current_regime": {
            "regime_label": (
                regime_brief.get("current_regime_label") or regime_brief.get("regime_label")
            ),
            "fit_score": regime_brief.get("fit_score"),
            "fit_label": regime_brief.get("fit_label"),
        },
        "regime_alignment_score": section_c.get("alignment_score"),
        "regime_alignment_label": section_c.get("alignment_label"),
        "top_positive_factors": _factor_summary(section_b.get("top_tailwinds")),
        "top_negative_factors": _factor_summary(section_b.get("top_headwinds")),
        "see_evidence": _see_summary(section_d),
        "sqe_score": stock_quality_evidence.get("overall_stock_quality_score"),
        "validation_status": {
            "scope": section_f.get("scope"),
            "pending_neutral": section_f.get("pending_neutral"),
            "informational_score": section_f.get("informational_score"),
            "current_run_status": section_f.get("current_run_status"),
            "historical_substitute_quality_label": (
                (section_f.get("historical_substitute") or {}).get("quality_label")
            ),
        },
        "legacy_overall_quant_confidence": stock_quality_evidence.get(
            "legacy_overall_quant_confidence"
        ),
    }
