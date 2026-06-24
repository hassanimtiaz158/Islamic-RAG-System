# src/db/models/api_key.py
"""API key model for programmatic access (MongoDB)."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class APIKey(BaseModel):
    """API key for programmatic access to the RAG API."""

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    tenant_id: str
    user_id: Optional[str] = None
    key_hash: str
    key_prefix: str = Field(..., description="First 8 chars for display")
    name: str = Field(default="Default")
    scopes: list[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
