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


# ---------------------------------------------------------------------- #
# Phase 3 / US1: Action validation and idempotency (T011, T012)
# ---------------------------------------------------------------------- #


@pytest.mark.unit
@pytest.mark.django_db
class TestActionValidation:
    """T011: Verify server-side action validation (FR-003)."""

    def _setup_bridge_and_session(self) -> tuple:
        """Create a mock bridge, inject it, and create a game session + user."""
        import uuid as uuid_mod

        from django.contrib.auth.models import User
        from django.test import Client

        from game.models import GameSession

        user = User.objects.create_user(username="valuser", password="valpass123")  # type: ignore[no-untyped-call]
        client = Client()
        client.login(username="valuser", password="valpass123")

        session = GameSession.objects.create(
            id=uuid_mod.uuid4(),
            player_id=user.id,
            scenario="two_node",
            current_tick=0,
            status="active",
        )

        # Mock the bridge with a snapshot that has organizations
        from unittest.mock import MagicMock

        mock_bridge = MagicMock()
        mock_bridge.submit_action.return_value = 1
        # Snapshot with a player-controlled political faction
        mock_bridge.get_snapshot.return_value = {
            "session_id": str(session.id),
            "tick": 0,
            "entities": [],
            "territories": [{"id": "hex_abc", "name": "Test Territory"}],
            "organizations": [
                {
                    "id": "political_faction_1",
                    "name": "Workers Party",
                    "org_type": "POLITICAL_FACTION",
                    "is_player": True,
                },
                {
                    "id": "business_1",
                    "name": "Corp Inc",
                    "org_type": "BUSINESS",
                },
            ],
            "institutions": [],
            "edges": [],
            "economy": {},
            "events": [],
        }
        return client, session, mock_bridge

    def test_invalid_verb_returns_400(self) -> None:
        """Submitting an invalid verb should return 400."""
        client, session, mock_bridge = self._setup_bridge_and_session()
        import game.api

        game.api._bridge_instance = mock_bridge

        response = client.post(
            f"/api/games/{session.id}/actions/",
            data=json.dumps(
                {"org_id": "political_faction_1", "verb": "invalid_verb", "target_id": "hex_abc"}
            ),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["status"] == "error"

    def test_valid_action_returns_201(self) -> None:
        """Submitting a valid action should succeed."""
        client, session, mock_bridge = self._setup_bridge_and_session()
        import game.api

        game.api._bridge_instance = mock_bridge

        response = client.post(
            f"/api/games/{session.id}/actions/",
            data=json.dumps(
                {"org_id": "political_faction_1", "verb": "educate", "target_id": "hex_abc"}
            ),
            content_type="application/json",
        )

        assert response.status_code == 201


@pytest.mark.unit
@pytest.mark.django_db
class TestIdempotencyGuard:
    """T012: Verify concurrent resolve requests are rejected."""

    def test_resolve_rejects_resolving_status(self) -> None:
        """Resolving a game already in 'resolving' status should return error."""
        import uuid as uuid_mod

        from django.contrib.auth.models import User
        from django.test import Client

        from game.models import GameSession

        user = User.objects.create_user(username="idempuser", password="idemppass")  # type: ignore[no-untyped-call]
        client = Client()
        client.login(username="idempuser", password="idemppass")

        session = GameSession.objects.create(
            id=uuid_mod.uuid4(),
            player_id=user.id,
            scenario="two_node",
            current_tick=0,
            status="resolving",
        )

        response = client.post(f"/api/games/{session.id}/resolve/")

        # Should reject because status is "resolving", not "active"
        assert response.status_code in (400, 409)
        data = json.loads(response.content)
        assert data["status"] == "error"
