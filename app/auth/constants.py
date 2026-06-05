"""Auth role and permission constants."""
from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    OWNER = "owner"
    VIEWER = "viewer"


class Permission(StrEnum):
    # Portfolio
    PORTFOLIO_READ = "portfolio:read"
    PORTFOLIO_WRITE = "portfolio:write"
    # Recommendations
    RECOMMENDATION_READ = "recommendation:read"
    RECOMMENDATION_APPROVE = "recommendation:approve"
    RECOMMENDATION_RUN = "recommendation:run"
    # Committee
    COMMITTEE_READ = "committee:read"
    COMMITTEE_RUN = "committee:run"
    # Copilot
    COPILOT_ASK = "copilot:ask"
    COPILOT_AUDIT = "copilot:audit"
    # Analytics
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_RUN = "analytics:run"
    # Platform ops
    OPS_ADMIN = "ops:admin"
    USER_ADMIN = "user:admin"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset(Permission),
    UserRole.OWNER: frozenset(
        {
            Permission.PORTFOLIO_READ,
            Permission.PORTFOLIO_WRITE,
            Permission.RECOMMENDATION_READ,
            Permission.RECOMMENDATION_APPROVE,
            Permission.RECOMMENDATION_RUN,
            Permission.COMMITTEE_READ,
            Permission.COMMITTEE_RUN,
            Permission.COPILOT_ASK,
            Permission.COPILOT_AUDIT,
            Permission.ANALYTICS_READ,
            Permission.ANALYTICS_RUN,
        }
    ),
    UserRole.VIEWER: frozenset(
        {
            Permission.PORTFOLIO_READ,
            Permission.RECOMMENDATION_READ,
            Permission.COMMITTEE_READ,
            Permission.COPILOT_ASK,
            Permission.ANALYTICS_READ,
        }
    ),
}


def role_has_permission(role: UserRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
