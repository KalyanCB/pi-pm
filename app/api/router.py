from fastapi import APIRouter

from app.api.v1 import health, market_data, stocks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
