"""CustomerSupportAgent — Redis-backed short-term memory.

Stores conversation history and agent state per customer session.
Uses Redis with TTL so sessions auto-expire after inactivity.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis

from shared.config.settings import get_settings

settings = get_settings()

# Default TTL: 1 hour (conversation context expires after inactivity)
DEFAULT_TTL_SECONDS = 3600


class RedisMemory:
    """Short-term memory for agent conversations, backed by Redis.

    Key schema:
        agent:session:{session_id}:messages   — conversation history (list)
        agent:session:{session_id}:metadata   — session metadata (hash)
    """

    def __init__(self, redis_url: str | None = None, ttl: int = DEFAULT_TTL_SECONDS) -> None:
        self._redis_url = redis_url or settings.redis_url
        self._ttl = ttl
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self._redis_url, decode_responses=True)
        return self._client

    def _messages_key(self, session_id: str) -> str:
        return f"agent:session:{session_id}:messages"

    def _metadata_key(self, session_id: str) -> str:
        return f"agent:session:{session_id}:metadata"

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to the session's conversation history."""
        client = await self._get_client()
        message = json.dumps(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        key = self._messages_key(session_id)
        await client.rpush(key, message)
        await client.expire(key, self._ttl)

    async def get_messages(self, session_id: str, last_n: int = 20) -> list[dict[str, Any]]:
        """Retrieve the last N messages from a session."""
        client = await self._get_client()
        key = self._messages_key(session_id)
        raw = await client.lrange(key, -last_n, -1)
        return [json.loads(m) for m in raw]

    async def set_metadata(self, session_id: str, **kwargs: Any) -> None:
        """Store session metadata (customer_id, complaint_type, etc.)."""
        client = await self._get_client()
        key = self._metadata_key(session_id)
        await client.hset(key, mapping={k: json.dumps(v) for k, v in kwargs.items()})
        await client.expire(key, self._ttl)

    async def get_metadata(self, session_id: str) -> dict[str, Any]:
        """Retrieve all session metadata."""
        client = await self._get_client()
        key = self._metadata_key(session_id)
        raw = await client.hgetall(key)
        return {k: json.loads(v) for k, v in raw.items()}

    async def clear_session(self, session_id: str) -> None:
        """Delete all data for a session."""
        client = await self._get_client()
        await client.delete(
            self._messages_key(session_id),
            self._metadata_key(session_id),
        )

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
