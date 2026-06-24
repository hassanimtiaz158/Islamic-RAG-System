# src/db/models/tenant.py
"""Tenant model for multi-tenant SaaS architecture (MongoDB)."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Tenant(BaseModel):
    """Represents an organization/tenant in the SaaS platform."""

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    name: str
    slug: str = Field(..., description="URL-safe unique identifier")
    plan: str = Field(default="free", description="free, pro, or enterprise")
    is_active: bool = Field(default=True)

    # Per-tenant configuration
    config: dict = Field(default_factory=dict)
    rate_limit: int = Field(default=60, description="requests per minute")
    monthly_budget: float = Field(default=0.0, description="USD, 0 = unlimited")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "Acme Corp",
                "slug": "acme",
                "plan": "pro",
            }
        }

    @property
    def max_sources(self) -> int:
        limits = {"free": 3, "pro": 10, "enterprise": 100}
        return limits.get(self.plan, 3)

    @property
    def daily_request_limit(self) -> int:
        limits = {"free": 100, "pro": 5000, "enterprise": 100000}
        return limits.get(self.plan, 100)
