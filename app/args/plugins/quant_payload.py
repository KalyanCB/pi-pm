"""Compact quant/validation summaries for QRC prompts (packet-grounded only)."""

from __future__ import annotations

from typing import Any


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize_exit_research(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Reduce hundreds of exit-policy rows to aggregate statistics for the LLM prompt."""
    if not rows:
        return {
            "row_count": 0,
            "note": "No exit_research metrics present in packet.",
        }

    parsed: list[dict[str, Any]] = []
    for row in rows:
        mean_return = _as_float(row.get("mean_return"))
        hit_rate = _as_float(row.get("hit_rate"))
        sample_size = int(row.get("sample_size") or 0)
        if mean_return is None and hit_rate is None:
            continue
        parsed.append(
            {
                "policy_family": row.get("policy_family"),
                "policy_variant": row.get("policy_variant"),
                "horizon": row.get("horizon"),
                "regime_label": row.get("regime_label"),
                "mean_return": mean_return,
                "hit_rate": hit_rate,
                "sample_size": sample_size,
                "metric_id": row.get("metric_id") or row.get("id"),
            }
        )

    if not parsed:
        return {"row_count": len(rows), "note": "Exit rows present but lacked numeric fields."}

    def _best(key: str) -> dict[str, Any]:
        return max(parsed, key=lambda r: r[key] if r[key] is not None else float("-inf"))

    def _worst(key: str) -> dict[str, Any]:
        return min(parsed, key=lambda r: r[key] if r[key] is not None else float("inf"))

    families = sorted({str(r.get("policy_family") or "unknown") for r in parsed})
    return {
        "row_count": len(rows),
        "policies_evaluated": len(parsed),
        "policy_families": families,
        "best_mean_return": _best("mean_return"),
        "worst_mean_return": _worst("mean_return"),
        "highest_hit_rate": _best("hit_rate"),
        "lowest_hit_rate": _worst("hit_rate"),
        "largest_sample": max(parsed, key=lambda r: r["sample_size"]),
        "smallest_sample": min(parsed, key=lambda r: r["sample_size"]),
        "evidence_ref_hint": "quant_evidence:exit_research",
    }


def summarize_validation(validation: dict[str, Any] | None) -> dict[str, Any]:
    if not validation:
        return {"status": None, "note": "No validation block in packet."}

    horizon_metrics = list(validation.get("horizon_metrics") or [])
    decile_metrics = list(validation.get("decile_metrics") or [])

    primary_horizon = None
    primary = None
    for metric in horizon_metrics:
        horizon = metric.get("horizon")
        sample_size = int(metric.get("sample_size") or 0)
        if sample_size <= 0:
            continue
        if primary is None or sample_size > int(primary.get("sample_size") or 0):
            primary = metric
            primary_horizon = horizon

    decile_summary: dict[str, Any] | None = None
    if primary_horizon is not None and decile_metrics:
        horizon_deciles = [
            d for d in decile_metrics if d.get("horizon") == primary_horizon
        ]
        if horizon_deciles:
            top = max(horizon_deciles, key=lambda d: d.get("decile", 0))
            bottom = min(horizon_deciles, key=lambda d: d.get("decile", 0))
            decile_summary = {
                "horizon": primary_horizon,
                "top_decile": top.get("decile"),
                "top_avg_return": _as_float(top.get("avg_return")),
                "bottom_decile": bottom.get("decile"),
                "bottom_avg_return": _as_float(bottom.get("avg_return")),
                "spread_estimate": (
                    (_as_float(top.get("avg_return")) or 0.0)
                    - (_as_float(bottom.get("avg_return")) or 0.0)
                ),
            }

    return {
        "status": validation.get("status"),
        "report_id": validation.get("report_id"),
        "regime_label": validation.get("regime_label"),
        "primary_horizon_metric": primary,
        "decile_summary": decile_summary,
        "horizons_with_data": [
            m.get("horizon")
            for m in horizon_metrics
            if int(m.get("sample_size") or 0) > 0
        ],
        "horizons_missing_data": [
            m.get("horizon")
            for m in horizon_metrics
            if int(m.get("sample_size") or 0) == 0
        ],
        "evidence_ref_hints": [
            ref
            for ref in (
                "validation:status",
                f"validation:horizon:{primary_horizon}" if primary_horizon is not None else None,
            )
            if ref
        ],
    }


def compute_validation_coverage(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload.get("validation") or {}
    quant = payload.get("quant_evidence") or {}
    regime = payload.get("regime") or {}

    checks = {
        "horizon_metrics": bool(validation.get("horizon_metrics")),
        "decile_metrics": bool(validation.get("decile_metrics")),
        "factor_ic": bool(quant.get("factor_ic")),
        "regime_metrics": bool(regime.get("strategy_regime_performance")),
        "exit_research": bool(quant.get("exit_research")),
    }
    covered = sum(1 for v in checks.values() if v)
    pct = round((covered / len(checks)) * 100.0, 1)
    return {"coverage_pct": pct, "covered_components": covered, "components": checks}


def compute_sample_quality(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload.get("validation") or {}
    quant = payload.get("quant_evidence") or {}
    samples: list[int] = []
    for row in list(validation.get("horizon_metrics") or []):
        samples.append(int(row.get("sample_size") or 0))
    for row in list(quant.get("exit_research") or []):
        samples.append(int(row.get("sample_size") or 0))
    samples = [s for s in samples if s > 0]
    if not samples:
        return {"label": "small", "avg_sample_size": 0, "max_sample_size": 0}
    avg_size = sum(samples) / len(samples)
    label = "large" if avg_size >= 1000 else ("medium" if avg_size >= 300 else "small")
    return {"label": label, "avg_sample_size": round(avg_size, 2), "max_sample_size": max(samples)}


def compute_regime_reliability(payload: dict[str, Any]) -> str:
    regime = payload.get("regime") or {}
    perf = list(regime.get("strategy_regime_performance") or [])
    validation = payload.get("validation") or {}
    has_regime_label = bool(validation.get("regime_label"))
    if len(perf) >= 4 and has_regime_label:
        return "HIGH"
    if len(perf) >= 2 and has_regime_label:
        return "MEDIUM"
    if len(perf) >= 1 or has_regime_label:
        return "LOW"
    return "UNSUPPORTED"


def detect_evidence_gaps(payload: dict[str, Any]) -> list[str]:
    validation = payload.get("validation") or {}
    quant = payload.get("quant_evidence") or {}
    regime = payload.get("regime") or {}
    gaps: list[str] = []
    if not validation.get("horizon_metrics"):
        gaps.append("No horizon metrics present.")
    if not validation.get("decile_metrics"):
        gaps.append("No decile metrics present.")
    if not quant.get("factor_ic"):
        gaps.append("No factor IC metrics present.")
    if not quant.get("exit_research"):
        gaps.append("No exit research metrics present.")
    if not regime.get("strategy_regime_performance"):
        gaps.append("No regime history/performance metrics present.")
    return gaps


def summarize_factor_ic(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"row_count": 0, "note": "No factor IC metrics in packet."}
    numeric = [
        {
            "factor_name": r.get("factor_name"),
            "ic": _as_float(r.get("ic") or r.get("ic_pearson") or r.get("rank_ic")),
            "horizon": r.get("horizon"),
            "regime_label": r.get("regime_label"),
            "id": r.get("id") or r.get("metric_id"),
        }
        for r in rows
        if _as_float(r.get("ic") or r.get("ic_pearson") or r.get("rank_ic")) is not None
    ]
    if not numeric:
        return {"row_count": len(rows), "note": "Factor rows present without IC values."}
    best = max(numeric, key=lambda r: r["ic"] or float("-inf"))
    worst = min(numeric, key=lambda r: r["ic"] or float("inf"))
    return {
        "row_count": len(rows),
        "best_ic": best,
        "worst_ic": worst,
        "evidence_ref_hint": "quant_evidence:factor_ic",
    }


def build_qrc_user_payload(packet_payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    quant = packet_payload.get("quant_evidence") or {}
    validation = packet_payload.get("validation") or {}
    coverage = compute_validation_coverage(packet_payload)
    sample_quality = compute_sample_quality(packet_payload)
    regime_reliability = compute_regime_reliability(packet_payload)
    gaps = detect_evidence_gaps(packet_payload)
    return {
        "symbol": symbol,
        "validation": validation,
        "validation_summary": summarize_validation(validation),
        "decile_metrics": validation.get("decile_metrics") or [],
        "horizon_metrics": validation.get("horizon_metrics") or [],
        "factor_ic_summary": summarize_factor_ic(list(quant.get("factor_ic") or [])),
        "exit_research_summary": summarize_exit_research(list(quant.get("exit_research") or [])),
        "regime": packet_payload.get("regime"),
        "validation_coverage": coverage,
        "evidence_quality": sample_quality,
        "regime_reliability": regime_reliability,
        "evidence_gaps": gaps,
        "instructions": (
            "Use validation_summary and exit_research_summary for aggregate interpretation. "
            "Cite evidence refs that exist in the original packet (validation:*, quant_evidence:*, regime:*)."
        ),
    }
