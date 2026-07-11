# src/db/models/usage_record.py
"""Usage tracking for billing and rate limiting (MongoDB)."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class UsageRecord(BaseModel):
    """Records each API request for billing and analytics."""

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    tenant_id: str
    user_id: Optional[str] = None
    endpoint: str
    tokens_input: int = Field(default=0)
    tokens_output: int = Field(default=0)
    cost_usd: float = Field(default=0.0)
    model: str = Field(default="")
    status_code: int = Field(default=200)
    duration_ms: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
