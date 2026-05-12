"""Spec 061 T105 / FR-033: purged session UUIDs surface as 404 to authorized clients.

Migration ``0007_purge_fixture_sessions`` deletes every pre-061
``game_session`` row, cascading through every per-session table. Any
client that still holds a UUID from a purged session must not see a
500, a leaked database stack trace, or any other 5xx.

The game endpoints sit behind authentication; an unauthenticated call
short-circuits with 403 (or 401 depending on DRF config) *before* the
session lookup happens. That's an unrelated concern. The contract this
file pins is: once a client is authenticated, a purged UUID returns
404 with a JSON body — never a 5xx and never a Django HTML debug page.

Gated behind ``mise run test:int`` via ``pytest.mark.integration``
because the Django app + database are loaded.
"""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

pytestmark = pytest.mark.integration


_PURGED_UUID = "00000000-0000-0000-0000-000000000061"


@pytest.fixture
def authed_client(db):  # noqa: ARG001 — pytest-django fixture
    """A Django test client logged in as a staff user.

    Skips when the ``game_session`` table is absent — the table is
    created by the engine bridge's ``postgres_schema.py`` DDL, not
    Django migrations, so it only exists when the test DB is the
    real Postgres-backed runtime DB.
    """
    from django.db import connection

    table_names = connection.introspection.table_names()
    if "game_session" not in table_names:
        pytest.skip(
            "game_session table not present (engine bridge DDL not run); "
            "test requires the Postgres runtime DB, not the SQLite testing harness"
        )

    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="spec061-t105",
        defaults={"is_staff": True, "is_active": True},
    )
    user.is_staff = True
    user.is_active = True
    user.set_password("test-password-T105")
    user.save()
    client = Client()
    client.force_login(user)
    return client


class TestPurgedSession404:
    """FR-033: an authenticated request for a purged UUID returns 404 cleanly."""

    def test_state_endpoint_returns_404(self, authed_client: Client) -> None:
        """A UUID that does not exist in game_session must 404, never 500."""
        response = authed_client.get(f"/api/games/{_PURGED_UUID}/state/")
        assert response.status_code == 404, (
            f"expected 404 for purged session UUID, got {response.status_code}: "
            f"{response.content[:200]!r}"
        )

    def test_resolve_endpoint_returns_404(self, authed_client: Client) -> None:
        response = authed_client.post(f"/api/games/{_PURGED_UUID}/resolve/")
        assert response.status_code == 404, (
            f"expected 404 for purged session UUID, got {response.status_code}"
        )

    def test_timeseries_endpoint_returns_404(self, authed_client: Client) -> None:
        response = authed_client.get(f"/api/games/{_PURGED_UUID}/timeseries/")
        assert response.status_code == 404, (
            f"expected 404 for purged session UUID, got {response.status_code}"
        )

    def test_404_body_is_valid_json(self, authed_client: Client) -> None:
        """Body must be JSON (not a Django HTML debug page), even in DEBUG mode."""
        response = authed_client.get(f"/api/games/{_PURGED_UUID}/state/")
        assert response.status_code == 404
        content_type = response.get("Content-Type", "")
        assert "json" in content_type.lower() or response.content == b"", (
            f"404 body should be JSON or empty, got Content-Type={content_type!r}"
        )
        if response.content:
            try:
                json.loads(response.content)
            except json.JSONDecodeError as e:
                pytest.fail(f"404 body is not valid JSON: {e}: {response.content[:200]!r}")
