"""Deterministic per-stock quant research brief for QRC (packet-grounded only)."""

from __future__ import annotations

from typing import Any

from app.args.validation_status import (
    is_current_validation_pending,
    latest_historical_validation_block,
)

_WEIGHT_SEE = 0.45
_WEIGHT_HISTORICAL = 0.20
_WEIGHT_REGIME = 0.15
_WEIGHT_FACTOR = 0.15
_WEIGHT_VALIDATION_STATUS = 0.05  # bonus only when completed; no penalty when pending


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _score_from_magnitude(value: float | None, *, strong: float, moderate: float) -> float:
    if value is None:
        return 0.45
    mag = abs(value)
    if mag >= strong:
        return 0.90
    if mag >= moderate:
        return 0.70
    if mag >= moderate / 2:
        return 0.55
    return 0.35


def _score_sample_size(sample: int | None) -> float:
    if not sample or sample <= 0:
        return 0.35
    if sample >= 500:
        return 0.90
    if sample >= 200:
        return 0.70
    if sample >= 50:
        return 0.55
    return 0.40


def _primary_horizon_metric(metrics: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for metric in metrics:
        sample = int(metric.get("sample_size") or 0)
        if sample <= 0:
            continue
        if best is None or sample > int(best.get("sample_size") or 0):
            best = metric
    return best


def _decile_spread(decile_metrics: list[dict[str, Any]], horizon: Any) -> float | None:
    horizon_deciles = [d for d in decile_metrics if d.get("horizon") == horizon]
    if len(horizon_deciles) < 2:
        return None
    top = max(horizon_deciles, key=lambda d: d.get("decile", 0))
    bottom = min(horizon_deciles, key=lambda d: d.get("decile", 0))
    top_ret = _as_float(top.get("avg_return"))
    bottom_ret = _as_float(bottom.get("avg_return"))
    if top_ret is None or bottom_ret is None:
        return None
    return top_ret - bottom_ret


def _assess_historical_strategy(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload.get("validation") or {}
    pending = is_current_validation_pending(validation)
    hist_ctx = payload.get("historical_validation_context") or {}
    recent = list(hist_ctx.get("recent_completed_validations") or [])
    historical = latest_historical_validation_block(payload) if pending else {}

    source = historical if pending and historical else (recent[-1] if recent else {})
    horizon_metrics = list(source.get("horizon_metrics") or [])
    decile_metrics = list(source.get("decile_metrics") or [])
    primary = _primary_horizon_metric(horizon_metrics)

    rank_ic = None
    hit_rate = None
    sample_size = None
    spread = None
    if primary:
        rank_ic = _as_float(primary.get("rank_ic_spearman") or primary.get("ic_pearson"))
        hit_rate = _as_float(primary.get("hit_rate") or primary.get("directional_hit_rate"))
        sample_size = int(primary.get("sample_size") or 0) or None
        spread = _decile_spread(decile_metrics, primary.get("horizon"))
        if spread is None:
            spread = _as_float(primary.get("spread"))

    ic_score = _score_from_magnitude(rank_ic, strong=0.05, moderate=0.025)
    spread_score = _score_from_magnitude(spread, strong=0.02, moderate=0.01)
    hit_score = _score_from_magnitude(
        (hit_rate - 0.5) if hit_rate is not None else None, strong=0.10, moderate=0.05
    )
    sample_score = _score_sample_size(sample_size)

    if not source:
        quality_score = 0.40
        label = "unavailable"
    else:
        quality_score = round(
            ic_score * 0.35 + spread_score * 0.30 + hit_score * 0.15 + sample_score * 0.20,
            4,
        )
        label = (
            "strong"
            if quality_score >= 0.75
            else ("moderate" if quality_score >= 0.55 else "weak")
        )

    return {
        "source": "historical_validation_context" if pending else "recent_completed_validations",
        "as_of_date": source.get("as_of_date"),
        "report_id": source.get("report_id"),
        "regime_label": source.get("regime_label") or validation.get("regime_label"),
        "rank_ic": rank_ic,
        "decile_spread": spread,
        "hit_rate": hit_rate,
        "sample_size": sample_size,
        "completed_reports_in_window": hist_ctx.get("completed_reports_in_window"),
        "quality_label": label,
        "quality_score": quality_score,
        "evidence_ref_hint": "historical_validation_context",
    }


def _current_regime_label(payload: dict[str, Any]) -> str | None:
    validation = payload.get("validation") or {}
    label = validation.get("regime_label")
    if label:
        return str(label)
    if is_current_validation_pending(validation):
        historical = latest_historical_validation_block(payload)
        if historical.get("regime_label"):
            return str(historical["regime_label"])
    return None


def _assess_current_regime(payload: dict[str, Any]) -> dict[str, Any]:
    regime = payload.get("regime") or {}
    perf = list(regime.get("strategy_regime_performance") or [])
    current_label = _current_regime_label(payload)

    current_rows = [r for r in perf if r.get("is_current_regime")]
    if not current_rows and current_label:
        current_rows = [r for r in perf if r.get("regime_label") == current_label]
    if not current_rows and perf:
        current_rows = perf[:1]

    row = current_rows[0] if current_rows else {}
    avg_ic = _as_float(row.get("avg_ic"))
    avg_spread = _as_float(row.get("avg_spread"))
    sample_count = int(row.get("sample_count") or 0) or None

    ic_score = _score_from_magnitude(avg_ic, strong=0.04, moderate=0.02)
    spread_score = _score_from_magnitude(avg_spread, strong=0.015, moderate=0.008)
    sample_score = _score_sample_size(sample_count)

    if not row:
        quality_score = 0.40
        label = "unsupported"
    else:
        quality_score = round(ic_score * 0.45 + spread_score * 0.35 + sample_score * 0.20, 4)
        label = (
            "strong_fit"
            if quality_score >= 0.75
            else ("moderate_fit" if quality_score >= 0.55 else "weak_fit")
        )

    return {
        "current_regime_label": current_label,
        "regime_performance": {
            "regime_label": row.get("regime_label"),
            "horizon": row.get("horizon"),
            "avg_ic": avg_ic,
            "avg_spread": avg_spread,
            "sample_count": sample_count,
            "is_current_regime": row.get("is_current_regime"),
        },
        "regime_rows_available": len(perf),
        "fit_label": label,
        "fit_score": quality_score,
        "evidence_ref_hint": "regime:strategy_regime_performance",
    }


def _assess_factors(payload: dict[str, Any]) -> dict[str, Any]:
    quant = payload.get("quant_evidence") or {}
    rows = list(quant.get("factor_ic") or [])
    numeric: list[dict[str, Any]] = []
    for row in rows:
        ic = _as_float(row.get("ic_spearman") or row.get("ic_pearson") or row.get("ic"))
        if ic is None:
            continue
        numeric.append(
            {
                "factor_name": row.get("factor_name"),
                "ic": ic,
                "horizon": row.get("horizon"),
                "regime_label": row.get("regime_label"),
                "stability_score": _as_float(row.get("stability_score")),
            }
        )

    if not numeric:
        return {
            "row_count": len(rows),
            "quality_label": "unavailable",
            "quality_score": 0.40,
            "top_positive_factors": [],
            "top_negative_factors": [],
            "avg_stability": None,
            "evidence_ref_hint": "quant_evidence:factor_ic",
        }

    sorted_rows = sorted(numeric, key=lambda r: r["ic"], reverse=True)
    top_pos = sorted_rows[:3]
    top_neg = list(reversed(sorted_rows[-3:])) if len(sorted_rows) >= 3 else sorted_rows[-1:]
    stabilities = [r["stability_score"] for r in numeric if r["stability_score"] is not None]
    avg_stability = sum(stabilities) / len(stabilities) if stabilities else None

    ics = [abs(r["ic"]) for r in numeric]
    avg_ic_mag = sum(ics) / len(ics)
    ic_score = _score_from_magnitude(avg_ic_mag, strong=0.05, moderate=0.025)
    stability_score = (
        _clamp(avg_stability, 0.0, 1.0) if avg_stability is not None else 0.50
    )
    quality_score = round(ic_score * 0.65 + stability_score * 0.35, 4)
    label = (
        "strong"
        if quality_score >= 0.75
        else ("moderate" if quality_score >= 0.55 else "weak")
    )

    return {
        "row_count": len(rows),
        "quality_label": label,
        "quality_score": quality_score,
        "top_positive_factors": top_pos,
        "top_negative_factors": top_neg,
        "avg_abs_ic": round(avg_ic_mag, 4),
        "avg_stability": round(avg_stability, 4) if avg_stability is not None else None,
        "evidence_ref_hint": "quant_evidence:factor_ic",
    }


def _see_regime_row(see: dict[str, Any], current_regime: str | None) -> dict[str, Any] | None:
    stats = list(see.get("regime_statistics") or [])
    if not stats:
        return None
    if current_regime:
        for row in stats:
            if row.get("regime_label") == current_regime:
                return row
    for row in stats:
        if row.get("regime_label") == "ALL_REGIMES":
            return row
    return stats[0]


def _assess_see(payload: dict[str, Any]) -> dict[str, Any]:
    see = payload.get("stock_setup_evidence") or {}
    current_regime = _current_regime_label(payload)
    status = str(see.get("status") or "").lower()

    score_raw = _as_float(see.get("setup_evidence_score"))
    qualifying = int(see.get("qualifying_matches") or 0)
    total = int(see.get("total_matches") or see.get("match_count") or 0)
    regime_row = _see_regime_row(see, current_regime)

    win_rate = None
    avg_return = None
    median_return = None
    sample_size = None
    if regime_row:
        win_rate = _as_float(regime_row.get("win_rate_20d") or regime_row.get("win_rate_5d"))
        avg_return = _as_float(
            regime_row.get("average_return_20d")
            or regime_row.get("avg_return_20d")
            or regime_row.get("average_return_5d")
        )
        median_return = _as_float(regime_row.get("median_return_20d"))
        sample_size = int(regime_row.get("sample_size") or regime_row.get("similar_setups") or 0)

    has_evidence = (
        score_raw is not None
        or qualifying > 0
        or status in ("completed", "ok")
        or regime_row is not None
    )

    if not has_evidence:
        return {
            "status": see.get("status") or "unavailable",
            "quality_label": "unavailable",
            "quality_score": 0.42,
            "setup_evidence_score": None,
            "qualifying_matches": qualifying,
            "total_matches": total,
            "regime_label": current_regime,
            "win_rate_20d": None,
            "avg_return_20d": None,
            "median_return_20d": None,
            "similar_setups_sample": None,
            "evidence_ref_hint": "stock_setup_evidence",
        }

    score_component = _clamp((score_raw or 50.0) / 100.0, 0.0, 1.0)
    match_component = _score_sample_size(qualifying if qualifying > 0 else sample_size)
    win_component = _score_from_magnitude(
        (win_rate - 0.5) if win_rate is not None else None, strong=0.12, moderate=0.06
    )
    return_component = _score_from_magnitude(avg_return, strong=0.03, moderate=0.015)

    quality_score = round(
        score_component * 0.45
        + match_component * 0.25
        + win_component * 0.20
        + return_component * 0.10,
        4,
    )
    label = (
        "strong"
        if quality_score >= 0.75
        else ("moderate" if quality_score >= 0.55 else "weak")
    )

    return {
        "status": see.get("status"),
        "research_id": see.get("research_id"),
        "quality_label": label,
        "quality_score": quality_score,
        "setup_evidence_score": score_raw,
        "qualifying_matches": qualifying,
        "total_matches": total,
        "regime_label": regime_row.get("regime_label") if regime_row else current_regime,
        "win_rate_20d": win_rate,
        "avg_return_20d": avg_return,
        "median_return_20d": median_return,
        "similar_setups_sample": sample_size,
        "evidence_ref_hint": "stock_setup_evidence",
    }


def _assess_validation_status(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload.get("validation") or {}
    pending = is_current_validation_pending(validation)
    status = validation.get("status")
    db_status = validation.get("database_status")

    if pending:
        status_score = 0.50  # neutral — never penalize pending
        note = (
            "Current-run forward validation is pending or insufficient_data; "
            "informational only (not a negative signal)."
        )
    elif str(status).lower() in ("completed", "ok"):
        status_score = 0.85
        note = "Current-run validation completed."
    else:
        status_score = 0.50
        note = f"Current validation status: {status}."

    return {
        "status": status,
        "database_status": db_status,
        "pending_neutral": pending,
        "informational_score": status_score,
        "note": note,
        "evidence_ref_hint": "validation:status",
    }


def build_quant_research_brief(packet_payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    """Build per-stock quant brief with deterministic overall_quant_confidence."""
    historical = _assess_historical_strategy(packet_payload)
    regime = _assess_current_regime(packet_payload)
    factors = _assess_factors(packet_payload)
    see = _assess_see(packet_payload)
    validation_status = _assess_validation_status(packet_payload)

    weighted = round(
        see["quality_score"] * _WEIGHT_SEE
        + historical["quality_score"] * _WEIGHT_HISTORICAL
        + regime["fit_score"] * _WEIGHT_REGIME
        + factors["quality_score"] * _WEIGHT_FACTOR
        + validation_status["informational_score"] * _WEIGHT_VALIDATION_STATUS,
        4,
    )
    overall = _clamp(weighted, 0.15, 0.95)

    return {
        "symbol": symbol,
        "historical_strategy_assessment": historical,
        "current_regime_assessment": regime,
        "factor_assessment": factors,
        "see_assessment": see,
        "validation_status": validation_status,
        "overall_quant_confidence": overall,
        "confidence_weights": {
            "see": _WEIGHT_SEE,
            "historical_strategy": _WEIGHT_HISTORICAL,
            "regime_fit": _WEIGHT_REGIME,
            "factor_quality": _WEIGHT_FACTOR,
            "validation_status_informational": _WEIGHT_VALIDATION_STATUS,
        },
        "component_scores": {
            "see": see["quality_score"],
            "historical_strategy": historical["quality_score"],
            "regime_fit": regime["fit_score"],
            "factor_quality": factors["quality_score"],
            "validation_status": validation_status["informational_score"],
        },
    }
