from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.args.llm.port import LlmPort
from app.args.plugins.committee_llm_base import execute_committee_llm
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.constants import COMMITTEE_TARC
from app.workspace_args.models import InvestmentReviewPacket


class TarcCommitteePlugin:
    committee_code = COMMITTEE_TARC
    version = "1.0.0"

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult:
        diagnostics = _build_tarc_diagnostics(packet.payload)
        system = (
            f"{COMMITTEE_TARC} technical research committee. "
            "Interpret only ranking factors, score components, regime, technical_factors, and historical_performance. "
            "Return strict JSON with keys: findings, strengths, risks, supporting_evidence, confidence, research_label, "
            "signal_quality, signal_breadth, regime_alignment, technical_summary. "
            "findings must be 150-350 words and must explain: why rank is high/low, strongest factors, weakest factors, "
            "whether signal is balanced vs concentrated, and regime implications. "
            "strengths must contain at least 3 concrete bullet strings. "
            "risks must contain at least 3 concrete bullet strings. "
            "supporting_evidence must contain at least 3 objects each with a packet-grounded ref like "
            "ranking:rank, ranking:composite_score, technical_factors:<factor>, regime:regime_label, historical_performance:return_5d. "
            "Use diagnostics to classify signal_breadth as STRONG_BREADTH, MEDIUM_BREADTH, or NARROW_SIGNAL. "
            "Use diagnostics to classify regime_alignment as HIGH, MODERATE, or UNSUPPORTED. "
            "Set confidence from 0-1 using rubric: signal_quality 30%, breadth 25%, regime_alignment 25%, risk_profile 20%. "
            "Never use external data. Never speculate beyond packet fields. "
            "Never output investment recommendations, BUY/SELL/HOLD, position sizing, or stop-loss guidance. "
            "Do not leave findings/arrays empty."
        )
        result = execute_committee_llm(
            packet=packet,
            llm=llm,
            committee_code=self.committee_code,
            committee_version=self.version,
            system=system,
            user_payload={
                "symbol": packet.symbol,
                "ranking": packet.payload.get("ranking"),
                "technical_factors": packet.payload.get("technical_factors"),
                "regime": packet.payload.get("regime"),
                "historical_performance": packet.payload.get("historical_performance"),
                "diagnostics": diagnostics,
                "output_requirements": {
                    "findings_word_range": "150-350",
                    "min_strengths": 3,
                    "min_risks": 3,
                    "min_supporting_evidence": 3,
                    "evidence_ref_examples": [
                        "ranking:rank",
                        "ranking:composite_score",
                        "technical_factors:trend_quality",
                        "regime:regime_label",
                        "historical_performance:return_5d",
                    ],
                },
            },
        )
        score = diagnostics["confidence_rubric"]["weighted_score"]
        ext = dict(result.output.extensions)
        ext.update(
            {
                "signal_quality": diagnostics["signal_quality"],
                "signal_breadth": diagnostics["signal_breadth"],
                "regime_alignment": diagnostics["regime_alignment"],
                "technical_summary": diagnostics["technical_summary"],
                "breadth_metrics": diagnostics["breadth_metrics"],
                "confidence_rubric": diagnostics["confidence_rubric"],
            }
        )
        output = replace(
            result.output,
            confidence=float(score),
            extensions=ext,
        )
        return replace(result, output=output)


def _build_tarc_diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    ranking = payload.get("ranking") or {}
    technical = payload.get("technical_factors") or {}
    regime = payload.get("regime") or {}
    historical = payload.get("historical_performance") or {}

    normalized_values: list[tuple[str, float]] = []
    weak_factors: list[str] = []
    for name, item in technical.items():
        value = _extract_normalized(item)
        if value is None:
            continue
        normalized_values.append((name, value))
        if value < 0.30:
            weak_factors.append(name)

    above_08 = sum(1 for _, v in normalized_values if v >= 0.80)
    above_06 = sum(1 for _, v in normalized_values if v >= 0.60)
    below_03 = sum(1 for _, v in normalized_values if v < 0.30)
    breadth = "STRONG_BREADTH" if above_08 >= 4 else ("MEDIUM_BREADTH" if above_06 >= 4 else "NARROW_SIGNAL")

    concentration = 1.0
    if normalized_values:
        vals = sorted((v for _, v in normalized_values), reverse=True)
        total = sum(vals) or 1.0
        concentration = min(1.0, (sum(vals[:2]) / total))

    regime_perf = list(regime.get("strategy_regime_performance") or [])
    regime_alignment = "HIGH" if len(regime_perf) >= 3 else ("MODERATE" if len(regime_perf) >= 1 else "UNSUPPORTED")

    composite = float(ranking.get("composite_score") or 0.0)
    signal_quality_score = _clamp((composite / 1.0), 0.0, 1.0)
    breadth_score = 0.90 if breadth == "STRONG_BREADTH" else (0.65 if breadth == "MEDIUM_BREADTH" else 0.40)
    regime_score = 0.90 if regime_alignment == "HIGH" else (0.65 if regime_alignment == "MODERATE" else 0.35)
    risk_score = _clamp(1.0 - (0.5 * concentration + 0.1 * below_03), 0.25, 0.95)
    weighted = round(
        signal_quality_score * 0.30 + breadth_score * 0.25 + regime_score * 0.25 + risk_score * 0.20,
        2,
    )

    summary = (
        f"Rank {ranking.get('rank')} with composite score {composite:.4f}; "
        f"breadth {breadth} (>=0.8: {above_08}, >=0.6: {above_06}, <0.3: {below_03}), "
        f"regime alignment {regime_alignment}, concentration ratio {concentration:.2f}. "
        f"Weak factors: {', '.join(weak_factors) if weak_factors else 'none'}; "
        f"historical return_5d={historical.get('return_5d')}."
    )
    return {
        "signal_quality": "HIGH" if signal_quality_score >= 0.8 else ("MEDIUM" if signal_quality_score >= 0.6 else "LOW"),
        "signal_breadth": breadth,
        "regime_alignment": regime_alignment,
        "technical_summary": summary,
        "breadth_metrics": {
            "factors_above_0_8": above_08,
            "factors_above_0_6": above_06,
            "factors_below_0_3": below_03,
            "concentration_ratio_top2": round(concentration, 4),
        },
        "confidence_rubric": {
            "signal_quality_score": round(signal_quality_score, 4),
            "breadth_score": round(breadth_score, 4),
            "regime_alignment_score": round(regime_score, 4),
            "risk_profile_score": round(risk_score, 4),
            "weighted_score": weighted,
        },
    }


def _extract_normalized(item: Any) -> float | None:
    if isinstance(item, dict):
        for key in ("normalized", "score", "value"):
            if key in item:
                return _to_float(item.get(key))
    return _to_float(item)


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
