from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings, parse_cors_origins
from app.auth.exceptions import AuthenticationError, AuthorizationError, TokenError
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
from app.core.middleware import RequestContextMiddleware
from app.core.startup import validate_startup
from app.db.session import dispose_engine


def _error_body(detail: str, *, error_code: str | None = None) -> dict:
    body: dict = {"detail": detail}
    if error_code:
        body["error_code"] = error_code
    return body


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    setup_logging(settings)
    fail_fast = settings.app_env == "production"
    validate_startup(settings, fail_fast=fail_fast)
    yield
    dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Pi-PM",
        description=(
            "Personal Intelligence Portfolio Manager — deterministic ranking, "
            "validation, traceability, and regime policy research for Indian NSE equities."
        ),
        version="0.4.1",
        lifespan=lifespan,
        debug=settings.debug,
        openapi_tags=[
            {"name": "health", "description": "Liveness, readiness, and health probes"},
            {"name": "stocks", "description": "Stock master data"},
            {"name": "market-data", "description": "Market data ingestion and queries"},
            {"name": "rankings", "description": "Deterministic ranking engine"},
            {"name": "validation", "description": "Signal validation and IC analytics"},
            {"name": "observability", "description": "Platform traceability and run lineage"},
            {"name": "recommendations", "description": "Daily recommendation lifecycle"},
            {"name": "portfolio", "description": "Portfolio positions and limits"},
            {"name": "copilot", "description": "Grounded Q&A over platform data"},
        ],
    )

    cors_origins = parse_cors_origins(settings.cors_allowed_origins)
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "X-Correlation-ID"],
        )

    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                {
                    "detail": exc.errors(),
                    "error_code": "validation_error",
                }
            ),
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content=_error_body(str(exc), error_code="not_found"),
        )

    @app.exception_handler(InvalidSymbolError)
    async def invalid_symbol_handler(_request: Request, exc: InvalidSymbolError):
        return JSONResponse(
            status_code=422,
            content=_error_body(str(exc), error_code="invalid_symbol"),
        )

    @app.exception_handler(ProviderError)
    async def provider_error_handler(_request: Request, exc: ProviderError):
        return JSONResponse(
            status_code=502,
            content=_error_body(str(exc), error_code="provider_error"),
        )

    @app.exception_handler(StrategyNotFoundError)
    async def strategy_not_found_handler(_request: Request, exc: StrategyNotFoundError):
        return JSONResponse(
            status_code=422,
            content=_error_body(str(exc), error_code="strategy_not_found"),
        )

    @app.exception_handler(RankingError)
    async def ranking_error_handler(_request: Request, exc: RankingError):
        return JSONResponse(
            status_code=500,
            content=_error_body(str(exc), error_code="ranking_error"),
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(_request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content=_error_body(str(exc), error_code="validation_error"),
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(_request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=401,
            content=_error_body(str(exc), error_code="authentication_error"),
        )

    @app.exception_handler(TokenError)
    async def token_error_handler(_request: Request, exc: TokenError):
        return JSONResponse(
            status_code=401,
            content=_error_body(str(exc), error_code="token_error"),
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(_request: Request, exc: AuthorizationError):
        return JSONResponse(
            status_code=403,
            content=_error_body(str(exc), error_code="authorization_error"),
        )

    @app.exception_handler(PiPMError)
    async def pipm_error_handler(_request: Request, exc: PiPMError):
        return JSONResponse(
            status_code=400,
            content=_error_body(str(exc), error_code="application_error"),
        )

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
