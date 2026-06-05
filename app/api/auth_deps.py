"""FastAPI dependencies for authentication and RBAC."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.constants import Permission, UserRole
from app.auth.context import AuthContext
from app.auth.exceptions import AuthenticationError, AuthorizationError, TokenError
from app.api.deps import get_db
from app.core.config import Settings, get_settings
from app.core.context import current_user_var
from app.services.auth_service import AuthService

_bearer = HTTPBearer(auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthContext | None:
    if not settings.auth_enabled or settings.auth_bypass_for_tests:
        return _dev_bypass_user()

    if credentials is None or credentials.scheme.lower() != "bearer":
        return None

    try:
        ctx = auth_service.authenticate_access_token(credentials.credentials)
        current_user_var.set(ctx)
        return ctx
    except (AuthenticationError, TokenError):
        return None


def get_current_user(
    ctx: AuthContext | None = Depends(get_current_user_optional),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    if not settings.auth_enabled or settings.auth_bypass_for_tests:
        return _dev_bypass_user()
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return ctx


def require_permission(permission: Permission):
    def _checker(user: AuthContext = Depends(get_current_user)) -> AuthContext:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}",
            )
        return user

    return _checker


def require_roles(*roles: UserRole):
    def _checker(user: AuthContext = Depends(get_current_user)) -> AuthContext:
        if not user.has_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {[r.value for r in roles]}",
            )
        return user

    return _checker


require_owner = require_roles(UserRole.OWNER, UserRole.ADMIN)
require_admin = require_roles(UserRole.ADMIN)
require_viewer = require_roles(UserRole.VIEWER, UserRole.OWNER, UserRole.ADMIN)

# Typed aliases for route signatures
CurrentUser = Annotated[AuthContext, Depends(get_current_user)]
OwnerUser = Annotated[AuthContext, Depends(require_owner)]
AdminUser = Annotated[AuthContext, Depends(require_admin)]


def get_portfolio_scope(
    user: AuthContext = Depends(get_current_user),
    x_portfolio_id: str | None = Header(default=None, alias="X-Portfolio-Id"),
    auth_service: AuthService = Depends(get_auth_service),
) -> UUID:
    """Resolve and authorize portfolio scope for the current request."""
    portfolio_id: UUID | None
    if x_portfolio_id:
        try:
            portfolio_id = UUID(x_portfolio_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid X-Portfolio-Id") from exc
    else:
        portfolio_id = user.portfolio_id

    if portfolio_id is None:
        raise HTTPException(status_code=403, detail="No portfolio assigned to user")

    try:
        auth_service.assert_portfolio_access(user, portfolio_id)
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return portfolio_id


PortfolioScope = Annotated[UUID, Depends(get_portfolio_scope)]


def _dev_bypass_user() -> AuthContext:
    """Default owner context when auth is disabled (dev/test)."""
    from uuid import UUID

    return AuthContext(
        user_id=UUID("00000000-0000-4000-8000-000000000001"),
        email="dev@pipm.local",
        display_name="Dev Owner",
        roles=(UserRole.OWNER, UserRole.ADMIN),
        portfolio_id=UUID("00000000-0000-4000-8000-000000000010"),
        is_superuser=True,
    )
