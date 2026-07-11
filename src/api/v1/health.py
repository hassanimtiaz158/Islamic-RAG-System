# src/api/v1/health.py
"""Health check endpoint with deep connectivity tests."""

import time
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from src.config.settings import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str = "2.0.0"
    environment: str = "development"
    rag_available: bool = False
    db_connected: bool = False
    redis_connected: bool = False
    response_time_ms: Optional[float] = None


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Deep health check with connectivity tests."""
    start = time.time()
    db_ok = False
    rag_ok = False

    # Check MongoDB
    try:
        from src.db.database import get_database
        db = get_database()
        await db.command("ping")
        db_ok = True
    except Exception:
        pass

    # Check RAG pipeline (lazy import to avoid startup dependency)
    try:
        from src.api.main import graph
        rag_ok = graph is not None
    except Exception:
        pass

    # Check Redis (optional, don't fail if not configured)
    redis_ok = False
    try:
        from src.services.cache_service import get_redis
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        pass

    elapsed = (time.time() - start) * 1000
    settings = get_settings()

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        environment="production" if not settings.DEBUG else "development",
        rag_available=rag_ok,
        db_connected=db_ok,
        redis_connected=redis_ok,
        response_time_ms=round(elapsed, 2),
    )
