"""Simple JWT token validation middleware for FastAPI.

Self-contained JWT authentication — no external identity provider needed.
Tokens are signed with a symmetric secret (HS256).

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

from datetime import datetime, timedelta, timezone

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from shared.config.settings import get_settings

logger = structlog.get_logger(__name__)

_security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str  # user id
    preferred_username: str = ""
    email: str = ""
    roles: list[str] = []
    exp: int = 0


def create_access_token(
    sub: str,
    username: str = "",
    email: str = "",
    roles: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))

    payload = {
        "sub": sub,
        "preferred_username": username,
        "email": email,
        "roles": roles or [],
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    settings = get_settings()

    try:
        payload: dict = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> TokenPayload:
    """FastAPI dependency — validates JWT and returns user info.

    Usage:
        @router.get("/me")
        async def me(user: TokenPayload = Depends(get_current_user)):
            return user
    """
    settings = get_settings()

    if settings.dev_mode:
        return TokenPayload(
            sub="dev-user-id",
            preferred_username="dev-admin",
            roles=["agent-operator", "agent-supervisor"],
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(credentials.credentials)

    return TokenPayload(
        sub=payload.get("sub", ""),
        preferred_username=payload.get("preferred_username", ""),
        email=payload.get("email", ""),
        roles=payload.get("roles", []),
        exp=payload.get("exp", 0),
    )


def require_role(role: str):
    """FastAPI dependency factory — requires a specific role.

    Usage:
        @router.delete("/admin-only")
        async def admin(user: TokenPayload = Depends(require_role("agent-supervisor"))):
            ...
    """

    async def _check_role(
        user: TokenPayload = Depends(get_current_user),
    ) -> TokenPayload:
        settings = get_settings()
        if settings.dev_mode:
            return user

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
