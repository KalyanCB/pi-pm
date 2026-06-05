"""Authentication and authorization exceptions."""
from __future__ import annotations

from app.core.exceptions import PiPMError


class AuthenticationError(PiPMError):
    """Invalid or missing credentials."""


class AuthorizationError(PiPMError):
    """Authenticated but not permitted."""


class TokenError(PiPMError):
    """Invalid or expired token."""
