"""Recommendation Performance & Trust Analytics API (P3)."""
from __future__ import annotations

import dataclasses
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import get_recommendation_analytics_service
from app.services.recommendation_analytics_service import RecommendationAnalyticsService

router = APIRouter()


def _to_dict(obj: Any) -> Any:
    """Recursively convert dataclasses to dicts for JSON serialisation."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_summary(
    strategy_name: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    service: RecommendationAnalyticsService = Depends(get_recommendation_analytics_service),
) -> Any:
    """Overall recommendation performance summary.

    Answers: "Are recommendations working?"
    Includes quality metrics (win rate, alpha, profit factor), top BUY candidates,
    and current EXIT_APPROVED candidates.
    """
    result = service.get_summary(
        strategy_name=strategy_name,
        from_date=from_date,
        to_date=to_date,
    )
    return _to_dict(result)


# ── Conviction effectiveness ───────────────────────────────────────────────────

@router.get("/conviction")
def get_conviction_performance(
    strategy_name: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    service: RecommendationAnalyticsService = Depends(get_recommendation_analytics_service),
) -> Any:
    """Conviction band effectiveness.

    Answers: "Do HIGH conviction picks outperform MEDIUM?"
    Includes per-band win rate, alpha, profit factor and calibration assessment.
    """
    result = service.get_conviction_performance(
        strategy_name=strategy_name,
        from_date=from_date,
        to_date=to_date,
    )
    return _to_dict(result)


# ── Regime effectiveness ───────────────────────────────────────────────────────

@router.get("/regime")
def get_regime_performance(
    strategy_name: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    service: RecommendationAnalyticsService = Depends(get_recommendation_analytics_service),
) -> Any:
    """Regime effectiveness.

    Answers: "Do recommendations perform differently across market regimes?"
    Includes per-regime win rate, alpha, recommendation count.
    """
    result = service.get_regime_performance(
        strategy_name=strategy_name,
        from_date=from_date,
        to_date=to_date,
    )
    return _to_dict(result)


# ── Committee effectiveness ────────────────────────────────────────────────────

@router.get("/committee")
def get_committee_performance(
    strategy_name: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    service: RecommendationAnalyticsService = Depends(get_recommendation_analytics_service),
) -> Any:
    """Committee advisory effectiveness (post-hoc, observation only).

    Answers: "Is ARGS adding predictive value?"
    Committee output is advisory — this measures it, does not use it to change recommendations.
    """
    result = service.get_committee_performance(
        strategy_name=strategy_name,
        from_date=from_date,
        to_date=to_date,
    )
    return _to_dict(result)


# ── Trust metrics ─────────────────────────────────────────────────────────────

@router.get("/trust")
def get_trust_metrics(
    strategy_name: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    service: RecommendationAnalyticsService = Depends(get_recommendation_analytics_service),
) -> Any:
    """Trust metrics: conviction calibration, stability, reliability.

    Answers: "Should I trust the next recommendation?"
    - Calibration: do conviction bands predict outcomes correctly?
    - Stability: how much do recommendations churn day-to-day?
    - Reliability: what fraction of recommendations had complete validation data?
    """
    result = service.get_trust_metrics(
        strategy_name=strategy_name,
        from_date=from_date,
        to_date=to_date,
    )
    return _to_dict(result)


# ── Symbol analytics ──────────────────────────────────────────────────────────

@router.get("/symbol/{symbol}")
def get_symbol_analytics(
    symbol: str,
    strategy_name: str | None = Query(default=None),
    service: RecommendationAnalyticsService = Depends(get_recommendation_analytics_service),
) -> Any:
    """Per-symbol recommendation history and performance.

    Answers: "Why was HFCL not recommended?" and "How has RELIANCE performed
    across recommendations?"
    Includes last action, why-not reason codes, win rate, alpha, conviction history.
    """
    result = service.get_symbol_analytics(symbol, strategy_name)
    return _to_dict(result)
