"""Kite Connect OAuth flow endpoints.

GET  /api/v1/ops/kite/login    — returns the Zerodha login URL
GET  /api/v1/ops/kite/callback — Zerodha redirects here with ?request_token=...
POST /api/v1/ops/kite/token    — manually set access_token (for scripted refresh)
GET  /api/v1/ops/kite/status   — check whether a valid token is stored
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings

router = APIRouter(prefix="/ops/kite", tags=["kite-auth"])


def _get_provider():
    settings = get_settings()
    if not settings.kite_api_key:
        raise HTTPException(status_code=503, detail="KITE_API_KEY not configured")
    from app.providers.kite import token_store
    from app.providers.kite.client import KiteConnectProvider
    # We need some token to instantiate — use stored one or empty (login-url only needs api_key)
    token = settings.kite_access_token or "placeholder"
    try:
        from kiteconnect import KiteConnect  # type: ignore[import]
        kite = KiteConnect(api_key=settings.kite_api_key)
        kite.set_access_token(token)
        return kite
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="kiteconnect package not installed") from exc


@router.get("/login")
def kite_login():
    """Return the Zerodha login URL. Visit it in a browser to authenticate."""
    settings = get_settings()
    if not settings.kite_api_key:
        raise HTTPException(status_code=503, detail="KITE_API_KEY not configured")
    try:
        from kiteconnect import KiteConnect  # type: ignore[import]
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="kiteconnect package not installed") from exc

    kite = KiteConnect(api_key=settings.kite_api_key)
    return {"login_url": kite.login_url()}


@router.get("/callback")
def kite_callback(
    request_token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Zerodha redirects here after login with ?request_token=...
    Exchanges for access_token and persists it to DB.
    """
    settings = get_settings()
    if not settings.kite_api_key or not settings.kite_api_secret:
        raise HTTPException(status_code=503, detail="KITE_API_KEY / KITE_API_SECRET not configured")
    try:
        from kiteconnect import KiteConnect  # type: ignore[import]
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="kiteconnect package not installed") from exc

    kite = KiteConnect(api_key=settings.kite_api_key)
    try:
        session = kite.generate_session(request_token, api_secret=settings.kite_api_secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {exc}") from exc

    access_token = session["access_token"]
    from app.providers.kite import token_store
    token_store.save_token(db, access_token)

    return {
        "status": "authenticated",
        "user_id": session.get("user_id"),
        "login_time": str(session.get("login_time", "")),
        "message": "Access token saved. Kite data ingestion is now active.",
    }


class TokenRequest(BaseModel):
    access_token: str


@router.post("/token")
def set_access_token(body: TokenRequest, db: Session = Depends(get_db)):
    """Manually set (or refresh) the Kite access token — for scripted daily renewal."""
    from app.providers.kite import token_store
    token_store.save_token(db, body.access_token)
    return {"status": "saved"}


@router.get("/status")
def kite_status(db: Session = Depends(get_db)):
    """Check whether a Kite access token is available."""
    settings = get_settings()
    configured = bool(settings.kite_api_key)

    from app.providers.kite import token_store
    token = token_store.get_token(db)

    provider = settings.market_data_provider if hasattr(settings, "market_data_provider") else "yahoo"

    return {
        "active_provider": provider,
        "kite_api_key_set": configured,
        "access_token_available": bool(token),
        "note": "Visit /api/v1/ops/kite/login to authenticate" if not token else "Ready",
    }
