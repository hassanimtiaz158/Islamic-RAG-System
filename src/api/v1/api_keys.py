# src/api/v1/api_keys.py
"""API key management endpoints (MongoDB)."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from src.auth.api_keys import generate_api_key
from src.auth.dependencies import AuthContext, require_auth
from src.db.database import get_database

router = APIRouter(tags=["api-keys"])


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(default="Default", max_length=100)
    expires_days: Optional[int] = Field(default=90, ge=1, le=365)


class APIKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    key: Optional[str] = None
    expires_at: Optional[datetime]
    created_at: datetime


@router.get("/api-keys")
async def list_api_keys(
    auth: AuthContext = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List all API keys for the authenticated tenant."""
    cursor = db.api_keys.find({"tenant_id": auth.tenant_id}).sort("created_at", -1)
    keys = []
    async for k in cursor:
        keys.append({
            "id": k["_id"],
            "name": k.get("name", ""),
            "prefix": k.get("key_prefix", ""),
            "expires_at": k.get("expires_at"),
            "last_used_at": k.get("last_used_at"),
            "is_active": k.get("is_active", True),
            "created_at": k["created_at"],
        })
    return keys


@router.post("/api-keys", response_model=APIKeyResponse, status_code=201)
async def create_api_key(
    req: CreateAPIKeyRequest,
    auth: AuthContext = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Create a new API key. The full key is only returned once."""
    full_key, key_hash, key_prefix = generate_api_key()

    now = datetime.utcnow()
    api_key_doc = {
        "_id": str(uuid4()),
        "tenant_id": auth.tenant_id,
        "user_id": auth.user_id,
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "name": req.name,
        "scopes": [],
        "expires_at": now + timedelta(days=req.expires_days) if req.expires_days else None,
        "last_used_at": None,
        "is_active": True,
        "created_at": now,
    }
    await db.api_keys.insert_one(api_key_doc)

    return APIKeyResponse(
        id=api_key_doc["_id"],
        name=api_key_doc["name"],
        prefix=api_key_doc["key_prefix"],
        key=full_key,  # Only time this is shown
        expires_at=api_key_doc["expires_at"],
        created_at=api_key_doc["created_at"],
    )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    auth: AuthContext = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Revoke (deactivate) an API key."""
    result = await db.api_keys.update_one(
        {"_id": key_id, "tenant_id": auth.tenant_id},
        {"$set": {"is_active": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"status": "revoked", "id": key_id}
