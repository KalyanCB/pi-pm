"""Compact quant/validation summaries for QRC prompts (packet-grounded only)."""

from __future__ import annotations

from typing import Any

from app.args.plugins.qrc_sqe_brief import build_qrc_sqe_brief
from app.args.plugins.quant_research_brief import build_quant_research_brief
from app.args.validation_status import (
    is_current_validation_pending,
    latest_historical_validation_block,
)
from app.core.config import get_settings


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _see_evidence_available(payload: dict[str, Any]) -> bool:
    see = payload.get("stock_setup_evidence") or {}
    status = str(see.get("status") or "").lower()
    if status in ("completed", "ok"):
        return True
    if int(see.get("qualifying_matches") or see.get("total_matches") or 0) > 0:
        return True
    if see.get("setup_evidence_score") is not None:
        return True
    return False


def _summarize_see(payload: dict[str, Any]) -> dict[str, Any]:
    see = payload.get("stock_setup_evidence") or {}
    if not _see_evidence_available(payload):
        return {"status": see.get("status") or "unavailable", "note": "No SEE evidence in packet."}
    return {
        "status": see.get("status"),
        "research_id": see.get("research_id"),
        "setup_evidence_score": see.get("setup_evidence_score"),
        "qualifying_matches": see.get("qualifying_matches"),
        "total_matches": see.get("total_matches"),
        "regime_label": see.get("regime_label"),
        "evidence_ref_hint": "stock_setup_evidence",
    }


def _validation_for_quant_assessment(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Current validation block plus optional historical substitute when run is pending."""
    validation = dict(payload.get("validation") or {})
    historical: dict[str, Any] | None = None
    if is_current_validation_pending(validation):
        historical = latest_historical_validation_block(payload)
        if historical:
            validation = {
                **validation,
                "current_run_status": validation.get("status"),
                "historical_substitute": historical,
            }
    return validation, historical


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


def summarize_validation(
    validation: dict[str, Any] | None,
    *,
    historical: dict[str, Any] | None = None,
    pending_current: bool = False,
) -> dict[str, Any]:
    if not validation and not historical:
        return {"status": None, "note": "No validation block in packet."}

    horizon_metrics = list(validation.get("horizon_metrics") or []) if validation else []
    decile_metrics = list(validation.get("decile_metrics") or []) if validation else []
    status = validation.get("status") if validation else None
    regime_label = validation.get("regime_label") if validation else None
    report_id = validation.get("report_id") if validation else None

    if pending_current and historical:
        horizon_metrics = horizon_metrics or list(historical.get("horizon_metrics") or [])
        decile_metrics = decile_metrics or list(historical.get("decile_metrics") or [])
        status = validation.get("current_run_status") or status
        regime_label = regime_label or historical.get("regime_label")
        report_id = report_id or historical.get("report_id")

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
        horizon_deciles = [d for d in decile_metrics if d.get("horizon") == primary_horizon]
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

    out: dict[str, Any] = {
        "status": status,
        "report_id": report_id,
        "regime_label": regime_label,
        "primary_horizon_metric": primary,
        "decile_summary": decile_summary,
        "horizons_with_data": [
            m.get("horizon") for m in horizon_metrics if int(m.get("sample_size") or 0) > 0
        ],
        "horizons_missing_data": [
            m.get("horizon") for m in horizon_metrics if int(m.get("sample_size") or 0) == 0
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
    if pending_current:
        out["current_run_validation"] = "pending_neutral"
        if historical:
            out["historical_validation_as_of"] = historical.get("as_of_date")
            out["historical_validation_source"] = historical.get("source")
    return out


def compute_validation_coverage(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload.get("validation") or {}
    quant = payload.get("quant_evidence") or {}
    regime = payload.get("regime") or {}
    pending = is_current_validation_pending(validation)
    historical = latest_historical_validation_block(payload) if pending else {}

    horizon_ok = bool(validation.get("horizon_metrics")) or bool(historical.get("horizon_metrics"))
    decile_ok = bool(validation.get("decile_metrics")) or bool(historical.get("decile_metrics"))

    checks = {
        "horizon_metrics": horizon_ok,
        "decile_metrics": decile_ok,
        "factor_ic": bool(quant.get("factor_ic")),
        "regime_metrics": bool(regime.get("strategy_regime_performance")),
        "exit_research": bool(quant.get("exit_research")),
        "see_evidence": _see_evidence_available(payload),
        "current_validation_pending_neutral": pending,
    }
    covered = sum(
        1 for key, value in checks.items() if value and key != "current_validation_pending_neutral"
    )
    scorable = len(checks) - 1
    pct = round((covered / scorable) * 100.0, 1) if scorable else 0.0
    return {
        "coverage_pct": pct,
        "covered_components": covered,
        "components": checks,
        "uses_historical_validation": bool(historical) and pending,
    }


def compute_sample_quality(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload.get("validation") or {}
    quant = payload.get("quant_evidence") or {}
    samples: list[int] = []

    horizon_sources: list[dict[str, Any]] = list(validation.get("horizon_metrics") or [])
    if is_current_validation_pending(validation):
        historical = latest_historical_validation_block(payload)
        if historical:
            horizon_sources = horizon_sources or list(historical.get("horizon_metrics") or [])

    for row in horizon_sources:
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
    if not has_regime_label and is_current_validation_pending(validation):
        historical = latest_historical_validation_block(payload)
        has_regime_label = bool(historical.get("regime_label"))
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
    pending = is_current_validation_pending(validation)
    historical = latest_historical_validation_block(payload) if pending else {}
    gaps: list[str] = []

    if pending:
        gaps.append("Current-run forward validation is pending (neutral; not a negative signal).")
    if not validation.get("horizon_metrics") and not historical.get("horizon_metrics"):
        gaps.append("No horizon metrics present (current or historical).")
    if not validation.get("decile_metrics") and not historical.get("decile_metrics"):
        gaps.append("No decile metrics present (current or historical).")
    if not quant.get("factor_ic"):
        gaps.append("No factor IC metrics present.")
    if not quant.get("exit_research"):
        gaps.append("No exit research metrics present.")
    if not regime.get("strategy_regime_performance"):
        gaps.append("No regime history/performance metrics present.")
    if not _see_evidence_available(payload):
        gaps.append("No stock setup (SEE) evidence present.")
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


_SQE_INSTRUCTIONS = (
    "Primary evidence: qrc_sqe_brief (stock-level Stock Quality Evidence). "
    "Lead with stock-specific ranking attribution, factor alignment (top_positive_factors / "
    "top_negative_factors), regime fit (regime_alignment_score), and historical analog "
    "(see_evidence). strategy_quality is the shared strategy prior. "
    "validation_status is informational only; pending current-run validation is neutral. "
    "Align confidence with qrc_sqe_brief.sqe_score (overall_stock_quality_score). "
    "quant_research_brief is secondary cross-check only. "
    "Use exit_research_summary for exit-policy context. "
    "Cite evidence refs from qrc_sqe_brief and validation_summary."
)


def build_qrc_user_payload(packet_payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    quant = packet_payload.get("quant_evidence") or {}
    validation, historical = _validation_for_quant_assessment(packet_payload)
    pending = is_current_validation_pending(packet_payload.get("validation") or {})
    brief = build_quant_research_brief(packet_payload, symbol)
    coverage = compute_validation_coverage(packet_payload)
    sample_quality = compute_sample_quality(packet_payload)
    regime_reliability = compute_regime_reliability(packet_payload)
    gaps = detect_evidence_gaps(packet_payload)

    base: dict[str, Any] = {
        "symbol": symbol,
        "quant_research_brief": brief,
        "validation_summary": summarize_validation(
            validation,
            historical=historical,
            pending_current=pending,
        ),
        "exit_research_summary": summarize_exit_research(list(quant.get("exit_research") or [])),
        "validation_coverage": coverage,
        "evidence_quality": sample_quality,
        "regime_reliability": regime_reliability,
        "evidence_gaps": gaps,
        "overall_quant_confidence": brief["overall_quant_confidence"],
        "instructions": (
            "Use quant_research_brief sections as the primary evidence hierarchy: "
            "historical_strategy_assessment, current_regime_assessment, factor_assessment, "
            "see_assessment (stock-specific primary differentiator), validation_status "
            "(informational only). Current-run validation pending is neutral — never penalize. "
            "overall_quant_confidence is pre-computed per stock from packet evidence; align "
            "your confidence with it unless you cite a specific gap. "
            "Use exit_research_summary for exit-policy context. "
            "Cite evidence refs (validation:*, quant_evidence:*, regime:*, stock_setup_evidence:*)."
        ),
    }

    sqe = packet_payload.get("stock_quality_evidence")
    if get_settings().args_qrc_use_sqe and sqe:
        sqe_brief = build_qrc_sqe_brief(brief, sqe)
        base["qrc_sqe_brief"] = sqe_brief
        base["overall_stock_quality_score"] = sqe_brief["sqe_score"]
        base["instructions"] = _SQE_INSTRUCTIONS

    return base
