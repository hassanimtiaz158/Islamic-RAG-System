# src/api/v1/auth.py
"""Authentication endpoints: login, register, token refresh, me (MongoDB)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.auth.api_keys import generate_api_key
from src.auth.dependencies import AuthContext, get_auth_context
from src.auth.jwt import create_access_token, create_refresh_token, decode_token
from src.auth.passwords import hash_password, verify_password
from src.db.database import get_database
from src.db.models.user import User, UserRole
from src.services.tenant_service import create_tenant

router = APIRouter(tags=["auth"])


# ── Request/Response Models ──

class RegisterRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=8, max_length=128)
    organization: str = Field(..., min_length=2, max_length=100)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    tenant_id: str
    created_at: datetime


# ── Endpoints ──

@router.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Register a new user with a new organization."""
    # Check if email already exists
    existing = await db.users.find_one({"email": req.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create tenant
    slug = re.sub(r"[^a-z0-9]+", "-", req.organization.lower())[:60].strip("-")
    if not slug:
        slug = f"org-{uuid4().hex[:8]}"

    # Ensure unique slug
    while await db.tenants.find_one({"slug": slug}):
        slug = f"{slug}-{uuid4().hex[:4]}"

    tenant = await create_tenant(db, name=req.organization, slug=slug)

    # Create user as owner
    user = User(
        tenant_id=tenant.id,
        email=req.email,
        hashed_password=hash_password(req.password),
        role=UserRole.OWNER,
    )
    await db.users.insert_one(user.model_dump(by_alias=True))

    # Generate tokens
    access_token = create_access_token(user.id, tenant.id, user.role)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Login with email and password."""
    user_doc = await db.users.find_one({"email": req.email})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(req.password, user_doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last login
    await db.users.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {"last_login": datetime.utcnow()}},
    )

    access_token = create_access_token(
        user_doc["_id"], user_doc["tenant_id"], user_doc["role"]
    )
    refresh_token = create_refresh_token(user_doc["_id"])

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Refresh an access token using a refresh token."""
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc or not user_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token = create_access_token(
        user_doc["_id"], user_doc["tenant_id"], user_doc["role"]
    )
    new_refresh_token = create_refresh_token(user_doc["_id"])

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_me(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get current user info."""
    if auth is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_doc = await db.users.find_one({"_id": auth.user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user_doc["_id"],
        email=user_doc["email"],
        role=user_doc["role"],
        tenant_id=user_doc["tenant_id"],
        created_at=user_doc["created_at"],
    )
