from fastapi import APIRouter

from app.api.v1 import (
    backtest,
    daily_batch,
    exit_analytics,
    factor_analytics,
    health,
    market_data,
    observability,
    rankings,
    recommendation_analytics,
    recommendations,
    regime_policy,
    research,
    research_intelligence,
    stock_setup_research,
    stocks,
    validation,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
api_router.include_router(rankings.router, prefix="/rankings", tags=["rankings"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(validation.router, prefix="/validation", tags=["validation"])
api_router.include_router(observability.router, prefix="/observability", tags=["observability"])
api_router.include_router(regime_policy.router, prefix="/regime-policy", tags=["regime-policy"])
api_router.include_router(factor_analytics.router, prefix="/analytics/factors", tags=["factor-analytics"])
api_router.include_router(exit_analytics.router, prefix="/analytics/exit", tags=["exit-analytics"])
api_router.include_router(
    research_intelligence.router,
    prefix="/analytics/research-intelligence",
    tags=["research-intelligence"],
)
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(
    stock_setup_research.router,
    prefix="/research/stock-setup",
    tags=["research-stock-setup"],
)
api_router.include_router(
    daily_batch.router,
    prefix="/ops/daily-batch",
    tags=["ops-daily-batch"],
)
api_router.include_router(
    recommendations.router,
    prefix="/recommendations",
    tags=["recommendations"],
)
api_router.include_router(
    recommendation_analytics.router,
    prefix="/analytics/recommendations",
    tags=["recommendation-analytics"],
)
