from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.args.committee_packet_views import build_qrc_view
from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_QRC
from app.workspace_args.models import InvestmentReviewPacket

_PLAIN_LANGUAGE = (
    "`findings` MUST be a single plain-English paragraph (a JSON string, NOT a nested object), readable by a "
    "non-specialist investor. Cover, in plain words: how the strategy validated historically, how clearly the "
    "return deciles separated, the rank-IC, the regime fit, and the stock-setup evidence — and interpret each "
    "number (say whether it is weak / moderate / strong) instead of only quoting it. Spell out every code and "
    "abbreviation on use: write regime labels in words (e.g. BEAR_LOW_VOL -> 'a bearish market with low "
    "volatility', BEAR_HIGH_VOL -> 'a bearish market with high volatility', BULL_LOW_VOL -> 'a bullish market "
    "with low volatility', BULL_HIGH_VOL -> 'a bullish market with high volatility'); write 'IC' as "
    "'Information Coefficient (how strongly the model's ranks predicted later returns; ~0 weak, 0.05-0.10 "
    "modest, above 0.10 strong)'; write 'rank-IC' as 'rank correlation with future returns'; write 'SEE' as "
    "'Stock Setup Evidence (a 0-100 score of how well the current setup matches historically profitable "
    "patterns)'. Do not emit raw enum codes or bare metrics without their plain-language meaning. "
)

_LEGACY_SYSTEM = (
    f"{COMMITTEE_QRC} quant research committee. "
    "Use ONLY the scoped payload: validation, historical_validation_context, factor_ic_summary, "
    "regime, stock_setup_evidence, stock_quality_evidence, quant_research_brief. "
    "NEVER repeat TARC technical factor storytelling, fundamentals, or news. "
    "Return strict JSON with keys: findings, strengths, risks, supporting_evidence, confidence, "
    "research_label, contrarian_view, validation_coverage, evidence_quality, regime_reliability, "
    "evidence_gaps, quant_summary. "
    + _PLAIN_LANGUAGE +
    "contrarian_view MUST challenge strong TARC ranks when validation/regime IC is weak. "
    "supporting_evidence refs: validation:*, quant_evidence:*, regime:*, stock_setup_evidence:*, "
    "historical_validation_context:* — include at least one quant/validation ref unique to QRC. "
    "Cite ONLY refs that literally appear in the provided payload (e.g. validation:status, "
    "validation:horizon:<h>, quant_evidence:factor_ic, stock_setup_evidence:setup_evidence_score); "
    "NEVER invent ids such as validation:<uuid> or validation:recent. "
    "When current-run validation is pending, treat as neutral. "
    "Never output recommendations, BUY/SELL/HOLD, position sizing, or stop-loss guidance."
)

_SQE_SYSTEM = (
    f"{COMMITTEE_QRC} quant research committee (SQE experiment). "
    "Use ONLY qrc_sqe_brief, stock_quality_evidence, validation summaries, factor_ic_summary, regime, SEE. "
    "NEVER repeat TARC technical narrative, fundamentals, or news. "
    "Return strict JSON with keys: findings, strengths, risks, supporting_evidence, confidence, "
    "research_label, contrarian_view, validation_coverage, evidence_quality, regime_reliability, "
    "evidence_gaps, quant_summary. "
    + _PLAIN_LANGUAGE +
    "Lead with stock-specific factor alignment and historical analog outcomes. "
    "contrarian_view must disagree with uncritical TARC rank enthusiasm when SQE/regime data is weak. "
    "supporting_evidence: validation:*, quant_evidence:*, regime:*, stock_setup_evidence:*. "
    "Never output recommendations, BUY/SELL/HOLD, position sizing, or stop-loss guidance."
)


class QrcCommitteePlugin:
    committee_code = COMMITTEE_QRC
    version = "1.0.0"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        user_payload = build_qrc_view(packet.payload, packet.symbol)
        sqe_mode = "qrc_sqe_brief" in user_payload
        evidence_mode = "sqe_experiment" if sqe_mode else "legacy"
        diagnostics = _build_qrc_diagnostics(user_payload, evidence_mode=evidence_mode)
        system = _SQE_SYSTEM if sqe_mode else _LEGACY_SYSTEM
        result = execute_committee_llm(
            packet=packet,
            llm=llm,
            committee_code=self.committee_code,
            committee_version=self.version,
            system=system,
            user_payload=user_payload,
        )
        ext = dict(result.output.extensions)
        ext.update(
            {
                "validation_coverage": diagnostics["validation_coverage"],
                "evidence_quality": diagnostics["evidence_quality"],
                "regime_reliability": diagnostics["regime_reliability"],
                "evidence_gaps": diagnostics["evidence_gaps"],
                "quant_summary": diagnostics["quant_summary"],
                "confidence_rubric": diagnostics["confidence_rubric"],
                "quant_research_brief": user_payload.get("quant_research_brief"),
                "qrc_evidence_mode": evidence_mode,
            }
        )
        if sqe_mode:
            ext["qrc_sqe_brief"] = user_payload.get("qrc_sqe_brief")
        output = replace(
            result.output,
            confidence=float(diagnostics["confidence_rubric"]["weighted_score"]),
            extensions=ext,
        )
        return replace(result, output=output)


def _build_qrc_diagnostics(
    user_payload: dict[str, Any],
    *,
    evidence_mode: str = "legacy",
) -> dict[str, Any]:
    coverage = user_payload.get("validation_coverage") or {}
    sample = user_payload.get("evidence_quality") or {}
    regime_rel = str(user_payload.get("regime_reliability") or "UNSUPPORTED").upper()
    gaps = list(user_payload.get("evidence_gaps") or [])

    if evidence_mode == "sqe_experiment":
        sqe_brief = user_payload.get("qrc_sqe_brief") or {}
        overall = float(
            sqe_brief.get("sqe_score") or user_payload.get("overall_stock_quality_score") or 0.5
        )
        legacy = sqe_brief.get("legacy_overall_quant_confidence")
        see = (sqe_brief.get("see_evidence") or {}).get("setup_evidence_score")
        return {
            "validation_coverage": coverage,
            "evidence_quality": sample,
            "regime_reliability": regime_rel,
            "evidence_gaps": gaps,
            "quant_summary": (
                f"SQE confidence {overall:.2f} (legacy brief {legacy}, "
                f"regime alignment {sqe_brief.get('regime_alignment_score')}, "
                f"SEE analog score {see}). "
                f"Coverage {coverage.get('coverage_pct')}%, regime reliability {regime_rel}."
            ),
            "confidence_rubric": {
                "mode": "sqe_experiment",
                "sqe_score": round(overall, 4),
                "legacy_overall_quant_confidence": legacy,
                "regime_alignment_score": sqe_brief.get("regime_alignment_score"),
                "weighted_score": round(overall, 2),
            },
        }

    brief = user_payload.get("quant_research_brief") or {}
    components = brief.get("component_scores") or {}
    overall = float(brief.get("overall_quant_confidence") or 0.5)

    return {
        "validation_coverage": coverage,
        "evidence_quality": sample,
        "regime_reliability": regime_rel,
        "evidence_gaps": gaps,
        "quant_summary": (
            f"Quant confidence {overall:.2f} (SEE {components.get('see', 'n/a')}, "
            f"historical {components.get('historical_strategy', 'n/a')}, "
            f"regime {components.get('regime_fit', 'n/a')}, factor {components.get('factor_quality', 'n/a')}). "
            f"Coverage {coverage.get('coverage_pct')}%, regime reliability {regime_rel}."
        ),
        "confidence_rubric": {
            "mode": "legacy",
            "see_score": components.get("see"),
            "historical_strategy_score": components.get("historical_strategy"),
            "regime_fit_score": components.get("regime_fit"),
            "factor_quality_score": components.get("factor_quality"),
            "validation_status_score": components.get("validation_status"),
            "weighted_score": round(overall, 2),
            "weights": brief.get("confidence_weights"),
        },
    }
