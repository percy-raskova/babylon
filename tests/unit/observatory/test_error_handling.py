"""Error-handling tests (spec-096 review findings #2 + #17) — no sim DB.

Proves that DatabaseError subclasses other than OperationalError (a missing
view = ProgrammingError, a dropped conn = InterfaceError) are caught and turned
into a clean 503 JSON body with no SQL/DSN leak, and that an out-of-INT4-range
tick is rejected as a 400 before it reaches the database.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.db import ProgrammingError
from django.test import Client
from django.urls import reverse

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

_SID = "bc680a68-0000-4000-8000-000000000000"


def _authed_client(username: str) -> Client:
    User.objects.create_user(username=username, password="pw12345678")  # noqa: S106
    client = Client()
    client.login(username=username, password="pw12345678")  # noqa: S106
    return client


@contextmanager
def _fake_cursor() -> Any:
    yield object()


class TestDatabaseErrorHandling:
    def test_programming_error_returns_clean_503(self, settings: Any) -> None:
        settings.OBSERVATORY_ENABLED = True
        client = _authed_client("obs_err")
        with (
            patch("observatory.views._sim_cursor", _fake_cursor),
            patch(
                "observatory.views.fetch_sessions",
                side_effect=ProgrammingError('relation "v_hex_state_asof" does not exist'),
            ),
        ):
            resp = client.get(reverse("observatory:sessions"))
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "error"
        # No SQL identifiers / DSN internals leak into the client-facing body.
        assert "relation" not in body["message"].lower()
        assert "v_hex_state_asof" not in body["message"]


class TestIntRangeValidation:
    def test_out_of_range_tick_is_400(self, settings: Any) -> None:
        settings.OBSERVATORY_ENABLED = True
        client = _authed_client("obs_range")
        url = reverse("observatory:hex", kwargs={"session_id": _SID})
        resp = client.get(url, {"tick": "99999999999999"})  # > INT4 max
        assert resp.status_code == 400

    def test_out_of_range_from_tick_is_400(self, settings: Any) -> None:
        settings.OBSERVATORY_ENABLED = True
        client = _authed_client("obs_range2")
        url = reverse("observatory:series", kwargs={"session_id": _SID})
        resp = client.get(url, {"scope": "national", "from_tick": "-99999999999"})
        assert resp.status_code == 400


class TestHexSourceDispatch:
    """spec-099 fix #3: hex/ must dispatch on ``source``, never silently

    serve live/empty data for ``source=archive`` (archived sessions lack
    ``hex_spatial_map``, so an honest 501 is required instead)."""

    def test_archive_source_is_explicit_501_not_silent_empty(self, settings: Any) -> None:
        settings.OBSERVATORY_ENABLED = True
        client = _authed_client("obs_hex_src")
        url = reverse("observatory:hex", kwargs={"session_id": _SID})
        resp = client.get(url, {"tick": "0", "source": "archive"})
        assert resp.status_code == 501
        body = resp.json()
        assert body["status"] == "error"
        assert "archive" in body["message"].lower()

    def test_bad_source_is_400(self, settings: Any) -> None:
        settings.OBSERVATORY_ENABLED = True
        client = _authed_client("obs_hex_src2")
        url = reverse("observatory:hex", kwargs={"session_id": _SID})
        resp = client.get(url, {"tick": "0", "source": "cloud"})
        assert resp.status_code == 400


class TestTestConfigFlag:
    def test_testing_settings_disable_observatory(self, settings: Any) -> None:
        # Latent config bug: stub/testing/testing_pg drop the sim alias but
        # inherited OBSERVATORY_ENABLED=True from base → any endpoint raised
        # ConnectionDoesNotExist. The test configs must default the flag off.
        assert settings.OBSERVATORY_ENABLED is False
