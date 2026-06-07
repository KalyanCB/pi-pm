from fastapi import APIRouter, Depends

from app.api.auth_deps import get_current_user, require_owner
from app.api.v1 import (
    auth,
    backtest,
    copilot,
    daily_batch,
    execution,
    exit_analytics,
    factor_analytics,
    health,
    investment_committee,
    market_data,
    observability,
    pilot_ops,
    portfolio,
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
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

_authenticated = [Depends(get_current_user)]
_owner_mutations = [Depends(get_current_user), Depends(require_owner)]

api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"], dependencies=_authenticated)
api_router.include_router(
    market_data.router, prefix="/market-data", tags=["market-data"], dependencies=_authenticated
)
api_router.include_router(rankings.router, prefix="/rankings", tags=["rankings"], dependencies=_authenticated)
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"], dependencies=_authenticated)
api_router.include_router(
    validation.router, prefix="/validation", tags=["validation"], dependencies=_authenticated
)
api_router.include_router(
    observability.router, prefix="/observability", tags=["observability"], dependencies=_authenticated
)
api_router.include_router(
    regime_policy.router, prefix="/regime-policy", tags=["regime-policy"], dependencies=_authenticated
)
api_router.include_router(
    factor_analytics.router,
    prefix="/analytics/factors",
    tags=["factor-analytics"],
    dependencies=_authenticated,
)
api_router.include_router(
    exit_analytics.router,
    prefix="/analytics/exit",
    tags=["exit-analytics"],
    dependencies=_authenticated,
)
api_router.include_router(
    research_intelligence.router,
    prefix="/analytics/research-intelligence",
    tags=["research-intelligence"],
    dependencies=_authenticated,
)
api_router.include_router(
    research.router, prefix="/research", tags=["research-deprecated"], dependencies=_authenticated
)
api_router.include_router(
    investment_committee.router,
    prefix="/investment-committee",
    tags=["investment-committee"],
    dependencies=_authenticated,
)
api_router.include_router(
    stock_setup_research.router,
    prefix="/research/stock-setup",
    tags=["research-stock-setup"],
    dependencies=_authenticated,
)
api_router.include_router(
    daily_batch.router,
    prefix="/ops/daily-batch",
    tags=["ops-daily-batch"],
    dependencies=_owner_mutations,
)
api_router.include_router(
    pilot_ops.router,
    prefix="/pilot",
    tags=["pilot-command-center"],
    dependencies=_authenticated,
)
api_router.include_router(
    recommendations.router,
    prefix="/recommendations",
    tags=["recommendations"],
    dependencies=_authenticated,
)
api_router.include_router(
    recommendation_analytics.router,
    prefix="/analytics/recommendations",
    tags=["recommendation-analytics"],
    dependencies=_authenticated,
)
api_router.include_router(
    portfolio.router,
    prefix="/portfolio",
    tags=["portfolio"],
    dependencies=_authenticated,
)
api_router.include_router(
    execution.router,
    prefix="/execution",
    tags=["execution"],
    dependencies=_authenticated,
)
api_router.include_router(
    copilot.router,
    prefix="/copilot",
    tags=["copilot"],
    dependencies=_authenticated,
)
