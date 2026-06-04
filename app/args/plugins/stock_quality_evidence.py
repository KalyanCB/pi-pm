"""Stock Quality Evidence (SQE) — per-stock packet enricher (Phase 2, observability only)."""

from __future__ import annotations

from typing import Any

from app.args.plugins.quant_payload import summarize_exit_research
from app.args.plugins.quant_research_brief import build_quant_research_brief
from app.args.validation_status import (
    is_current_validation_pending,
    latest_historical_validation_block,
)

SCHEMA_VERSION = "1.0.0"

_WEIGHT_RANKING = 0.20
_WEIGHT_FACTOR = 0.15
_WEIGHT_REGIME = 0.10
_WEIGHT_ANALOG = 0.30
_WEIGHT_EXIT = 0.05
_WEIGHT_VALIDATION = 0.05
_WEIGHT_STRATEGY_PRIOR = 0.15

_COMPONENT_WEIGHTS = {
    "ranking_attribution": _WEIGHT_RANKING,
    "factor_attribution": _WEIGHT_FACTOR,
    "regime_alignment": _WEIGHT_REGIME,
    "historical_analog": _WEIGHT_ANALOG,
    "exit_profile": _WEIGHT_EXIT,
    "validation_context": _WEIGHT_VALIDATION,
    "strategy_context_prior": _WEIGHT_STRATEGY_PRIOR,
}


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _current_regime_label(payload: dict[str, Any]) -> str | None:
    validation = payload.get("validation") or {}
    label = validation.get("regime_label")
    if label:
        return str(label)
    if is_current_validation_pending(validation):
        historical = latest_historical_validation_block(payload)
        if historical.get("regime_label"):
            return str(historical["regime_label"])
    regime = payload.get("regime") or {}
    return regime.get("regime_label")


def _ranking_block(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("ranking") or {}


def _parse_score_components(payload: dict[str, Any]) -> list[dict[str, Any]]:
    components = _ranking_block(payload).get("score_components") or {}
    rows: list[dict[str, Any]] = []
    for factor, raw in components.items():
        if factor == "composite_score" or not isinstance(raw, dict):
            continue
        normalized = _as_float(raw.get("normalized"))
        weighted = _as_float(raw.get("weighted"))
        weight = _as_float(raw.get("weight"))
        if normalized is None and weighted is None:
            continue
        rows.append(
            {
                "factor": factor,
                "normalized": normalized if normalized is not None else 0.0,
                "weighted": weighted if weighted is not None else 0.0,
                "weight": weight,
            }
        )
    return rows


def _build_ranking_attribution(payload: dict[str, Any]) -> dict[str, Any]:
    ranking = _ranking_block(payload)
    rows = _parse_score_components(payload)
    composite = _as_float(ranking.get("composite_score"))

    if not rows:
        return {
            "rank": ranking.get("rank"),
            "composite_score": composite,
            "top_contributors": [],
            "weakest_factor": None,
            "signal_breadth": {"factors_above_0.8": 0, "factors_below_0.3": 0, "label": "UNAVAILABLE"},
            "concentration_ratio_top3": None,
            "quality_score": 0.40,
            "evidence_ref": "ranking:score_components",
        }

    sorted_by_weighted = sorted(rows, key=lambda r: r["weighted"], reverse=True)
    sorted_by_normalized = sorted(rows, key=lambda r: r["normalized"])
    weakest = sorted_by_normalized[0]

    top_contributors = []
    for idx, row in enumerate(sorted_by_weighted[:3], start=1):
        top_contributors.append(
            {
                "factor": row["factor"],
                "normalized": round(row["normalized"], 4),
                "weighted": round(row["weighted"], 4),
                "rank_among_factors": idx,
            }
        )

    above_08 = sum(1 for r in rows if r["normalized"] >= 0.8)
    below_03 = sum(1 for r in rows if r["normalized"] < 0.3)
    if above_08 >= 5:
        breadth_label = "STRONG_BREADTH"
    elif above_08 >= 3:
        breadth_label = "MODERATE_BREADTH"
    else:
        breadth_label = "NARROW_BREADTH"

    total_weighted = sum(abs(r["weighted"]) for r in rows) or 1.0
    top3_weighted = sum(abs(r["weighted"]) for r in sorted_by_weighted[:3])
    concentration = round(top3_weighted / total_weighted, 4)

    breadth_score = _clamp(above_08 / max(len(rows), 1), 0.0, 1.0)
    composite_part = _clamp(composite or 0.5, 0.0, 1.0)
    concentration_part = _clamp(1.0 - max(0.0, concentration - 0.45) * 1.5, 0.0, 1.0)
    quality_score = round(
        composite_part * 0.45 + breadth_score * 0.35 + concentration_part * 0.20,
        4,
    )

    return {
        "rank": ranking.get("rank"),
        "composite_score": composite,
        "top_contributors": top_contributors,
        "weakest_factor": {
            "factor": weakest["factor"],
            "normalized": round(weakest["normalized"], 4),
        },
        "signal_breadth": {
            "factors_above_0.8": above_08,
            "factors_below_0.3": below_03,
            "label": breadth_label,
        },
        "concentration_ratio_top3": concentration,
        "quality_score": quality_score,
        "evidence_ref": "ranking:score_components",
    }


def _factor_ic_by_name(payload: dict[str, Any], regime_label: str | None) -> dict[str, float]:
    quant = payload.get("quant_evidence") or {}
    rows = list(quant.get("factor_ic") or [])
    if regime_label:
        regime_rows = [r for r in rows if r.get("regime_label") == regime_label]
        if regime_rows:
            rows = regime_rows
    ic_map: dict[str, float] = {}
    for row in rows:
        name = row.get("factor_name")
        if not name:
            continue
        ic = _as_float(row.get("ic_spearman") or row.get("ic_pearson") or row.get("ic"))
        if ic is None:
            continue
        existing = ic_map.get(name)
        if existing is None or abs(ic) > abs(existing):
            ic_map[name] = ic
    return ic_map


def _build_factor_attribution(payload: dict[str, Any], regime_label: str | None) -> dict[str, Any]:
    rows = _parse_score_components(payload)
    ic_map = _factor_ic_by_name(payload, regime_label)

    attributions: list[dict[str, Any]] = []
    for row in rows:
        ic = ic_map.get(row["factor"])
        if ic is None:
            continue
        signed = row["normalized"] * ic
        attributions.append(
            {
                "factor": row["factor"],
                "normalized": round(row["normalized"], 4),
                "ic": round(ic, 4),
                "signed_contribution": round(signed, 4),
            }
        )

    if not attributions:
        return {
            "current_regime_label": regime_label,
            "method": "normalized_exposure_x_regime_ic",
            "net_signed_alignment": None,
            "positive_ic_weight_share": None,
            "top_headwinds": [],
            "top_tailwinds": [],
            "quality_score": 0.40,
            "quality_label": "unavailable",
            "note": "No factor IC rows aligned with score_components.",
            "evidence_ref": "ranking:score_components + quant_evidence:factor_ic",
        }

    net_signed = round(sum(a["signed_contribution"] for a in attributions), 4)
    total_weight = sum(abs(r["weighted"]) for r in rows) or 1.0
    positive_weight = sum(
        abs(r["weighted"])
        for r in rows
        if ic_map.get(r["factor"]) is not None and ic_map[r["factor"]] > 0
    )
    positive_share = round(positive_weight / total_weight, 4)

    headwinds = sorted(attributions, key=lambda a: a["signed_contribution"])[:3]
    tailwinds = sorted(attributions, key=lambda a: a["signed_contribution"], reverse=True)[:3]

    alignment_mag = abs(net_signed)
    quality_score = round(
        _clamp(0.55 + net_signed * 0.35 + positive_share * 0.25, 0.15, 0.95),
        4,
    )
    if positive_share >= 0.35 and net_signed >= 0:
        label = "tailwind_favorable"
    elif positive_share <= 0.10 or net_signed <= -0.4:
        label = "headwind_heavy"
    elif net_signed < 0:
        label = "headwind_moderate"
    else:
        label = "mixed_alignment"

    return {
        "current_regime_label": regime_label,
        "method": "normalized_exposure_x_regime_ic",
        "net_signed_alignment": net_signed,
        "positive_ic_weight_share": positive_share,
        "top_headwinds": headwinds,
        "top_tailwinds": tailwinds,
        "quality_score": quality_score,
        "quality_label": label,
        "note": (
            "Signed contribution = normalized × regime IC; "
            "score reflects relative alignment within batch."
        ),
        "evidence_ref": "ranking:score_components + quant_evidence:factor_ic",
    }


def _normalized_factor(payload: dict[str, Any], factor_name: str) -> float | None:
    for row in _parse_score_components(payload):
        if row["factor"] == factor_name:
            return row["normalized"]
    return None


def _build_regime_alignment(payload: dict[str, Any], regime_label: str | None) -> dict[str, Any]:
    regime = payload.get("regime") or {}
    perf = list(regime.get("strategy_regime_performance") or [])

    current_row: dict[str, Any] = {}
    if regime_label:
        matches = [r for r in perf if r.get("regime_label") == regime_label]
        if matches:
            current_row = matches[0]
    if not current_row:
        flagged = [r for r in perf if r.get("is_current_regime")]
        current_row = flagged[0] if flagged else (perf[0] if perf else {})

    best_row: dict[str, Any] = {}
    if perf:
        best_row = max(
            perf,
            key=lambda r: _as_float(r.get("avg_ic")) or float("-inf"),
        )

    current_ic = _as_float(current_row.get("avg_ic"))
    current_spread = _as_float(current_row.get("avg_spread"))
    current_sample = int(current_row.get("sample_count") or 0) or None

    bearish = bool(regime_label and "BEAR" in regime_label.upper())
    mom = _normalized_factor(payload, "volatility_adjusted_momentum")
    high_prox = _normalized_factor(payload, "high_proximity")
    breakout = _normalized_factor(payload, "consolidation_breakout")

    flags = {
        "high_momentum_in_bear_regime": bool(
            bearish and mom is not None and mom >= 0.75
        ),
        "near_highs_in_bear_regime": bool(
            bearish and high_prox is not None and high_prox >= 0.85
        ),
        "weak_breakout_confirmation": bool(
            breakout is not None and breakout < 0.35
        ),
    }

    headwind_count = sum(1 for v in flags.values() if v)
    regime_ic_score = _clamp(0.55 + (current_ic or 0.0) * 4.0, 0.15, 0.95)
    flag_penalty = headwind_count * 0.08
    alignment_score = round(_clamp(regime_ic_score - flag_penalty, 0.15, 0.95), 4)

    if alignment_score >= 0.72:
        alignment_label = "strong_fit"
    elif alignment_score >= 0.55:
        alignment_label = "moderate_headwind" if headwind_count else "moderate_fit"
    else:
        alignment_label = "weak_headwind"

    return {
        "current_regime_label": regime_label,
        "strategy_in_current_regime": {
            "avg_ic": current_ic,
            "avg_spread": current_spread,
            "sample_count": current_sample,
        },
        "strategy_best_regime": {
            "label": best_row.get("regime_label"),
            "avg_ic": _as_float(best_row.get("avg_ic")),
            "avg_spread": _as_float(best_row.get("avg_spread")),
        },
        "stock_profile_flags": flags,
        "alignment_score": alignment_score,
        "alignment_label": alignment_label,
        "evidence_ref": "regime:strategy_regime_performance + ranking:score_components",
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


def _build_historical_analog(payload: dict[str, Any], regime_label: str | None) -> dict[str, Any]:
    see = payload.get("stock_setup_evidence") or {}
    regime_row = _see_regime_row(see, regime_label)

    score_raw = _as_float(see.get("setup_evidence_score"))
    qualifying = int(see.get("qualifying_matches") or 0)
    total = int(see.get("total_matches") or see.get("match_count") or 0)

    win_rate = None
    avg_return = None
    median_return = None
    sample_size = None
    avg_drawdown = None
    avg_runup = None
    if regime_row:
        win_rate = _as_float(regime_row.get("win_rate_20d") or regime_row.get("win_rate_5d"))
        avg_return = _as_float(
            regime_row.get("average_return_20d")
            or regime_row.get("avg_return_20d")
            or regime_row.get("average_return_5d")
        )
        median_return = _as_float(regime_row.get("median_return_20d"))
        sample_size = int(regime_row.get("sample_size") or regime_row.get("similar_setups") or 0)
        avg_drawdown = _as_float(
            regime_row.get("avg_max_drawdown_20d") or regime_row.get("average_max_drawdown_20d")
        )
        avg_runup = _as_float(
            regime_row.get("avg_max_runup_20d") or regime_row.get("average_max_runup_20d")
        )

    ci_low = _as_float((regime_row or {}).get("ci_95_20d_low"))
    ci_high = _as_float((regime_row or {}).get("ci_95_20d_high"))
    ci_95 = None
    if ci_low is not None and ci_high is not None:
        ci_95 = [ci_low, ci_high]
    elif regime_row:
        ci = regime_row.get("ci_95_20d")
        if isinstance(ci, (list, tuple)) and len(ci) >= 2:
            ci_95 = [_as_float(ci[0]), _as_float(ci[1])]

    has_evidence = score_raw is not None or qualifying > 0 or regime_row is not None
    if not has_evidence:
        return {
            "source": "stock_setup_evidence",
            "setup_evidence_score": None,
            "qualifying_matches": qualifying,
            "total_matches": total,
            "regime_label": regime_label,
            "sample_size": None,
            "win_rate_20d": None,
            "avg_return_20d": None,
            "median_return_20d": None,
            "ci_95_20d": None,
            "avg_max_drawdown_20d": None,
            "quality_score": 0.42,
            "quality_label": "unavailable",
            "evidence_ref": "stock_setup_evidence",
        }

    score_component = _clamp((score_raw or 50.0) / 100.0, 0.0, 1.0)
    win_component = _clamp(
        0.5 + ((win_rate - 0.5) * 1.2 if win_rate is not None else 0.0),
        0.0,
        1.0,
    )
    return_component = _clamp(0.5 + (avg_return or 0.0) * 8.0, 0.0, 1.0)
    quality_score = round(
        score_component * 0.50 + win_component * 0.30 + return_component * 0.20,
        4,
    )
    label = (
        "strong"
        if quality_score >= 0.75
        else ("moderate" if quality_score >= 0.55 else "weak")
    )

    return {
        "source": "stock_setup_evidence",
        "setup_evidence_score": score_raw,
        "qualifying_matches": qualifying,
        "total_matches": total,
        "regime_label": regime_row.get("regime_label") if regime_row else regime_label,
        "sample_size": sample_size,
        "win_rate_20d": win_rate,
        "avg_return_20d": avg_return,
        "median_return_20d": median_return,
        "ci_95_20d": ci_95,
        "avg_max_drawdown_20d": avg_drawdown,
        "avg_max_runup_20d": avg_runup,
        "quality_score": quality_score,
        "quality_label": label,
        "evidence_ref": "stock_setup_evidence",
    }


def _drawdown_risk_label(drawdown: float | None) -> str:
    if drawdown is None:
        return "unknown"
    if drawdown >= 0.15:
        return "elevated"
    if drawdown >= 0.10:
        return "moderate"
    return "low"


def _build_exit_profile(payload: dict[str, Any], analog: dict[str, Any]) -> dict[str, Any]:
    quant = payload.get("quant_evidence") or {}
    exit_summary = summarize_exit_research(list(quant.get("exit_research") or []))
    best = exit_summary.get("best_mean_return") or exit_summary.get("highest_hit_rate") or {}

    strategy_default = {
        "best_policy": {
            "family": best.get("policy_family"),
            "variant": best.get("policy_variant"),
            "mean_return": best.get("mean_return"),
            "hit_rate": best.get("hit_rate"),
        },
        "scope": "strategy",
        "evidence_ref": "quant_evidence:exit_research",
    }

    drawdown = _as_float(analog.get("avg_max_drawdown_20d"))
    runup = _as_float(analog.get("avg_max_runup_20d"))
    stock_proxy = {
        "expected_hold_horizon_days": 20,
        "analog_avg_max_drawdown": drawdown,
        "analog_avg_max_runup": runup,
        "drawdown_risk_label": _drawdown_risk_label(drawdown),
        "scope": "stock",
        "evidence_ref": "stock_setup_evidence:regime_statistics",
    }

    exit_quality = 0.55
    if drawdown is not None:
        exit_quality = round(_clamp(0.75 - drawdown * 1.2, 0.25, 0.90), 4)
    if best.get("hit_rate") is not None:
        exit_quality = round((exit_quality + _clamp(float(best["hit_rate"]), 0.0, 1.0)) / 2, 4)

    return {
        "strategy_default": strategy_default,
        "stock_analog_proxy": stock_proxy,
        "quality_score": exit_quality,
        "evidence_ref": "quant_evidence:exit_research + stock_setup_evidence",
    }


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


def _build_validation_context(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload.get("validation") or {}
    pending = is_current_validation_pending(validation)
    historical = latest_historical_validation_block(payload) if pending else {}

    source = historical if pending and historical else {}
    if not source and pending:
        hist_ctx = payload.get("historical_validation_context") or {}
        recent = list(hist_ctx.get("recent_completed_validations") or [])
        source = recent[-1] if recent else {}

    horizon_metrics = list(source.get("horizon_metrics") or [])
    decile_metrics = list(source.get("decile_metrics") or [])
    primary = _primary_horizon_metric(horizon_metrics)

    rank_ic = None
    spread = None
    sample_size = None
    if primary:
        rank_ic = _as_float(primary.get("rank_ic_spearman") or primary.get("ic_pearson"))
        sample_size = int(primary.get("sample_size") or 0) or None
        spread = _decile_spread(decile_metrics, primary.get("horizon"))
        if spread is None:
            spread = _as_float(primary.get("spread"))

    if not source:
        hist_quality = 0.40
        hist_label = "unavailable"
    else:
        ic_score = _clamp(0.5 + abs(rank_ic or 0.0) * 6.0, 0.35, 0.90)
        spread_score = _clamp(0.5 + abs(spread or 0.0) * 12.0, 0.35, 0.90)
        hist_quality = round(ic_score * 0.55 + spread_score * 0.45, 4)
        hist_label = (
            "strong"
            if hist_quality >= 0.75
            else ("moderate" if hist_quality >= 0.55 else "weak")
        )

    informational = 0.50 if pending else 0.85

    return {
        "scope": "strategy",
        "current_run_status": validation.get("status"),
        "pending_neutral": pending,
        "historical_substitute": {
            "quality_label": hist_label,
            "rank_ic": rank_ic,
            "decile_spread": spread,
            "sample_size": sample_size,
            "as_of_date": source.get("as_of_date"),
        },
        "informational_score": informational,
        "evidence_ref": "historical_validation_context + validation:status",
    }


def _strategy_context_subset(brief: dict[str, Any]) -> dict[str, Any]:
    return {
        "_from": "build_quant_research_brief",
        "historical_strategy_assessment": {
            "quality_score": brief["historical_strategy_assessment"]["quality_score"],
            "quality_label": brief["historical_strategy_assessment"].get("quality_label"),
        },
        "current_regime_assessment": {
            "fit_score": brief["current_regime_assessment"]["fit_score"],
            "fit_label": brief["current_regime_assessment"].get("fit_label"),
        },
        "factor_assessment": {
            "quality_score": brief["factor_assessment"]["quality_score"],
            "quality_label": brief["factor_assessment"].get("quality_label"),
        },
        "validation_status": {
            "informational_score": brief["validation_status"]["informational_score"],
            "pending_neutral": brief["validation_status"].get("pending_neutral"),
        },
    }


def _strategy_context_blend(strategy_context: dict[str, Any]) -> float:
    hist = strategy_context["historical_strategy_assessment"]["quality_score"]
    regime = strategy_context["current_regime_assessment"]["fit_score"]
    factor = strategy_context["factor_assessment"]["quality_score"]
    validation = strategy_context["validation_status"]["informational_score"]
    return round(hist * 0.40 + regime * 0.30 + factor * 0.20 + validation * 0.10, 4)


def build_stock_quality_evidence(packet_payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    """Build per-stock SQE object (observability only; does not affect QRC confidence)."""
    regime_label = _current_regime_label(packet_payload)
    ranking = _ranking_block(packet_payload)

    brief = build_quant_research_brief(packet_payload, symbol)
    strategy_context = _strategy_context_subset(brief)
    strategy_blend = _strategy_context_blend(strategy_context)

    section_a = _build_ranking_attribution(packet_payload)
    section_b = _build_factor_attribution(packet_payload, regime_label)
    section_c = _build_regime_alignment(packet_payload, regime_label)
    section_d = _build_historical_analog(packet_payload, regime_label)
    section_e = _build_exit_profile(packet_payload, section_d)
    section_f = _build_validation_context(packet_payload)

    overall = round(
        section_a["quality_score"] * _WEIGHT_RANKING
        + section_b["quality_score"] * _WEIGHT_FACTOR
        + section_c["alignment_score"] * _WEIGHT_REGIME
        + section_d["quality_score"] * _WEIGHT_ANALOG
        + section_e["quality_score"] * _WEIGHT_EXIT
        + section_f["informational_score"] * _WEIGHT_VALIDATION
        + strategy_blend * _WEIGHT_STRATEGY_PRIOR,
        4,
    )
    overall_stock_quality_score = round(_clamp(overall, 0.15, 0.95), 4)

    return {
        "schema_version": SCHEMA_VERSION,
        "symbol": symbol,
        "as_of_date": ranking.get("as_of_date"),
        "ranking_run_id": ranking.get("ranking_run_id"),
        "A_ranking_attribution": section_a,
        "B_factor_attribution": section_b,
        "C_regime_alignment": section_c,
        "D_historical_analog": section_d,
        "E_exit_profile": section_e,
        "F_validation_context": section_f,
        "strategy_context": strategy_context,
        "overall_stock_quality_score": overall_stock_quality_score,
        "component_weights": dict(_COMPONENT_WEIGHTS),
        "legacy_overall_quant_confidence": brief["overall_quant_confidence"],
    }


def condense_stock_quality_evidence(sqe: dict[str, Any]) -> dict[str, Any]:
    """Compact SQE for markdown export (key scores and labels only)."""
    return {
        "schema_version": sqe.get("schema_version"),
        "symbol": sqe.get("symbol"),
        "overall_stock_quality_score": sqe.get("overall_stock_quality_score"),
        "legacy_overall_quant_confidence": sqe.get("legacy_overall_quant_confidence"),
        "A_ranking": {
            "rank": (sqe.get("A_ranking_attribution") or {}).get("rank"),
            "quality_score": (sqe.get("A_ranking_attribution") or {}).get("quality_score"),
            "breadth_label": ((sqe.get("A_ranking_attribution") or {}).get("signal_breadth") or {}).get(
                "label"
            ),
        },
        "B_factor": {
            "quality_score": (sqe.get("B_factor_attribution") or {}).get("quality_score"),
            "quality_label": (sqe.get("B_factor_attribution") or {}).get("quality_label"),
            "net_signed_alignment": (sqe.get("B_factor_attribution") or {}).get("net_signed_alignment"),
        },
        "C_regime": {
            "alignment_score": (sqe.get("C_regime_alignment") or {}).get("alignment_score"),
            "alignment_label": (sqe.get("C_regime_alignment") or {}).get("alignment_label"),
        },
        "D_analog": {
            "setup_evidence_score": (sqe.get("D_historical_analog") or {}).get("setup_evidence_score"),
            "quality_score": (sqe.get("D_historical_analog") or {}).get("quality_score"),
            "win_rate_20d": (sqe.get("D_historical_analog") or {}).get("win_rate_20d"),
        },
        "E_exit": {"quality_score": (sqe.get("E_exit_profile") or {}).get("quality_score")},
        "F_validation": {
            "pending_neutral": (sqe.get("F_validation_context") or {}).get("pending_neutral"),
            "informational_score": (sqe.get("F_validation_context") or {}).get("informational_score"),
        },
    }
