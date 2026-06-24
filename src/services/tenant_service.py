# src/services/tenant_service.py
"""Tenant management service (MongoDB)."""

from typing import Optional
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.db.models.tenant import Tenant


async def get_tenant(db: AsyncIOMotorDatabase, tenant_id: str) -> Optional[Tenant]:
    """Get tenant by ID."""
    doc = await db.tenants.find_one({"_id": tenant_id})
    if doc:
        return Tenant(**doc)
    return None


async def get_tenant_by_slug(db: AsyncIOMotorDatabase, slug: str) -> Optional[Tenant]:
    """Get tenant by slug."""
    doc = await db.tenants.find_one({"slug": slug})
    if doc:
        return Tenant(**doc)
    return None


async def create_tenant(
    db: AsyncIOMotorDatabase,
    name: str,
    slug: str,
    plan: str = "free",
) -> Tenant:
    """Create a new tenant."""
    tenant = Tenant(name=name, slug=slug, plan=plan)
    doc = tenant.model_dump(by_alias=True)
    await db.tenants.insert_one(doc)
    return tenant


async def get_default_tenant(db: AsyncIOMotorDatabase) -> Tenant:
    """Get or create the default tenant for backward compatibility."""
    tenant = await get_tenant_by_slug(db, "default")
    if not tenant:
        tenant = await create_tenant(
            db,
            name="Default Tenant",
            slug="default",
            plan="enterprise",
        )
    return tenant


async def update_tenant(
    db: AsyncIOMotorDatabase,
    tenant_id: str,
    updates: dict,
) -> Optional[Tenant]:
    """Update tenant settings."""
    from datetime import datetime
    updates["updated_at"] = datetime.utcnow()
    await db.tenants.update_one(
        {"_id": tenant_id},
        {"$set": updates},
    )
    return await get_tenant(db, tenant_id)
