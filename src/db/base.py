# src/db/base.py
"""Base utilities for MongoDB document models."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4


def generate_id() -> str:
    """Generate a UUID4 string for document _id."""
    return str(uuid4())


def now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()


class DocumentMixin:
    """Mixin providing common document fields and methods."""

    @staticmethod
    def to_doc(obj: Any) -> dict:
        """Convert a model to a MongoDB document dict."""
        if hasattr(obj, "model_dump"):
            data = obj.model_dump()
        elif hasattr(obj, "__dict__"):
            data = obj.__dict__.copy()
        else:
            return {}

        # Convert UUIDs to strings
        for key, value in data.items():
            if isinstance(value, UUID):
                data[key] = str(value)
            elif isinstance(value, datetime):
                data[key] = value
        return data
