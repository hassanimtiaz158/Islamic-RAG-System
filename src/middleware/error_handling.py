# src/middleware/error_handling.py
"""Consistent error response formatting."""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Format all error responses consistently."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except ValueError as e:
            return JSONResponse(
                status_code=400,
                content={"error": "bad_request", "detail": str(e)},
            )
        except PermissionError as e:
            return JSONResponse(
                status_code=403,
                content={"error": "forbidden", "detail": str(e)},
            )
        except FileNotFoundError as e:
            return JSONResponse(
                status_code=404,
                content={"error": "not_found", "detail": str(e)},
            )
        except Exception as e:
            # Log the full error but return generic message
            import logging
            logger = logging.getLogger("islamic-rag")
            logger.error(f"Unhandled error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": "internal_error", "detail": "An internal error occurred"},
            )
