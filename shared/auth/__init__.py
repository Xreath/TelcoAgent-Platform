"""Shared authentication — Simple JWT validation."""

from shared.auth.middleware import TokenPayload, create_access_token, get_current_user, require_role

__all__ = ["get_current_user", "require_role", "TokenPayload", "create_access_token"]
