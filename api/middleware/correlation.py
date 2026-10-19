import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from core.logging import correlation_id_ctx


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts or generates an X-Correlation-Id header,

    binds it to the request context for structured logging, and includes it
    in the response headers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("X-Correlation-Id") or f"corr_{uuid.uuid4().hex[:12]}"
        token = correlation_id_ctx.set(correlation_id)

        try:
            response: Response = await call_next(request)
            response.headers["X-Correlation-Id"] = correlation_id
            return response
        finally:
            correlation_id_ctx.reset(token)
