from __future__ import annotations

from typing import Any


def score_packet_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    """Score packet evidence completeness 0-100 from populated sections."""
    weights = {
        "validation_current": 20,
        "validation_historical": 15,
        "factor_ic": 20,
        "factor_daily": 10,
        "regime_strategy": 10,
        "exit_research": 15,
        "research_intelligence": 10,
    }
    missing: list[str] = []
    components: dict[str, float] = {}

    validation = payload.get("validation") or {}
    if validation.get("status") == "completed" and validation.get("horizon_metrics"):
        components["validation_current"] = float(weights["validation_current"])
    else:
        missing.append("validation.horizon_metrics (current run)")

    historical = payload.get("historical_validation_context") or {}
    recent = historical.get("recent_completed_validations") or []
    if recent:
        components["validation_historical"] = float(weights["validation_historical"])
    else:
        missing.append("historical_validation_context")

    quant = payload.get("quant_evidence") or {}
    factor_ic = quant.get("factor_ic") or []
    if factor_ic:
        components["factor_ic"] = float(weights["factor_ic"])
    else:
        missing.append("quant_evidence.factor_ic")

    factor_daily = quant.get("factor_daily") or []
    if factor_daily:
        components["factor_daily"] = float(weights["factor_daily"])
    else:
        missing.append("quant_evidence.factor_daily")

    regime = payload.get("regime") or {}
    if regime.get("strategy_regime_performance"):
        components["regime_strategy"] = float(weights["regime_strategy"])
    else:
        missing.append("regime.strategy_regime_performance")

    if quant.get("exit_research"):
        components["exit_research"] = float(weights["exit_research"])
    else:
        missing.append("quant_evidence.exit_research")

    research = payload.get("research_context") or {}
    notes = research.get("notes") or []
    if notes:
        components["research_intelligence"] = float(weights["research_intelligence"])
    else:
        missing.append("research_context.notes")

    score = int(round(sum(components.values())))
    return {
        "score": min(100, max(0, score)),
        "max_score": 100,
        "components": {k: int(v) for k, v in components.items()},
        "missing": missing,
        "weight_map": weights,
    }


def derive_evidence_confidence(payload: dict[str, Any], coverage: dict[str, Any]) -> float:
    """Derive 0-1 confidence from evidence coverage and quality signals (not a static default)."""
    base = float(coverage.get("score", 0)) / 100.0

    validation = payload.get("validation") or {}
    if validation.get("status") == "completed":
        base += 0.05

    historical = payload.get("historical_validation_context") or {}
    if (historical.get("recent_completed_validations") or [])[:1]:
        base += 0.05

    quant = payload.get("quant_evidence") or {}
    factor_rows = quant.get("factor_ic") or []
    if factor_rows:
        avg_ic = _mean_abs_ic(factor_rows)
        if avg_ic is not None:
            base += min(0.1, avg_ic * 0.5)

    regime_rows = (payload.get("regime") or {}).get("strategy_regime_performance") or []
    if regime_rows:
        base += 0.05

    exit_rows = quant.get("exit_research") or []
    if exit_rows:
        base += 0.05

    research_notes = (payload.get("research_context") or {}).get("notes") or []
    if research_notes:
        base += 0.05

    return round(min(0.95, max(0.15, base)), 4)


def derive_governance_confidence(
    packet_payload: dict[str, Any],
    *,
    committee_confidences: list[float] | None = None,
) -> float:
    """Governance confidence from packet evidence + optional committee average."""
    coverage = packet_payload.get("evidence_coverage") or score_packet_evidence(packet_payload)
    evidence = float(
        packet_payload.get("evidence_confidence")
        or derive_evidence_confidence(packet_payload, coverage)
    )
    if not committee_confidences:
        return evidence
    committee_avg = sum(committee_confidences) / len(committee_confidences)
    return round(min(0.95, max(0.15, 0.6 * evidence + 0.4 * committee_avg)), 4)


def _mean_abs_ic(rows: list[dict[str, Any]]) -> float | None:
    values: list[float] = []
    for row in rows:
        ic = row.get("ic_spearman")
        if ic is None:
            continue
        try:
            values.append(abs(float(ic)))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    return sum(values) / len(values)
