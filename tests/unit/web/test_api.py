"""Tests for the game API views (Phase 4).

Tests URL routing, authentication enforcement, and response envelope format.
Uses Django's test client with SQLite in-memory.
"""

from __future__ import annotations

import json

import pytest
from django.test import RequestFactory
from django.urls import resolve, reverse


@pytest.mark.unit
class TestURLRouting:
    """Verify all API URL patterns resolve correctly."""

    def test_game_list_url(self) -> None:
        url = reverse("game:game-list")
        assert url == "/api/games/"

    def test_game_detail_url(self) -> None:
        url = reverse(
            "game:game-detail",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/"

    def test_game_pause_url(self) -> None:
        url = reverse(
            "game:game-pause",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/pause/"

    def test_game_resume_url(self) -> None:
        url = reverse(
            "game:game-resume",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/resume/"

    def test_game_state_url(self) -> None:
        url = reverse(
            "game:game-state",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/state/"

    def test_actions_available_url(self) -> None:
        url = reverse(
            "game:actions-available",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert "/actions/available/" in url

    def test_actions_list_url(self) -> None:
        url = reverse(
            "game:actions-list",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert "/actions/" in url

    def test_resolve_tick_url(self) -> None:
        url = reverse(
            "game:resolve-tick",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert "/resolve/" in url

    def test_tick_results_url(self) -> None:
        url = reverse(
            "game:tick-results",
            kwargs={
                "game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "tick": 5,
            },
        )
        assert "/results/5/" in url

    def test_game_list_resolves_to_correct_view(self) -> None:
        match = resolve("/api/games/")
        assert match.view_name == "game:game-list"


@pytest.mark.unit
@pytest.mark.django_db
class TestAuthEnforcement:
    """Verify API endpoints require authentication."""

    def test_game_list_unauthenticated_returns_403(self) -> None:
        factory = RequestFactory()
        request = factory.get("/api/games/")
        # DRF requires request to not have session auth
        from game.api import game_list

        response = game_list(request)
        # DRF returns 403 for unauthenticated requests with session auth
        assert response.status_code == 403

    def test_game_detail_unauthenticated_returns_403(self) -> None:
        factory = RequestFactory()
        request = factory.get("/api/games/some-uuid/")
        from game.api import game_detail

        response = game_detail(request, game_id="some-uuid")
        assert response.status_code == 403


@pytest.mark.unit
class TestResponseEnvelope:
    """Verify the response envelope format."""

    def test_envelope_has_status_ok(self) -> None:
        from game.api import _envelope

        response = _envelope({"test": True})
        data = json.loads(response.content)
        assert data["status"] == "ok"
        assert data["data"] == {"test": True}

    def test_envelope_with_tick_and_session(self) -> None:
        from game.api import _envelope

        response = _envelope(
            {"test": True},
            tick=5,
            session_id="abc-123",
        )
        data = json.loads(response.content)
        assert data["tick"] == 5
        assert data["session_id"] == "abc-123"

    def test_error_envelope(self) -> None:
        from game.api import _error

        response = _error("Something went wrong", http_status=400)
        data = json.loads(response.content)
        assert data["status"] == "error"
        assert data["message"] == "Something went wrong"
        assert response.status_code == 400

    def test_error_envelope_404(self) -> None:
        from game.api import _error

        response = _error("Not found", http_status=404)
        assert response.status_code == 404
