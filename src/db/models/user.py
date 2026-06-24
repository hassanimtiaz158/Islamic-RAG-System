# src/db/models/user.py
"""User model with tenant-scoped roles (MongoDB)."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, EmailStr


class UserRole:
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class User(BaseModel):
    """User belonging to a tenant."""

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    tenant_id: str
    email: str
    hashed_password: str
    role: str = Field(default=UserRole.MEMBER)
    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    class Config:
        populate_by_name = True

    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.OWNER, UserRole.ADMIN)

    @property
    def is_owner(self) -> bool:
        return self.role == UserRole.OWNER
