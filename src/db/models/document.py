# src/db/models/document.py
"""Tracked documents for tenant-uploaded content (MongoDB)."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Document(BaseModel):
    """Tracks uploaded documents and their indexing status."""

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    tenant_id: str
    uploaded_by: Optional[str] = None
    filename: str
    file_type: str = Field(..., description="pdf or txt")
    chunk_count: int = Field(default=0)
    collection_name: str
    status: str = Field(default="pending", description="pending, indexing, indexed, failed")
    metadata: dict = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    indexed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
