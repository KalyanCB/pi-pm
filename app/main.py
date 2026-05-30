from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    InvalidSymbolError,
    NotFoundError,
    PiPMError,
    ProviderError,
    RankingError,
    StrategyNotFoundError,
    ValidationError,
)
from app.core.logging import setup_logging
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    setup_logging(settings)
    yield
    dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Pi-PM",
        description="Personal Intelligence Portfolio Manager",
        version="0.4.1",
        lifespan=lifespan,
        debug=settings.debug,
    )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidSymbolError)
    async def invalid_symbol_handler(_request: Request, exc: InvalidSymbolError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ProviderError)
    async def provider_error_handler(_request: Request, exc: ProviderError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(StrategyNotFoundError)
    async def strategy_not_found_handler(_request: Request, exc: StrategyNotFoundError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(RankingError)
    async def ranking_error_handler(_request: Request, exc: RankingError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def validation_error_handler(_request: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(PiPMError)
    async def pipm_error_handler(_request: Request, exc: PiPMError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
