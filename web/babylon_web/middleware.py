"""Middleware for the Babylon web application.

Two middlewares live here:

- :class:`RequestLoggingMiddleware` (existing): adds correlation IDs +
  per-request timing logs.
- :class:`EngineAvailabilityMiddleware` (spec 061 T127, FR-010): catches
  :exc:`psycopg.OperationalError` and :exc:`psycopg_pool.PoolTimeout`
  raised during request handling and returns HTTP 503 with the standard
  error body. Health endpoints are exempt (they have their own
  degraded-state reporting via ``database.reachable`` on
  ``/health/detail/``).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

from django.http import HttpResponse

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponseBase

logger = logging.getLogger("babylon_web.request")
engine_logger = logging.getLogger("babylon_web.engine_availability")

# Routes that MUST NOT be 503'd by the engine-availability middleware.
# These endpoints have their own degraded-state reporting via the
# ``database.reachable`` field on ``/health/detail/`` per spec 061 FR-009.
_HEALTH_PATH_PREFIXES = ("/health/",)

_ENGINE_UNAVAILABLE_BODY = json.dumps(
    {
        "detail": "Service temporarily unavailable. "
        "The simulation engine cannot reach its data layer."
    }
).encode("utf-8")

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


class EngineAvailabilityMiddleware:
    """Convert mid-session DB-loss into HTTP 503 (spec 061 T127, FR-010).

    The :class:`~game.apps.GameConfig` boot retry handles
    *startup-time* engine init failures by hard-exiting the worker.
    But once the worker is up, a transient Postgres outage during
    request handling produces a :class:`psycopg.OperationalError` (or
    :class:`psycopg_pool.PoolTimeout` on pool exhaustion) deep inside
    the bridge / persistence layer. Without this middleware, those
    surface as Django 500 (or worse, a half-broken JSON response).

    Per FR-010 (clarified): the right response shape is a uniform
    HTTP 503 with body::

        {"detail": "Service temporarily unavailable. The simulation
         engine cannot reach its data layer."}

    Health endpoints (``/health/``, ``/health/detail/``) are exempt —
    they must continue to respond so operators can observe the
    degraded state via the ``database.reachable`` field
    (spec 061 FR-009).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        return self.get_response(request)

    def process_exception(
        self,
        request: HttpRequest,
        exception: BaseException,
    ) -> HttpResponseBase | None:
        """Map DB-unreachable exceptions onto the standard 503 envelope.

        Returns ``None`` to delegate to the normal exception path for
        anything that isn't a DB-availability failure.
        """
        if any(request.path.startswith(p) for p in _HEALTH_PATH_PREFIXES):
            return None

        # Import lazily so the middleware module doesn't fail to load
        # when psycopg isn't installed (e.g., in SQLite-only test runs).
        try:
            from psycopg import OperationalError as PsycopgOperationalError
            from psycopg_pool import PoolTimeout as PsycopgPoolTimeout
        except ImportError:
            return None

        if not isinstance(exception, PsycopgOperationalError | PsycopgPoolTimeout):
            return None

        engine_logger.warning(
            "Engine unavailable mid-request: %s %s -> 503 (%s)",
            request.method,
            request.path,
            type(exception).__name__,
        )

        return HttpResponse(
            _ENGINE_UNAVAILABLE_BODY,
            status=503,
            content_type="application/json",
        )
