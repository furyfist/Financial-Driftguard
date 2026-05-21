import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header on all routes except GET /health.

    Disabled transparently when API_KEY env var is not set (local dev).
    """

    async def dispatch(self, request: Request, call_next):
        api_key = os.getenv("API_KEY", "")
        if not api_key:
            return await call_next(request)
        if request.url.path == "/health":
            return await call_next(request)
        if request.headers.get("X-API-Key", "") != api_key:
            return JSONResponse({"detail": "Invalid or missing API key"}, status_code=401)
        return await call_next(request)
