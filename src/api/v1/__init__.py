# src/api/v1/__init__.py
"""API v1 router aggregation."""

from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.ask import router as ask_router
from src.api.v1.health import router as health_router
from src.api.v1.api_keys import router as api_keys_router
from src.api.v1.tenants import router as tenants_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_router)
v1_router.include_router(ask_router)
v1_router.include_router(health_router)
v1_router.include_router(api_keys_router)
v1_router.include_router(tenants_router)
