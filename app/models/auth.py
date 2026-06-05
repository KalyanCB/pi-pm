"""User, role, preference, and portfolio ownership models."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    preferences: Mapped[UserPreference | None] = relationship(
        back_populates="user", uselist=False
    )
    portfolio_memberships: Mapped[list[UserPortfolioMembership]] = relationship(
        back_populates="user"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="user")


class Role(Base, UUIDPrimaryKeyMixin):
    """Named role catalog (admin, owner, viewer)."""

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(256))

    permissions: Mapped[list[RolePermission]] = relationship(back_populates="role")


class PermissionRecord(Base, UUIDPrimaryKeyMixin):
    """Permission catalog for RBAC."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(256))

    roles: Mapped[list[RolePermission]] = relationship(back_populates="permission")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[PermissionRecord] = relationship(back_populates="roles")


class UserPreference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_preferences"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en-IN")
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    user: Mapped[User] = relationship(back_populates="preferences")


class Portfolio(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Logical portfolio container for multi-user ownership."""

    __tablename__ = "portfolios"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    memberships: Mapped[list[UserPortfolioMembership]] = relationship(back_populates="portfolio")

    __table_args__ = (Index("ix_portfolios_slug", "slug"),)


class UserPortfolioMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Maps users to portfolios with a scoped role."""

    __tablename__ = "user_portfolio_memberships"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    portfolio_id: Mapped[UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="owner")

    user: Mapped[User] = relationship(back_populates="portfolio_memberships")
    portfolio: Mapped[Portfolio] = relationship(back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("user_id", "portfolio_id", name="uq_user_portfolio_membership"),
        Index("ix_user_portfolio_memberships_user", "user_id"),
        Index("ix_user_portfolio_memberships_portfolio", "portfolio_id"),
    )


class RefreshToken(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(512))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    __table_args__ = (Index("ix_refresh_tokens_user_id", "user_id"),)
