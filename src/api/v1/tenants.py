# src/api/v1/tenants.py
"""Tenant management endpoints (admin only) (MongoDB)."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from src.auth.dependencies import AuthContext, require_role
from src.db.database import get_database

router = APIRouter(tags=["tenants"])


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    is_active: bool
    rate_limit: int
    created_at: str


class TenantUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    plan: Optional[str] = Field(None, pattern="^(free|pro|enterprise)$")
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)
    is_active: Optional[bool] = None


@router.get("/tenants/me", response_model=TenantResponse)
async def get_my_tenant(
    auth: AuthContext = Depends(require_role("owner", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get current tenant info."""
    doc = await db.tenants.find_one({"_id": auth.tenant_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return TenantResponse(
        id=doc["_id"],
        name=doc["name"],
        slug=doc["slug"],
        plan=doc["plan"],
        is_active=doc.get("is_active", True),
        rate_limit=doc.get("rate_limit", 60),
        created_at=doc["created_at"].isoformat() if "created_at" in doc else "",
    )


@router.patch("/tenants/me", response_model=TenantResponse)
async def update_tenant(
    req: TenantUpdateRequest,
    auth: AuthContext = Depends(require_role("owner", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update tenant settings (owner/admin only)."""
    updates = req.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.utcnow()
    await db.tenants.update_one(
        {"_id": auth.tenant_id},
        {"$set": updates},
    )

    doc = await db.tenants.find_one({"_id": auth.tenant_id})
    return TenantResponse(
        id=doc["_id"],
        name=doc["name"],
        slug=doc["slug"],
        plan=doc["plan"],
        is_active=doc.get("is_active", True),
        rate_limit=doc.get("rate_limit", 60),
        created_at=doc["created_at"].isoformat() if "created_at" in doc else "",
    )


@router.get("/tenants/me/users")
async def list_tenant_users(
    auth: AuthContext = Depends(require_role("owner", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List all users in the tenant."""
    cursor = db.users.find({"tenant_id": auth.tenant_id}).sort("created_at", -1)
    users = []
    async for u in cursor:
        users.append({
            "id": u["_id"],
            "email": u["email"],
            "role": u.get("role", "member"),
            "is_active": u.get("is_active", True),
            "created_at": u["created_at"].isoformat() if "created_at" in u else "",
            "last_login": u["last_login"].isoformat() if u.get("last_login") else None,
        })
    return users
