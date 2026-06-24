# src/db/__init__.py
"""MongoDB database layer for Al-Ilm SaaS platform."""

from src.db.database import db, get_db, init_db
from src.db.models.tenant import Tenant
from src.db.models.user import User
from src.db.models.api_key import APIKey
from src.db.models.usage_record import UsageRecord
from src.db.models.conversation import Conversation, ConversationMessage
from src.db.models.document import Document

__all__ = [
    "db",
    "get_db",
    "init_db",
    "Tenant",
    "User",
    "APIKey",
    "UsageRecord",
    "Conversation",
    "ConversationMessage",
    "Document",
]
