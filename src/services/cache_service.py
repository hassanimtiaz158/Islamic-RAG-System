# src/services/cache_service.py
"""Redis-based caching service (replaces in-memory dicts).

Redis is imported lazily so the application can boot (and degrade to an
in-memory cache) even when redis is not installed or configured.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from src.config.settings import get_settings

logger = logging.getLogger("islamic-rag.cache")

settings = get_settings()

_redis_client = None
_redis_available: Optional[bool] = None

# In-memory fallback cache used when Redis is unavailable.
_MEMORY_CACHE: dict = {}
_MEMORY_TTL: dict = {}


async def _get_redis_client():
    """Get or create the Redis connection (lazy). Returns None if unavailable."""
    global _redis_client, _redis_available
    if _redis_available is False:
        return None
    if _redis_client is None:
        try:
            import redis.asyncio as redis

            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis_available = True
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory cache: {e}")
            _redis_available = False
            return None
    return _redis_client


async def cache_get(key: str) -> Optional[dict]:
    """Get cached response by key."""
    r = await _get_redis_client()
    if r is not None:
        try:
            data = await r.get(f"response:{key}")
            return json.loads(data) if data else None
        except Exception:
            pass
    # In-memory fallback
    import time

    entry = _MEMORY_CACHE.get(key)
    if entry is None:
        return None
    if key in _MEMORY_TTL and time.time() > _MEMORY_TTL[key]:
        _MEMORY_CACHE.pop(key, None)
        _MEMORY_TTL.pop(key, None)
        return None
    return entry


async def cache_set(key: str, data: dict, ttl: int = 300) -> None:
    """Cache a response with TTL (default 5 minutes)."""
    r = await _get_redis_client()
    if r is not None:
        try:
            await r.setex(f"response:{key}", ttl, json.dumps(data))
            return
        except Exception:
            pass
    # In-memory fallback
    import time

    _MEMORY_CACHE[key] = data
    _MEMORY_TTL[key] = time.time() + ttl


async def cache_delete(key: str) -> None:
    """Delete a cached response."""
    r = await _get_redis_client()
    if r is not None:
        try:
            await r.delete(f"response:{key}")
        except Exception:
            pass
    _MEMORY_CACHE.pop(key, None)
    _MEMORY_TTL.pop(key, None)


async def rate_limit_check(tenant_id: str, max_rpm: int = 60) -> bool:
    """Check if tenant is within rate limit. Returns True if allowed."""
    r = await _get_redis_client()
    if r is not None:
        try:
            key = f"ratelimit:{tenant_id}"
            current = await r.incr(key)
            if current == 1:
                await r.expire(key, 60)  # 1-minute window
            return current <= max_rpm
        except Exception:
            pass
    # In-memory fallback (best-effort, not shared across workers)
    return True


async def close_redis() -> None:
    """Close Redis connection on shutdown."""
    global _redis_client, _redis_available
    if _redis_client:
        try:
            await _redis_client.close()
        except Exception:
            pass
        _redis_client = None
    _redis_available = None
