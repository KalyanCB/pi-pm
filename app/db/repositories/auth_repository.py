"""Data access for users, tokens, and portfolio ownership."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth.constants import UserRole
from app.models.auth import (
    Portfolio,
    RefreshToken,
    User,
    UserPortfolioMembership,
    UserPreference,
)


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        display_name: str,
        is_superuser: bool = False,
    ) -> User:
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            display_name=display_name,
            is_superuser=is_superuser,
        )
        self.db.add(user)
        self.db.flush()
        return user


class UserPreferenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_user(self, user_id: UUID) -> UserPreference | None:
        return self.db.scalar(select(UserPreference).where(UserPreference.user_id == user_id))

    def create_default(self, user_id: UUID) -> UserPreference:
        pref = UserPreference(user_id=user_id)
        self.db.add(pref)
        self.db.flush()
        return pref


class PortfolioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, portfolio_id: UUID) -> Portfolio | None:
        return self.db.get(Portfolio, portfolio_id)

    def create(self, *, name: str, slug: str, is_default: bool = False) -> Portfolio:
        portfolio = Portfolio(name=name, slug=slug, is_default=is_default)
        self.db.add(portfolio)
        self.db.flush()
        return portfolio


class UserPortfolioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_membership(self, user_id: UUID, portfolio_id: UUID) -> UserPortfolioMembership | None:
        return self.db.scalar(
            select(UserPortfolioMembership).where(
                UserPortfolioMembership.user_id == user_id,
                UserPortfolioMembership.portfolio_id == portfolio_id,
            )
        )

    def list_for_user(self, user_id: UUID) -> list[UserPortfolioMembership]:
        return list(
            self.db.scalars(
                select(UserPortfolioMembership)
                .where(UserPortfolioMembership.user_id == user_id)
                .options(joinedload(UserPortfolioMembership.portfolio))
            ).all()
        )

    def get_primary_portfolio_id(self, user_id: UUID) -> UUID | None:
        membership = self.db.scalar(
            select(UserPortfolioMembership)
            .join(Portfolio)
            .where(UserPortfolioMembership.user_id == user_id)
            .order_by(Portfolio.is_default.desc(), UserPortfolioMembership.created_at.asc())
            .limit(1)
        )
        return membership.portfolio_id if membership else None

    def create_membership(
        self,
        *,
        user_id: UUID,
        portfolio_id: UUID,
        role: UserRole = UserRole.OWNER,
    ) -> UserPortfolioMembership:
        membership = UserPortfolioMembership(
            user_id=user_id,
            portfolio_id=portfolio_id,
            role=role.value,
        )
        self.db.add(membership)
        self.db.flush()
        return membership

    def user_has_portfolio_access(self, user_id: UUID, portfolio_id: UUID) -> bool:
        return self.get_membership(user_id, portfolio_id) is not None


class RefreshTokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(token)
        self.db.flush()
        return token

    def revoke(self, token: RefreshToken, *, replaced_by_id: UUID | None = None) -> None:
        token.revoked_at = datetime.now(UTC)
        if replaced_by_id:
            token.replaced_by_id = replaced_by_id
        self.db.flush()

    def revoke_all_for_user(self, user_id: UUID) -> int:
        tokens = self.db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        ).all()
        now = datetime.now(UTC)
        for token in tokens:
            token.revoked_at = now
        self.db.flush()
        return len(tokens)
