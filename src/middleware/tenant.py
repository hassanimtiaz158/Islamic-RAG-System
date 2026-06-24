# src/middleware/tenant.py
"""Tenant resolution middleware.

Extracts tenant context from API key or JWT and attaches it to request state.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve tenant from Authorization header and attach to request state.

    For backward compatibility, this middleware does not enforce auth —
    it only populates request.state.tenant_id if credentials are present.
    Enforcement happens at the endpoint level via dependencies.
    """

    async def dispatch(self, request: Request, call_next):
        # Initialize tenant state as None (unauthenticated / default tenant)
        request.state.tenant_id = None
        request.state.user_id = None
        request.state.user_role = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Tenant resolution from JWT/API key happens in get_auth_context
            # This middleware just marks that auth was attempted
            request.state.has_auth_header = True
        else:
            request.state.has_auth_header = False

        response = await call_next(request)
        return response
