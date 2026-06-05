"""Authenticated user context for request scope."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.auth.constants import Permission, UserRole


@dataclass(frozen=True)
class AuthContext:
    user_id: UUID
    email: str
    display_name: str
    roles: tuple[UserRole, ...]
    portfolio_id: UUID | None
    is_superuser: bool = False

    def has_role(self, *roles: UserRole) -> bool:
        if self.is_superuser:
            return True
        return any(r in self.roles for r in roles)

    def has_permission(self, permission: Permission) -> bool:
        if self.is_superuser:
            return True
        from app.auth.constants import role_has_permission

        return any(role_has_permission(r, permission) for r in self.roles)

    def require_portfolio_id(self) -> UUID:
        if self.portfolio_id is None:
            raise ValueError("No portfolio context for user")
        return self.portfolio_id
