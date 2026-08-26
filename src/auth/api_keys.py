# src/auth/api_keys.py
"""API key generation and validation."""

import hashlib
import hmac
import secrets
from typing import Tuple


API_KEY_PREFIX = "sk_live_"


def generate_api_key() -> Tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        Tuple of (full_key, key_hash, key_prefix) — full_key is shown once to
        user, key_hash is stored in the database, key_prefix is safe to display.
    """
    random_part = secrets.token_hex(24)
    full_key = f"{API_KEY_PREFIX}{random_part}"
    key_hash = hash_api_key(full_key)
    key_prefix = full_key[:8]
    return full_key, key_hash, key_prefix


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash (constant-time comparison)."""
    return hmac.compare_digest(hash_api_key(provided_key), stored_hash)
