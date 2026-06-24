# src/services/conversation_service.py
"""Persistent conversation service (MongoDB)."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.db.models.conversation import Conversation, ConversationMessage

CONV_TTL_HOURS = 24


async def get_conversation(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    tenant_id: str,
) -> Optional[list[dict]]:
    """Get conversation messages if it exists, is active, and belongs to tenant."""
    conv = await db.conversations.find_one({
        "_id": conversation_id,
        "tenant_id": tenant_id,
        "is_active": True,
    })

    if not conv:
        return None

    # Check TTL
    updated_at = conv.get("updated_at", datetime.utcnow())
    if datetime.utcnow() - updated_at > timedelta(hours=CONV_TTL_HOURS):
        await db.conversations.update_one(
            {"_id": conversation_id},
            {"$set": {"is_active": False}},
        )
        return None

    # Load messages
    cursor = db.conversation_messages.find({
        "conversation_id": conversation_id,
    }).sort("created_at", 1)

    messages = []
    async for msg in cursor:
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
            "citations": msg.get("citations", []),
        })

    return messages


async def save_conversation(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    tenant_id: str,
    messages: list[dict],
) -> None:
    """Save or update a conversation."""
    # Upsert conversation
    await db.conversations.update_one(
        {"_id": conversation_id, "tenant_id": tenant_id},
        {
            "$set": {
                "updated_at": datetime.utcnow(),
                "is_active": True,
            },
            "$setOnInsert": {
                "_id": conversation_id,
                "tenant_id": tenant_id,
                "created_at": datetime.utcnow(),
            },
        },
        upsert=True,
    )

    # Append new messages
    for msg in messages:
        await db.conversation_messages.insert_one({
            "_id": str(uuid4()),
            "conversation_id": conversation_id,
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
            "citations": msg.get("citations", []),
            "metadata": msg.get("metadata", {}),
            "created_at": datetime.utcnow(),
        })


async def create_conversation(
    db: AsyncIOMotorDatabase,
    tenant_id: str,
    user_id: Optional[str] = None,
) -> Conversation:
    """Create a new conversation."""
    conv = Conversation(tenant_id=tenant_id, user_id=user_id)
    doc = conv.model_dump(by_alias=True)
    await db.conversations.insert_one(doc)
    return conv
