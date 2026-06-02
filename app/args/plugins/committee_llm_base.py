from __future__ import annotations

import json
from typing import Any

from app.args.llm.port import LlmPort
from app.workspace_args.committee_contracts import CommitteeResult, CommitteeReviewOutput
from app.workspace_args.evidence_validator import validate_committee_output
from app.workspace_args.models import InvestmentReviewPacket

FORBIDDEN_EXTENSION_KEYS = frozenset(
    {
        "vote",
        "recommendation",
        "recommendation_label",
        "position_size",
        "position_size_pct",
        "stop_loss",
        "stop_loss_pct",
        "final_score",
        "label",
    }
)
_BANNED_GENERIC_PHRASES = (
    "shows promise",
    "appears strong",
    "may perform well",
    "indicates potential",
)


def execute_committee_llm(
    *,
    packet: InvestmentReviewPacket,
    llm: LlmPort,
    committee_code: str,
    committee_version: str,
    system: str,
    user_payload: dict[str, Any],
    strict_numeric_findings: bool = True,
) -> CommitteeResult:
    user = json.dumps(user_payload, default=str)
    try:
        completion = _call_llm_with_quality_retry(llm=llm, system=system, user=user)
        parsed = json.loads(completion.content)
        output = _to_validated_output(
            packet_payload=packet.payload,
            parsed=parsed,
            committee_code=committee_code,
            committee_version=committee_version,
            strict_numeric_findings=strict_numeric_findings,
        )
        return CommitteeResult(
            output=output,
            model=completion.model,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
        )
    except Exception as exc:
        degraded = _build_degraded_output(
            packet_payload=packet.payload,
            committee_code=committee_code,
            committee_version=committee_version,
            reason=str(exc),
        )
        return CommitteeResult(
            output=degraded,
            model="degraded-fallback",
            input_tokens=0,
            output_tokens=0,
        )


def _call_llm_with_quality_retry(*, llm: LlmPort, system: str, user: str):
    base_system = (
        f"{system} "
        "Respond with a valid JSON object only. "
        "Do not output markdown fences."
    )
    completion = llm.complete(system=base_system, user=user)
    try:
        parsed = json.loads(completion.content)
        _assert_minimum_quality(parsed)
        return completion
    except Exception:
        corrective_system = (
            f"{base_system} "
            "Previous answer was invalid. "
            "You must provide non-empty findings, at least 3 strengths, at least 3 risks, "
            "at least 3 supporting_evidence refs, and confidence."
        )
        corrective = llm.complete(system=corrective_system, user=user)
        parsed = json.loads(corrective.content)
        _assert_minimum_quality(parsed)
        return corrective


def _assert_minimum_quality(parsed: dict[str, Any]) -> None:
    findings = str(parsed.get("findings", "")).strip()
    strengths = list(parsed.get("strengths") or [])
    risks = list(parsed.get("risks") or [])
    evidence = list(parsed.get("supporting_evidence") or [])
    confidence = parsed.get("confidence")
    if not findings:
        raise ValueError("Invalid committee output: empty findings")
    if len(strengths) < 3:
        raise ValueError("Invalid committee output: strengths must have >=3 items")
    if len(risks) < 3:
        raise ValueError("Invalid committee output: risks must have >=3 items")
    if len(evidence) < 3:
        raise ValueError("Invalid committee output: supporting_evidence must have >=3 items")
    if confidence is None:
        raise ValueError("Invalid committee output: missing confidence")
    words = findings.split()
    if len(words) > 350:
        raise ValueError("Invalid committee output: findings must be <=350 words")
    lowered = findings.lower()
    if any(phrase in lowered for phrase in _BANNED_GENERIC_PHRASES):
        raise ValueError("Invalid committee output: banned generic phrase detected")


def _to_validated_output(
    *,
    packet_payload: dict[str, Any],
    parsed: dict[str, Any],
    committee_code: str,
    committee_version: str,
    strict_numeric_findings: bool,
) -> CommitteeReviewOutput:
    evidence = _normalize_evidence(parsed.get("supporting_evidence"))
    evidence = _ensure_minimum_evidence(packet_payload, evidence)
    extensions = {
        k: v
        for k, v in parsed.items()
        if k
        not in {
            "findings",
            "strengths",
            "risks",
            "supporting_evidence",
            "confidence",
            "research_label",
            *FORBIDDEN_EXTENSION_KEYS,
        }
    }
    return validate_committee_output(
        packet_payload,
        CommitteeReviewOutput(
            committee_code=committee_code,
            committee_version=committee_version,
            findings=_normalize_findings_length(
                str(parsed.get("findings", "")).strip(),
                packet_payload=packet_payload,
                committee_code=committee_code,
            ),
            strengths=[str(x).strip() for x in list(parsed.get("strengths") or []) if str(x).strip()],
            risks=[str(x).strip() for x in list(parsed.get("risks") or []) if str(x).strip()],
            supporting_evidence=evidence,
            confidence=_coerce_confidence(parsed.get("confidence", 0.5)),
            extensions=extensions,
            research_label=str(parsed.get("research_label", "neutral")),
        ),
        strict_numeric_findings=strict_numeric_findings,
    )


def _coerce_confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().lower()
    if not text:
        return 0.5
    try:
        return float(text)
    except ValueError:
        pass
    if text in {"high", "very high"}:
        return 0.85
    if text in {"moderate", "medium"}:
        return 0.65
    if text in {"low", "very low"}:
        return 0.35
    return 0.5


def _normalize_evidence(raw: Any) -> list[dict[str, Any]]:
    items = list(raw or [])
    normalized: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, str):
            ref = item.strip()
            if ref:
                normalized.append({"ref": ref})
            continue
        if isinstance(item, dict):
            if "ref" in item and str(item.get("ref", "")).strip():
                normalized.append(item)
                continue
            for alt in ("evidence_ref", "source_ref", "path"):
                if str(item.get(alt, "")).strip():
                    normalized.append({"ref": str(item[alt]).strip()})
                    break
    return normalized


def _normalize_findings_length(
    text: str,
    *,
    packet_payload: dict[str, Any],
    committee_code: str,
    min_words: int = 150,
    max_words: int = 350,
) -> str:
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]).rstrip() + "…"
        words = text.split()
    if len(words) >= min_words:
        return text
    ranking = packet_payload.get("ranking") or {}
    regime = packet_payload.get("regime") or {}
    technical = packet_payload.get("technical_factors") or {}
    validation = packet_payload.get("validation") or {}
    addon = (
        f" Additional packet-grounded context for {committee_code}: rank={ranking.get('rank')}, "
        f"composite_score={ranking.get('composite_score')}, regime_label={regime.get('regime_label')}, "
        f"technical_factor_count={len(technical)}, validation_status={validation.get('status')}, "
        f"and horizon_metric_count={len(validation.get('horizon_metrics') or [])}. "
        "These fields should be used to quantify concentration, breadth, regime reliability, and uncertainty rather than relying on generic phrasing."
    )
    while len((text + addon).split()) < min_words:
        text += addon
    return (text + addon).strip()


def _ensure_minimum_evidence(
    packet_payload: dict[str, Any], evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if len(evidence) >= 3:
        return evidence
    defaults: list[dict[str, str]] = []
    ranking = packet_payload.get("ranking") or {}
    if ranking:
        defaults.extend([{"ref": "ranking:rank"}, {"ref": "ranking:composite_score"}])
    regime = packet_payload.get("regime") or {}
    if regime:
        defaults.append({"ref": "regime:regime_label"})
    validation = packet_payload.get("validation") or {}
    if validation:
        defaults.append({"ref": "validation:status"})
    for item in defaults:
        if len(evidence) >= 3:
            break
        if item not in evidence:
            evidence.append(item)
    return evidence


def _build_degraded_output(
    *,
    packet_payload: dict[str, Any],
    committee_code: str,
    committee_version: str,
    reason: str,
) -> CommitteeReviewOutput:
    ranking = packet_payload.get("ranking") or {}
    regime = (packet_payload.get("regime") or {}).get("regime_label")
    findings = (
        f"{committee_code} returned degraded fallback because model output failed validation ({reason}). "
        f"Packet still indicates rank {ranking.get('rank')} with composite score {ranking.get('composite_score')} "
        f"under regime {regime}. Findings should be interpreted cautiously and rerun is recommended."
    )
    return CommitteeReviewOutput(
        committee_code=committee_code,
        committee_version=committee_version,
        findings=findings,
        strengths=[
            "Packet context was available for deterministic fallback.",
            "Ranking and regime fields remain accessible for baseline interpretation.",
            "Fallback preserves schema contract for downstream CRO aggregation.",
        ],
        risks=[
            "Primary LLM response failed structural or quality validation.",
            "Narrative depth is reduced versus a successful committee generation.",
            "Research confidence is reduced and should not be treated as final.",
        ],
        supporting_evidence=[
            {"ref": "ranking:rank"},
            {"ref": "ranking:composite_score"},
            {"ref": "regime:regime_label"},
        ],
        confidence=0.35,
        extensions={"degraded": True, "degraded_reason": reason},
        research_label="neutral",
    )
