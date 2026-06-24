# src/auth/dependencies.py
"""FastAPI dependencies for authentication and authorization (MongoDB)."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.auth.api_keys import hash_api_key
from src.auth.jwt import decode_token
from src.db.database import get_database

security = HTTPBearer(auto_error=False)


class AuthContext:
    """Authenticated context containing user, tenant, and permissions."""

    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        user: Optional[dict] = None,
        api_key_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.user = user
        self.api_key_id = api_key_id

    @property
    def is_admin(self) -> bool:
        return self.role in ("owner", "admin")

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"


async def get_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Optional[AuthContext]:
    """Extract and validate auth context from JWT or API key.

    Returns None if no credentials are provided (for backward compatibility).
    """
    if not credentials:
        return None

    token = credentials.credentials

    # Try JWT first
    if not token.startswith("sk_"):
        try:
            payload = decode_token(token)
            return AuthContext(
                user_id=payload["sub"],
                tenant_id=payload["tenant_id"],
                role=payload["role"],
            )
        except (JWTError, KeyError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

    # Try API key
    key_hash = hash_api_key(token)
    api_key_doc = await db.api_keys.find_one({
        "key_hash": key_hash,
        "is_active": True,
    })

    if not api_key_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if api_key_doc.get("expires_at") and api_key_doc["expires_at"] < __import__("datetime").datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    return AuthContext(
        user_id=api_key_doc.get("user_id", ""),
        tenant_id=api_key_doc["tenant_id"],
        role="member",
        api_key_id=api_key_doc["_id"],
    )


async def require_auth(
    auth: Optional[AuthContext] = Depends(get_auth_context),
) -> AuthContext:
    """Require authentication. Raises 401 if not authenticated."""
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth


def require_role(*roles: str):
    """Dependency factory that requires specific roles."""
    async def _check_role(auth: AuthContext = Depends(require_auth)) -> AuthContext:
        if auth.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{auth.role}' not authorized. Required: {roles}",
            )
        return auth
    return _check_role
