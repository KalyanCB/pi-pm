"""Per-committee scoped packet views for prompt isolation (Phase 2 independence)."""

from __future__ import annotations

from typing import Any

from app.args.plugins.quant_payload import build_qrc_user_payload


def _pick(obj: dict[str, Any] | None, *keys: str) -> dict[str, Any]:
    if not obj:
        return {}
    return {k: obj[k] for k in keys if k in obj}


def _ranking_attribution(ranking: dict[str, Any] | None) -> dict[str, Any]:
    if not ranking:
        return {}
    return {
        "rank": ranking.get("rank"),
        "composite_score": ranking.get("composite_score"),
        "score_components": ranking.get("score_components") or {},
        "strategy_name": ranking.get("strategy_name"),
        "as_of_date": ranking.get("as_of_date"),
    }


def build_tarc_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Technical ranking attribution and factor context only."""
    ranking = payload.get("ranking") or {}
    regime = payload.get("regime") or {}
    return {
        "symbol": payload.get("symbol"),
        "ranking": _ranking_attribution(ranking),
        "technical_factors": payload.get("technical_factors") or {},
        "regime": {
            "regime_label": regime.get("regime_label"),
            "strategy_regime_performance": regime.get("strategy_regime_performance") or [],
        },
        "historical_performance": payload.get("historical_performance") or {},
        "scope_note": (
            "TARC mandate: technical structure, ranking factors, momentum/trend/volume/breakout "
            "mechanics only. Do not cite validation, factor IC, SEE, SQE, fundamentals, or news."
        ),
    }


def build_qrc_view(payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    """Quant validation, IC, regime, SEE/SQE evidence — no technical narrative or news."""
    quant = payload.get("quant_evidence") or {}
    validation = payload.get("validation") or {}
    historical_ctx = payload.get("historical_validation_context") or {}
    base = build_qrc_user_payload(payload, symbol)
    view: dict[str, Any] = {
        "symbol": symbol,
        "validation": validation,
        "historical_validation_context": historical_ctx,
        "factor_ic_summary": {
            "row_count": len(quant.get("factor_ic") or []),
            "factor_ic": (quant.get("factor_ic") or [])[:12],
            "evidence_ref_hint": "quant_evidence:factor_ic",
        },
        "regime": payload.get("regime") or {},
        "stock_setup_evidence": payload.get("stock_setup_evidence") or {},
        "stock_quality_evidence": payload.get("stock_quality_evidence") or {},
        "scope_note": (
            "QRC mandate: factor IC, validation history, decile separation, regime performance, "
            "SEE/SQE summaries. Challenge strong technical ranks when validation is weak. "
            "Do not repeat TARC factor storytelling, fundamentals, or news."
        ),
    }
    if "qrc_sqe_brief" in base:
        view["qrc_sqe_brief"] = base["qrc_sqe_brief"]
    if "quant_research_brief" in base:
        view["quant_research_brief"] = base["quant_research_brief"]
    for key in (
        "validation_summary",
        "validation_coverage",
        "evidence_quality",
        "regime_reliability",
        "evidence_gaps",
        "exit_research_summary",
    ):
        if key in base:
            view[key] = base[key]
    return view


def _fundamentals_present(snapshot: dict[str, Any] | None) -> bool:
    if not snapshot:
        return False
    if snapshot.get("status") == "unavailable":
        return False
    meaningful = {
        k: v for k, v in snapshot.items() if k != "status" and v not in (None, "", [], {})
    }
    return bool(meaningful)


def build_frc_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Fundamental snapshot only."""
    snapshot = payload.get("fundamental_snapshot") or {}
    sufficient = _fundamentals_present(snapshot)
    return {
        "symbol": payload.get("symbol"),
        "fundamental_snapshot": snapshot,
        "fundamental_evidence_status": "sufficient" if sufficient else "insufficient",
        "scope_note": (
            "FRC mandate: business quality, profitability, balance sheet, earnings, valuation only. "
            "If fundamental_evidence_status is insufficient, abstain — do not use ranking/regime filler."
        ),
    }


def _news_present(news: dict[str, Any] | None) -> bool:
    if not news:
        return False
    items = news.get("items") or []
    status = str(news.get("status") or "").lower()
    if items:
        return True
    return status not in ("", "unavailable", "missing", "none")


def build_nrcc_view(payload: dict[str, Any]) -> dict[str, Any]:
    """News snapshot and research catalyst context only."""
    news = payload.get("news_snapshot") or {}
    research = payload.get("research_context") or {}
    catalysts = research.get("catalysts") or research.get("notes") or []
    has_news = _news_present(news)
    return {
        "symbol": payload.get("symbol"),
        "news_snapshot": news,
        "research_context": {"catalysts": catalysts} if catalysts else {},
        "news_evidence_status": "available" if has_news else "no_news_evidence",
        "scope_note": (
            "NRCC mandate: news, corporate events, macro, sector context only. "
            "If news_evidence_status is no_news_evidence, report structured absence — "
            "do not cite rank/composite or validation IC."
        ),
    }


def build_rc_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Risk framing: drawdown, liquidity, concentration, regime risk."""
    see = payload.get("stock_setup_evidence") or {}
    market = payload.get("market_snapshot") or {}
    ranking = payload.get("ranking") or {}
    regime = payload.get("regime") or {}
    portfolio = payload.get("portfolio_context") or {}
    drawdown_fields = _pick(
        see,
        "setup_evidence_score",
        "max_drawdown",
        "median_drawdown",
        "worst_drawdown",
        "qualifying_matches",
        "status",
    )
    liquidity_fields = _pick(
        market,
        "avg_volume",
        "volume",
        "liquidity_score",
        "bid_ask_spread",
        "market_cap",
        "sector",
        "last_date",
    )
    concentration_fields = {
        "rank": ranking.get("rank"),
        "portfolio_context": portfolio,
        "score_components": ranking.get("score_components") or {},
    }
    regime_risk = {
        "regime_label": regime.get("regime_label"),
        "strategy_regime_performance": regime.get("strategy_regime_performance") or [],
    }
    has_risk_inputs = bool(
        drawdown_fields
        or liquidity_fields
        or ranking.get("rank") is not None
        or regime.get("regime_label")
    )
    return {
        "symbol": payload.get("symbol"),
        "risk_drawdown": drawdown_fields,
        "market_snapshot": liquidity_fields,
        "concentration_context": concentration_fields,
        "regime_risk": regime_risk,
        "risk_evidence_status": "sufficient" if has_risk_inputs else "insufficient",
        "scope_note": (
            "RC mandate: drawdown, regime risk, liquidity, concentration, veto themes. "
            "Strengths must not mirror TARC bullish factors. "
            "supporting_evidence refs MUST use exactly: risk_drawdown:, market_snapshot:, "
            "concentration_context:, regime_risk:, risk:, stock_setup_evidence:, portfolio_context:, regime:. "
            "Do NOT use ranking:, quant_evidence:, validation:, or technical_factors: prefixes."
        ),
    }
