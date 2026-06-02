from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.args.plugins.quant_payload import build_qrc_user_payload
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_QRC
from app.workspace_args.models import InvestmentReviewPacket


class QrcCommitteePlugin:
    committee_code = COMMITTEE_QRC
    version = "1.0.0"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        user_payload = build_qrc_user_payload(packet.payload, packet.symbol)
        diagnostics = _build_qrc_diagnostics(user_payload)
        system = (
            f"{COMMITTEE_QRC} quant research committee. "
            "Use only packet validation, decile metrics, horizon metrics, factor_ic summary, "
            "exit_research summary, and regime. "
            "Return strict JSON with keys: findings, strengths, risks, supporting_evidence, confidence, research_label, "
            "validation_coverage, evidence_quality, regime_reliability, evidence_gaps, quant_summary. "
            "findings must be 150-350 words and explain: validation quality, sample sizes, decile separation, "
            "rank-IC quality, missing data horizons, regime confidence, and exit policy observations. "
            "strengths must contain at least 3 concrete bullet strings. "
            "risks must contain at least 3 concrete bullet strings. "
            "supporting_evidence must contain at least 3 objects with packet-grounded refs "
            "(validation:*, quant_evidence:*, regime:*). "
            "For missing evidence, produce structured evidence_gaps and impact statements, not generic 'insufficient data'. "
            "Set confidence using rubric: validation_coverage 35%, sample_quality 25%, regime_reliability 20%, exit_research_quality 20%. "
            "Never use external facts. Never invent numbers. "
            "Never output recommendations, BUY/SELL/HOLD, position sizing, or stop-loss guidance. "
            "Do not leave findings/arrays empty."
        )
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
            }
        )
        output = replace(
            result.output,
            confidence=float(diagnostics["confidence_rubric"]["weighted_score"]),
            extensions=ext,
        )
        return replace(result, output=output)


def _build_qrc_diagnostics(user_payload: dict[str, Any]) -> dict[str, Any]:
    coverage = user_payload.get("validation_coverage") or {}
    sample = user_payload.get("evidence_quality") or {}
    regime_rel = str(user_payload.get("regime_reliability") or "UNSUPPORTED").upper()
    gaps = list(user_payload.get("evidence_gaps") or [])
    exit_summary = user_payload.get("exit_research_summary") or {}

    coverage_score = _clamp(float(coverage.get("coverage_pct") or 0.0) / 100.0, 0.0, 1.0)
    sample_label = str(sample.get("label") or "small").lower()
    sample_score = 0.90 if sample_label == "large" else (0.65 if sample_label == "medium" else 0.35)
    regime_score = {"HIGH": 0.90, "MEDIUM": 0.65, "LOW": 0.45, "UNSUPPORTED": 0.25}.get(regime_rel, 0.35)
    exit_quality = 0.25
    if int(exit_summary.get("policies_evaluated") or 0) >= 10:
        exit_quality = 0.85
    elif int(exit_summary.get("policies_evaluated") or 0) >= 4:
        exit_quality = 0.65
    elif int(exit_summary.get("policies_evaluated") or 0) >= 1:
        exit_quality = 0.45

    weighted = round(
        coverage_score * 0.35 + sample_score * 0.25 + regime_score * 0.20 + exit_quality * 0.20,
        2,
    )
    return {
        "validation_coverage": coverage,
        "evidence_quality": sample,
        "regime_reliability": regime_rel,
        "evidence_gaps": gaps,
        "quant_summary": (
            f"Coverage {coverage.get('coverage_pct')}%, sample quality {sample_label}, "
            f"regime reliability {regime_rel}, policies evaluated {exit_summary.get('policies_evaluated', 0)}."
        ),
        "confidence_rubric": {
            "validation_coverage_score": round(coverage_score, 4),
            "sample_quality_score": round(sample_score, 4),
            "regime_reliability_score": round(regime_score, 4),
            "exit_research_quality_score": round(exit_quality, 4),
            "weighted_score": weighted,
        },
    }


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
