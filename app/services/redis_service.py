import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """Centralised async Redis client for blacklist, cache, and health checks."""

    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Token blacklist ──────────────────────────────────────────────────────

    async def blacklist_token(self, jti: str, ttl_seconds: int) -> None:
        """Mark a JWT jti as revoked for the remainder of its lifetime."""
        if ttl_seconds <= 0:
            return
        client = await self._get_client()
        await client.setex(f"blacklist:{jti}", ttl_seconds, "1")

    async def is_token_blacklisted(self, jti: str) -> bool:
        client = await self._get_client()
        return await client.exists(f"blacklist:{jti}") == 1

    # ── Generic cache ────────────────────────────────────────────────────────

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        client = await self._get_client()
        await client.setex(f"cache:{key}", ttl_seconds, value)

    async def get(self, key: str) -> str | None:
        client = await self._get_client()
        return await client.get(f"cache:{key}")

    async def delete(self, key: str) -> None:
        client = await self._get_client()
        await client.delete(f"cache:{key}")

    # ── Health check ─────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        try:
            client = await self._get_client()
            return bool(await client.ping())
        except Exception as exc:
            logger.warning("Redis ping failed: %s", exc)
            return False


redis_service = RedisService()
