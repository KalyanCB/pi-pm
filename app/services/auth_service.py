"""Authentication service — login, refresh, logout, registration."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.constants import UserRole
from app.auth.context import AuthContext
from app.auth.exceptions import AuthenticationError, AuthorizationError, TokenError
from app.auth.jwt import create_access_token, create_refresh_token_value, decode_access_token
from app.auth.password import hash_password, verify_password
from app.core.config import Settings, get_settings
from app.db.repositories.auth_repository import (
    PortfolioRepository,
    RefreshTokenRepository,
    UserPortfolioRepository,
    UserPreferenceRepository,
    UserRepository,
)
from app.models.auth import User


class AuthService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.users = UserRepository(db)
        self.preferences = UserPreferenceRepository(db)
        self.portfolios = PortfolioRepository(db)
        self.memberships = UserPortfolioRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    # ── Public API ────────────────────────────────────────────────────────────

    def register_user(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        role: UserRole = UserRole.OWNER,
        portfolio_name: str | None = None,
    ) -> User:
        if self.users.get_by_email(email):
            raise AuthenticationError("Email already registered")

        user = self.users.create(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
        )
        self.preferences.create_default(user.id)

        slug = email.split("@")[0].lower().replace(".", "-")[:48]
        portfolio = self.portfolios.create(
            name=portfolio_name or f"{display_name}'s Portfolio",
            slug=f"{slug}-{str(user.id)[:8]}",
        )
        self.memberships.create_membership(
            user_id=user.id,
            portfolio_id=portfolio.id,
            role=role,
        )
        self.db.commit()
        return user

    def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> dict:
        user = self.users.get_by_email(email)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid email or password")
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        return self._issue_tokens(user, user_agent=user_agent, ip_address=ip_address)

    def refresh(
        self,
        refresh_token: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> dict:
        token_hash = self._hash_token(refresh_token)
        stored = self.refresh_tokens.get_by_hash(token_hash)
        if stored is None:
            raise TokenError("Invalid refresh token")
        if stored.revoked_at is not None:
            raise TokenError("Refresh token has been revoked")
        expires_at = stored.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            raise TokenError("Refresh token has expired")

        user = self.users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User account is inactive")

        # Token rotation — revoke old, issue new
        new_refresh_value = create_refresh_token_value()
        new_stored = self.refresh_tokens.create(
            user_id=user.id,
            token_hash=self._hash_token(new_refresh_value),
            expires_at=datetime.now(UTC)
            + timedelta(days=self.settings.jwt_refresh_token_days),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.refresh_tokens.revoke(stored, replaced_by_id=new_stored.id)

        ctx = self.build_auth_context(user)
        access_token, expires_at = create_access_token(
            user_id=user.id,
            email=user.email,
            roles=ctx.roles,
            portfolio_id=ctx.portfolio_id,
            settings=self.settings,
        )
        self.db.commit()
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_value,
            "token_type": "bearer",
            "expires_at": expires_at.isoformat(),
            "user": self._user_payload(user, ctx),
        }

    def logout(self, refresh_token: str) -> None:
        token_hash = self._hash_token(refresh_token)
        stored = self.refresh_tokens.get_by_hash(token_hash)
        if stored and stored.revoked_at is None:
            self.refresh_tokens.revoke(stored)
            self.db.commit()

    def logout_all(self, user_id: UUID) -> int:
        count = self.refresh_tokens.revoke_all_for_user(user_id)
        self.db.commit()
        return count

    def authenticate_access_token(self, token: str) -> AuthContext:
        payload = decode_access_token(token, self.settings)
        user_id = UUID(payload["sub"])
        user = self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User account is inactive")
        return self.build_auth_context(user)

    def build_auth_context(self, user: User) -> AuthContext:
        memberships = self.memberships.list_for_user(user.id)
        roles: list[UserRole] = []
        portfolio_id: UUID | None = None

        if user.is_superuser:
            roles.append(UserRole.ADMIN)

        for m in memberships:
            try:
                roles.append(UserRole(m.role))
            except ValueError:
                continue
            if portfolio_id is None:
                portfolio_id = m.portfolio_id

        if not roles and user.is_superuser:
            roles = [UserRole.ADMIN]
        elif not roles:
            roles = [UserRole.VIEWER]

        return AuthContext(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            roles=tuple(dict.fromkeys(roles)),
            portfolio_id=portfolio_id,
            is_superuser=user.is_superuser,
        )

    def assert_portfolio_access(self, ctx: AuthContext, portfolio_id: UUID) -> None:
        if ctx.is_superuser:
            return
        if not self.memberships.user_has_portfolio_access(ctx.user_id, portfolio_id):
            raise AuthorizationError("Access denied to this portfolio")

    def get_user_profile(self, user_id: UUID) -> dict:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found")
        ctx = self.build_auth_context(user)
        pref = self.preferences.get_for_user(user_id)
        memberships = self.memberships.list_for_user(user_id)
        return {
            **self._user_payload(user, ctx),
            "preferences": {
                "timezone": pref.timezone if pref else "Asia/Kolkata",
                "locale": pref.locale if pref else "en-IN",
                "settings": pref.settings if pref else {},
            },
            "portfolios": [
                {
                    "portfolio_id": str(m.portfolio_id),
                    "role": m.role,
                    "name": m.portfolio.name if m.portfolio else None,
                }
                for m in memberships
            ],
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _issue_tokens(
        self,
        user: User,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> dict:
        ctx = self.build_auth_context(user)
        access_token, expires_at = create_access_token(
            user_id=user.id,
            email=user.email,
            roles=ctx.roles,
            portfolio_id=ctx.portfolio_id,
            settings=self.settings,
        )
        refresh_value = create_refresh_token_value()
        self.refresh_tokens.create(
            user_id=user.id,
            token_hash=self._hash_token(refresh_value),
            expires_at=datetime.now(UTC)
            + timedelta(days=self.settings.jwt_refresh_token_days),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.commit()
        return {
            "access_token": access_token,
            "refresh_token": refresh_value,
            "token_type": "bearer",
            "expires_at": expires_at.isoformat(),
            "user": self._user_payload(user, ctx),
        }

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _user_payload(user: User, ctx: AuthContext) -> dict:
        return {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "roles": [r.value for r in ctx.roles],
            "portfolio_id": str(ctx.portfolio_id) if ctx.portfolio_id else None,
        }
