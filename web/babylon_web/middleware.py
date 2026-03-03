"""Request logging middleware for the Babylon web application.

Adds a correlation ID to each request, logs request/response metadata
with timing, and propagates context for downstream loggers.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponseBase

logger = logging.getLogger("babylon_web.request")

# Header used to receive or propagate a correlation ID.
CORRELATION_HEADER = "X-Request-ID"


class RequestLoggingMiddleware:
    """Log every HTTP request with timing and correlation ID.

    Adds ``request.correlation_id`` for downstream use and sets the
    ``X-Request-ID`` response header so the frontend can correlate.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        """Process a request, log it, and return the response."""
        # Generate or reuse correlation ID from the client
        correlation_id = request.META.get(
            f"HTTP_{CORRELATION_HEADER.upper().replace('-', '_')}",
            str(uuid.uuid4()),
        )
        request.correlation_id = correlation_id  # type: ignore[attr-defined]

        start = time.monotonic()

        response: HttpResponseBase = self.get_response(request)

        duration_ms = (time.monotonic() - start) * 1000

        # Determine user info
        user_str = "anonymous"
        if hasattr(request, "user") and request.user.is_authenticated:
            user_str = str(request.user.pk)

        log_data = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "user": user_str,
            "ip": _get_client_ip(request),
        }

        # Choose log level based on status code
        status_code = response.status_code
        if status_code >= 500:
            logger.error("%(method)s %(path)s %(status)s (%(duration_ms).1fms)", log_data)
        elif status_code >= 400:
            logger.warning("%(method)s %(path)s %(status)s (%(duration_ms).1fms)", log_data)
        else:
            logger.info("%(method)s %(path)s %(status)s (%(duration_ms).1fms)", log_data)

        # Propagate correlation ID to the response
        response[CORRELATION_HEADER] = correlation_id

        return response


def _get_client_ip(request: HttpRequest) -> str:
    """Extract the client IP from X-Forwarded-For or REMOTE_ADDR."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        # First IP in the chain is the original client
        return str(forwarded.split(",")[0].strip())
    return str(request.META.get("REMOTE_ADDR", "unknown"))
