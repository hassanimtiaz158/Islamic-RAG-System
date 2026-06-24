# src/services/cache_service.py
"""Redis-based caching service (replaces in-memory dicts)."""

import json
from typing import Optional

import redis.asyncio as redis

from src.config.settings import get_settings

settings = get_settings()

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get or create Redis connection."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_client


async def cache_get(key: str) -> Optional[dict]:
    """Get cached response by key."""
    r = await get_redis()
    data = await r.get(f"response:{key}")
    return json.loads(data) if data else None


async def cache_set(key: str, data: dict, ttl: int = 300) -> None:
    """Cache a response with TTL (default 5 minutes)."""
    r = await get_redis()
    await r.setex(f"response:{key}", ttl, json.dumps(data))


async def cache_delete(key: str) -> None:
    """Delete a cached response."""
    r = await get_redis()
    await r.delete(f"response:{key}")


async def rate_limit_check(tenant_id: str, max_rpm: int = 60) -> bool:
    """Check if tenant is within rate limit. Returns True if allowed."""
    r = await get_redis()
    key = f"ratelimit:{tenant_id}"
    current = await r.incr(key)
    if current == 1:
        await r.expire(key, 60)  # 1-minute window
    return current <= max_rpm


async def close_redis() -> None:
    """Close Redis connection on shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
