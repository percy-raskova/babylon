"""Spec 061 T126 / FR-010: mid-session DB-loss returns HTTP 503.

When the engine bridge is initialized successfully but the Postgres
connection later becomes unreachable, engine-dependent endpoints must
return HTTP 503 with the standard error body. Health endpoints must
remain reachable so operators can observe the degraded state.

Tests drive ``EngineAvailabilityMiddleware.process_exception`` directly
to avoid Django URL-cache complications from dynamic urlpatterns
mutation. The middleware is wired into the global ``MIDDLEWARE`` list
in ``babylon_web.settings.base`` so all real engine-dependent views
benefit from it automatically.

Gated behind ``mise run test:int`` via ``pytest.mark.integration``.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client, RequestFactory

pytestmark = pytest.mark.integration


def _engine_unavailable_body() -> dict:
    return {
        "detail": "Service temporarily unavailable. "
        "The simulation engine cannot reach its data layer."
    }


class TestEngineAvailabilityMiddleware:
    """FR-010: psycopg.OperationalError / PoolTimeout → HTTP 503."""

    def test_operational_error_maps_to_503(self) -> None:
        from psycopg import OperationalError

        from babylon_web.middleware import EngineAvailabilityMiddleware

        rf = RequestFactory()
        middleware = EngineAvailabilityMiddleware(get_response=lambda _r: None)  # type: ignore[arg-type]
        request = rf.get("/api/games/abc/state/")
        response = middleware.process_exception(request, OperationalError("simulated DB outage"))

        assert response is not None
        assert response.status_code == 503
        assert json.loads(response.content) == _engine_unavailable_body()
        assert response["Content-Type"] == "application/json"

    def test_pool_timeout_maps_to_503(self) -> None:
        from psycopg_pool import PoolTimeout

        from babylon_web.middleware import EngineAvailabilityMiddleware

        rf = RequestFactory()
        middleware = EngineAvailabilityMiddleware(get_response=lambda _r: None)  # type: ignore[arg-type]
        request = rf.post("/api/games/abc/resolve/")
        response = middleware.process_exception(request, PoolTimeout("pool exhausted"))

        assert response is not None
        assert response.status_code == 503
        assert json.loads(response.content) == _engine_unavailable_body()

    def test_unrelated_exception_passes_through(self) -> None:
        """ValueError/TypeError/etc. must NOT be classified as engine-unavailable."""
        from babylon_web.middleware import EngineAvailabilityMiddleware

        rf = RequestFactory()
        middleware = EngineAvailabilityMiddleware(get_response=lambda _r: None)  # type: ignore[arg-type]
        request = rf.get("/api/games/abc/state/")
        result = middleware.process_exception(request, ValueError("business-logic bug"))

        # Returning None hands control back to Django's normal exception path
        # (which becomes a 500 once the test framework finishes).
        assert result is None

    def test_health_endpoint_exempt_from_503(self) -> None:
        """Health endpoints have their own degraded-state reporting via
        ``/health/detail/``'s ``database.reachable`` field. The middleware
        must NOT 503 them."""
        from psycopg import OperationalError

        from babylon_web.middleware import EngineAvailabilityMiddleware

        rf = RequestFactory()
        middleware = EngineAvailabilityMiddleware(get_response=lambda _r: None)  # type: ignore[arg-type]
        for path in ("/health/", "/health/detail/"):
            request = rf.get(path)
            result = middleware.process_exception(request, OperationalError("blip"))
            assert result is None, f"{path} must not be 503'd by spec 061 FR-010"

    def test_public_health_endpoint_still_reachable(self) -> None:
        """End-to-end: with the middleware installed, /health/ still returns 200."""
        client = Client()
        response = client.get("/health/")
        assert response.status_code == 200

    def test_middleware_is_registered(self) -> None:
        """Defense-in-depth: confirm the middleware is in the active MIDDLEWARE list,
        else the request-path classification work above is moot in production."""
        from django.conf import settings

        assert "babylon_web.middleware.EngineAvailabilityMiddleware" in settings.MIDDLEWARE
