"""Request-scoped context for correlation, tracing, and authentication."""

from __future__ import annotations

from contextvars import ContextVar

from app.auth.context import AuthContext

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
current_user_var: ContextVar[AuthContext | None] = ContextVar("current_user", default=None)
