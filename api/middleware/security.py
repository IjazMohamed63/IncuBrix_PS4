from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from core.errors import ErrorCode


class DemoSecurityMiddleware(BaseHTTPMiddleware):
    """Enforces rate limiting headers and validates revocable demo API access tokens."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check for revoked tokens
        from api.routers.security import is_token_revoked

        auth_token = request.headers.get("X-IncuBrix-Token")
        if not auth_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                auth_token = auth_header[7:].strip()

        # If a token is supplied and currently revoked, block requests to API routes
        # (Exclude security endpoints so the user can restore it)
        if auth_token and is_token_revoked(auth_token) and not request.url.path.startswith("/api/v1/security"):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": ErrorCode.UNAUTHORIZED.value,
                        "message": "Demo API token has been revoked. Please restore or configure a new token in Settings.",
                        "retryable": False,
                        "details": {"revoked_token": auth_token},
                    }
                },
                headers={
                    "X-RateLimit-Limit": "120",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "60",
                },
            )

        response: Response = await call_next(request)

        # Append standard demo rate limit headers
        response.headers["X-RateLimit-Limit"] = "120"
        response.headers["X-RateLimit-Remaining"] = "118"
        response.headers["X-RateLimit-Reset"] = "60"

        return response
