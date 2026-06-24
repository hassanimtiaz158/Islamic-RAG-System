# src/db/database.py
"""MongoDB async database connection using Motor."""

from collections.abc import AsyncGenerator
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.config.settings import get_settings

settings = get_settings()

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_database() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance."""
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URL)
        _db = _client[settings.MONGODB_DB_NAME]
    return _db


# Alias for backward compatibility
db = get_database


async def init_db() -> None:
    """Initialize database connection and create indexes."""
    database = get_database()

    # Create indexes for performance
    await database.tenants.create_index("slug", unique=True)
    await database.users.create_index("email", unique=True)
    await database.users.create_index("tenant_id")
    await database.api_keys.create_index("key_hash", unique=True)
    await database.api_keys.create_index("tenant_id")
    await database.usage_records.create_index([("tenant_id", 1), ("created_at", -1)])
    await database.conversations.create_index([("tenant_id", 1), ("updated_at", -1)])
    await database.conversations.create_index("is_active")
    await database.conversation_messages.create_index([("conversation_id", 1), ("created_at", 1)])
    await database.documents.create_index([("tenant_id", 1), ("status", 1)])


async def close_db() -> None:
    """Close database connection on shutdown."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """FastAPI dependency that provides a database instance."""
    database = get_database()
    try:
        yield database
    finally:
        pass  # connection managed at app level
