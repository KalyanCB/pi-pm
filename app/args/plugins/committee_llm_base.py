from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.args.committee_evidence_enforcement import (
    build_evidence_repair_prompt,
    build_evidence_validation_failed_output,
    validate_committee_evidence_scope,
)
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

_CONTRARIAN_EXAMPLES: dict[str, str] = {
    "TARC": (
        "Example contrarian_view: 'QRC may cite negative regime IC — rank overstates edge if validation is weak.'"
    ),
    "QRC": (
        "Example contrarian_view: 'TARC rank 2 overstates edge given negative BEAR_LOW_VOL regime IC.'"
    ),
    "FRC": (
        "Example contrarian_view: 'Technical rank strength is unconfirmed without fundamental evidence.'"
    ),
    "NRCC": (
        "Example contrarian_view: 'Constructive quant signals lack corroborating news catalysts.'"
    ),
    "RC": (
        "Example contrarian_view: 'High technical rank ignores elevated drawdown/liquidity risk stack.'"
    ),
}


def execute_committee_llm(
    *,
    packet: InvestmentReviewPacket,
    llm: LlmPort,
    committee_code: str,
    committee_version: str,
    system: str,
    user_payload: dict[str, Any],
    strict_numeric_findings: bool = True,
    enforce_evidence_scope: bool = True,
    abstention_builder: Callable[[], CommitteeReviewOutput] | None = None,
) -> CommitteeResult:
    user = json.dumps(user_payload, default=str)
    contrarian_hint = _CONTRARIAN_EXAMPLES.get(committee_code, "")
    scoped_system = (
        f"{system} Required JSON field contrarian_view: at least one sentence explicitly "
        f"disagreeing with another committee's likely conclusion. {contrarian_hint}"
    )
    try:
        completion = _call_llm_with_quality_retry(
            llm=llm,
            system=scoped_system,
            user=user,
            committee_code=committee_code,
            enforce_evidence_scope=enforce_evidence_scope,
        )
        parsed = json.loads(completion.content)
        output = _to_validated_output(
            packet_payload=packet.payload,
            parsed=parsed,
            committee_code=committee_code,
            committee_version=committee_version,
            strict_numeric_findings=strict_numeric_findings,
            enforce_evidence_scope=enforce_evidence_scope,
        )
        return CommitteeResult(
            output=output,
            model=completion.model,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
        )
    except Exception as exc:
        if abstention_builder is not None:
            return CommitteeResult(
                output=abstention_builder(),
                model=f"{committee_code.lower()}-abstention",
                input_tokens=0,
                output_tokens=0,
            )
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


def _call_llm_with_quality_retry(
    *,
    llm: LlmPort,
    system: str,
    user: str,
    committee_code: str,
    enforce_evidence_scope: bool,
):
    base_system = f"{system} Respond with a valid JSON object only. Do not output markdown fences."
    completion = llm.complete(system=base_system, user=user)
    try:
        parsed = json.loads(completion.content)
        _assert_minimum_quality(parsed, committee_code=committee_code)
        if enforce_evidence_scope:
            ok, reason = validate_committee_evidence_scope(
                committee_code, list(parsed.get("supporting_evidence") or [])
            )
            if not ok:
                raise ValueError(f"evidence scope: {reason}")
        return completion
    except Exception as first_exc:
        corrective_system = (
            f"{base_system} "
            "Previous answer was invalid. "
            "You must provide non-empty findings, at least 3 strengths, at least 3 risks, "
            "at least 3 supporting_evidence refs within your committee mandate, "
            "contrarian_view (min 1 sentence), and confidence. "
            f"{build_evidence_repair_prompt(str(first_exc))}"
        )
        corrective = llm.complete(system=corrective_system, user=user)
        parsed = json.loads(corrective.content)
        _assert_minimum_quality(parsed, committee_code=committee_code)
        if enforce_evidence_scope:
            ok, reason = validate_committee_evidence_scope(
                committee_code, list(parsed.get("supporting_evidence") or [])
            )
            if not ok:
                raise ValueError(f"evidence scope after retry: {reason}")
        return corrective


def _assert_minimum_quality(parsed: dict[str, Any], *, committee_code: str) -> None:
    findings = str(parsed.get("findings", "")).strip()
    strengths = list(parsed.get("strengths") or [])
    risks = list(parsed.get("risks") or [])
    evidence = list(parsed.get("supporting_evidence") or [])
    confidence = parsed.get("confidence")
    contrarian = str(parsed.get("contrarian_view", "")).strip()
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
    if not contrarian or len(contrarian.split()) < 5:
        raise ValueError("Invalid committee output: contrarian_view must be at least one sentence")
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
    enforce_evidence_scope: bool,
) -> CommitteeReviewOutput:
    evidence = _normalize_evidence(parsed.get("supporting_evidence"))
    evidence = _ensure_minimum_evidence(packet_payload, evidence, committee_code=committee_code)
    if enforce_evidence_scope:
        ok, reason = validate_committee_evidence_scope(committee_code, evidence)
        if not ok:
            symbol = str(packet_payload.get("symbol") or "")
            return build_evidence_validation_failed_output(
                committee_code=committee_code,
                committee_version=committee_version,
                symbol=symbol,
                reason=reason,
            )

    contrarian_view = str(parsed.get("contrarian_view", "")).strip()
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
            "contrarian_view",
            *FORBIDDEN_EXTENSION_KEYS,
        }
    }
    extensions["contrarian_view"] = contrarian_view
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
            strengths=[
                str(x).strip() for x in list(parsed.get("strengths") or []) if str(x).strip()
            ],
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
    if committee_code == "TARC":
        addon = (
            f" Additional packet-grounded context for {committee_code}: rank={ranking.get('rank')}, "
            f"composite_score={ranking.get('composite_score')}, regime_label={regime.get('regime_label')}, "
            f"technical_factor_count={len(technical)}. "
            "Quantify signal breadth and concentration rather than generic phrasing."
        )
    elif committee_code == "QRC":
        addon = (
            f" Additional validation context for {committee_code}: validation_status={validation.get('status')}, "
            f"regime_label={regime.get('regime_label')}, "
            f"horizon_metric_count={len(validation.get('horizon_metrics') or [])}. "
            "Frame historical IC, decile separation, and regime fit — not technical factor storytelling."
        )
    else:
        addon = (
            f" Additional scoped context for {committee_code} on symbol {packet_payload.get('symbol')}. "
            "Stay within committee mandate; do not import ranking/regime filler when evidence is insufficient."
        )
    while len((text + addon).split()) < min_words:
        text += addon
    return (text + addon).strip()


def _ensure_minimum_evidence(
    packet_payload: dict[str, Any],
    evidence: list[dict[str, Any]],
    *,
    committee_code: str,
) -> list[dict[str, Any]]:
    if len(evidence) >= 3:
        return evidence
    defaults: list[dict[str, str]] = []
    if committee_code == "TARC":
        ranking = packet_payload.get("ranking") or {}
        if ranking:
            defaults.extend([{"ref": "ranking:rank"}, {"ref": "ranking:composite_score"}])
        technical = packet_payload.get("technical_factors") or {}
        for name in list(technical.keys())[:2]:
            defaults.append({"ref": f"technical_factors:{name}"})
        regime = packet_payload.get("regime") or {}
        if regime.get("regime_label"):
            defaults.append({"ref": "regime:regime_label"})
    elif committee_code == "QRC":
        validation = packet_payload.get("validation") or {}
        if validation:
            defaults.append({"ref": "validation:status"})
            horizons = validation.get("horizon_metrics") or []
            if horizons:
                h = horizons[0].get("horizon")
                if h is not None:
                    defaults.append({"ref": f"validation:horizon:{h}"})
        quant = packet_payload.get("quant_evidence") or {}
        if quant.get("factor_ic"):
            defaults.append({"ref": "quant_evidence:factor_ic"})
        regime = packet_payload.get("regime") or {}
        if regime.get("regime_label"):
            defaults.append({"ref": "regime:regime_label"})
    elif committee_code == "NRCC":
        defaults.append({"ref": "news_snapshot:status"})
    elif committee_code == "FRC":
        defaults.append({"ref": "fundamental_snapshot:status"})
    elif committee_code == "RC":
        market = packet_payload.get("market_snapshot") or {}
        if market:
            for key in ("sector", "avg_volume", "market_cap"):
                if key in market:
                    defaults.append({"ref": f"market_snapshot:{key}"})
                    break
        portfolio = packet_payload.get("portfolio_context") or {}
        if portfolio:
            defaults.append({"ref": "portfolio_context:existing_position"})
        see = packet_payload.get("stock_setup_evidence") or {}
        if see:
            defaults.append({"ref": "stock_setup_evidence:setup_evidence_score"})
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
    symbol = str(packet_payload.get("symbol") or "")
    return build_evidence_validation_failed_output(
        committee_code=committee_code,
        committee_version=committee_version,
        symbol=symbol,
        reason=f"LLM validation failed: {reason}",
    )
