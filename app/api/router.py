from fastapi import APIRouter

from app.api.v1 import backtest, health, market_data, rankings, stocks, validation

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
api_router.include_router(rankings.router, prefix="/rankings", tags=["rankings"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(validation.router, prefix="/validation", tags=["validation"])
