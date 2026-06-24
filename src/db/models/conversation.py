# src/db/models/conversation.py
"""Persistent conversation storage (MongoDB)."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Conversation(BaseModel):
    """A conversation session within a tenant."""

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    tenant_id: str
    user_id: Optional[str] = None
    title: str = Field(default="New Conversation")
    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class ConversationMessage(BaseModel):
    """Individual message within a conversation."""

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    conversation_id: str
    role: str = Field(..., description="user or assistant")
    content: str
    citations: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
