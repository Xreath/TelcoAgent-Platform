"""OAuth2.0 JWT token validation middleware for FastAPI.

Validates tokens issued by Keycloak using JWKS (JSON Web Key Set).
Supports role-based access control via realm_access.roles claim.

Usage in routes:
    from shared.auth import get_current_user, require_role, TokenPayload

    # Any authenticated user
    @router.get("/protected")
    async def protected(user: TokenPayload = Depends(get_current_user)):
        return {"sub": user.sub, "roles": user.roles}

    # Require specific role
    @router.get("/admin")
    async def admin(user: TokenPayload = Depends(require_role("agent-supervisor"))):
        return {"admin": user.preferred_username}
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from shared.config.settings import get_settings

logger = structlog.get_logger(__name__)

_security = HTTPBearer(auto_error=True)

# JWKS cache
_jwks_cache: dict[str, Any] = {}
_jwks_cache_expiry: float = 0.0
_JWKS_CACHE_TTL = 300  # 5 minutes


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str  # user id
    preferred_username: str = ""
    email: str = ""
    roles: list[str] = []
    client_id: str = ""
    scope: str = ""
    exp: int = 0
    iss: str = ""


async def _get_jwks() -> dict[str, Any]:
    """Fetch and cache JWKS from Keycloak."""
    global _jwks_cache, _jwks_cache_expiry

    if _jwks_cache and time.time() < _jwks_cache_expiry:
        return _jwks_cache

    settings = get_settings()
    jwks_url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_expiry = time.time() + _JWKS_CACHE_TTL
            return _jwks_cache
    except httpx.HTTPError:
        logger.exception("jwks_fetch_failed", url=jwks_url)
        if _jwks_cache:
            logger.warning("using_stale_jwks_cache")
            return _jwks_cache
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )


def _decode_token(token: str, jwks: dict[str, Any]) -> dict[str, Any]:
    """Decode and validate a JWT token using JWKS."""
    settings = get_settings()
    issuer = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"

    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience="account",
            issuer=issuer,
            options={"verify_exp": True},
        )
        return payload
    except JWTError as e:
        logger.warning("token_decode_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extract_roles(payload: dict[str, Any]) -> list[str]:
    """Extract realm roles from Keycloak token payload."""
    realm_access = payload.get("realm_access", {})
    return realm_access.get("roles", [])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> TokenPayload:
    """FastAPI dependency — validates JWT and returns user info.

    Usage:
        @router.get("/me")
        async def me(user: TokenPayload = Depends(get_current_user)):
            return user
    """
    jwks = await _get_jwks()
    payload = _decode_token(credentials.credentials, jwks)

    return TokenPayload(
        sub=payload.get("sub", ""),
        preferred_username=payload.get("preferred_username", ""),
        email=payload.get("email", ""),
        roles=_extract_roles(payload),
        client_id=payload.get("azp", ""),
        scope=payload.get("scope", ""),
        exp=payload.get("exp", 0),
        iss=payload.get("iss", ""),
    )


def require_role(role: str):
    """FastAPI dependency factory — requires a specific Keycloak realm role.

    Usage:
        @router.delete("/admin-only")
        async def admin(user: TokenPayload = Depends(require_role("agent-supervisor"))):
            ...
    """

    async def _check_role(
        user: TokenPayload = Depends(get_current_user),
    ) -> TokenPayload:
        if role not in user.roles:
            logger.warning(
                "insufficient_role",
                required=role,
                user_roles=user.roles,
                sub=user.sub,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )
        return user

    return _check_role
