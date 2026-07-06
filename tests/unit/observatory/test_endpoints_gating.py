"""Endpoint gating tests (spec-096, US4 + FR-019) — no simulation DB needed.

These exercise ONLY the paths that short-circuit before any ``sim`` DB access:
- the feature flag (404 when disabled, for everyone), and
- authentication (403 when unauthenticated, flag on).

Data-returning paths are integration tests (``tests/integration/observatory/``).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

_SID = "bc680a68-0000-4000-8000-000000000000"

# All Observatory endpoint URL names + kwargs.
_ENDPOINTS = [
    ("observatory:status", {}),
    ("observatory:sessions", {}),
    ("observatory:ticks", {"session_id": _SID}),
    ("observatory:series", {"session_id": _SID}),
    ("observatory:series-csv", {"session_id": _SID}),
    ("observatory:commits", {"session_id": _SID}),
    ("observatory:hex", {"session_id": _SID}),
]


def _url(name: str, kwargs: dict[str, str]) -> str:
    return reverse(name, kwargs=kwargs)


def _authed_client(username: str) -> Client:
    User.objects.create_user(username=username, password="pw12345678")  # noqa: S106
    client = Client()
    client.login(username=username, password="pw12345678")  # noqa: S106
    return client


class TestRouting:
    def test_all_endpoints_reverse(self) -> None:
        assert _url("observatory:sessions", {}) == "/api/observatory/sessions/"
        assert _url("observatory:status", {}) == "/api/observatory/status/"
        assert (
            _url("observatory:series-csv", {"session_id": _SID})
            == f"/api/observatory/sessions/{_SID}/series.csv/"
        )


class TestDisabledReturns404:
    """Flag off → 404 for every endpoint, authenticated or not (obscurity)."""

    @pytest.mark.parametrize(("name", "kwargs"), _ENDPOINTS)
    def test_disabled_unauthenticated_404(
        self, settings: Any, name: str, kwargs: dict[str, str]
    ) -> None:
        settings.OBSERVATORY_ENABLED = False
        resp = Client().get(_url(name, kwargs))
        assert resp.status_code == 404

    @pytest.mark.parametrize(("name", "kwargs"), _ENDPOINTS)
    def test_disabled_authenticated_404(
        self, settings: Any, name: str, kwargs: dict[str, str]
    ) -> None:
        settings.OBSERVATORY_ENABLED = False
        resp = _authed_client("obs_off").get(_url(name, kwargs))
        assert resp.status_code == 404


class TestEnabledRequiresAuth:
    """Flag on → unauthenticated calls are rejected (403/401), no data leaked."""

    @pytest.mark.parametrize(("name", "kwargs"), _ENDPOINTS)
    def test_enabled_unauthenticated_forbidden(
        self, settings: Any, name: str, kwargs: dict[str, str]
    ) -> None:
        settings.OBSERVATORY_ENABLED = True
        resp = Client().get(_url(name, kwargs))
        assert resp.status_code in (401, 403)


class TestStatusEndpoint:
    """The status probe reports the flag without touching the sim DB."""

    def test_status_enabled_authenticated_ok(self, settings: Any) -> None:
        settings.OBSERVATORY_ENABLED = True
        resp = _authed_client("obs_on").get(_url("observatory:status", {}))
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["data"]["enabled"] is True

    def test_status_disabled_is_404(self, settings: Any) -> None:
        settings.OBSERVATORY_ENABLED = False
        resp = _authed_client("obs_probe").get(_url("observatory:status", {}))
        assert resp.status_code == 404
