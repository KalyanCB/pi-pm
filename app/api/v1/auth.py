"""Authentication API — login, refresh, logout, profile."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, EmailStr, Field

from app.api.auth_deps import CurrentUser, get_auth_service
from app.services.auth_service import AuthService

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: str
    user: dict


class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: str
    roles: list[str]
    portfolio_id: str | None
    preferences: dict | None = None
    portfolios: list[dict] | None = None


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    result = auth.login(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return TokenResponse(**result)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    result = auth.refresh(
        payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return TokenResponse(**result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, auth: AuthService = Depends(get_auth_service)) -> None:
    auth.logout(payload.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(user: CurrentUser, auth: AuthService = Depends(get_auth_service)) -> None:
    auth.logout_all(user.user_id)


@router.get("/me", response_model=UserProfileResponse)
def me(user: CurrentUser, auth: AuthService = Depends(get_auth_service)) -> UserProfileResponse:
    profile = auth.get_user_profile(user.user_id)
    return UserProfileResponse(**profile)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    user = auth.register_user(
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
    )
    result = auth.login(
        email=user.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return TokenResponse(**result)
