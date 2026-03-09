"""Shared authentication — Keycloak OAuth2.0 JWT validation."""

from shared.auth.middleware import get_current_user, require_role, TokenPayload

__all__ = ["get_current_user", "require_role", "TokenPayload"]
