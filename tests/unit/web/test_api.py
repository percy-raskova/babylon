"""Tests for the game API views (Phase 4).

Tests URL routing, authentication enforcement, and response envelope format.
Uses Django's test client with SQLite in-memory.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client, RequestFactory
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

    def test_game_recover_url(self) -> None:
        url = reverse(
            "game:game-recover",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/recover/"

    def test_game_state_url(self) -> None:
        url = reverse(
            "game:game-state",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/state/"

    def test_game_map_url(self) -> None:
        url = reverse(
            "game:game-map",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/map/"

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

    # Wave 2 W2.5b: survival duel chart history (owner ruling 3) — served off
    # the generic node-inspector URL shape (class has no dedicated inspector
    # route, unlike org/territory).
    def test_inspector_node_history_url(self) -> None:
        url = reverse(
            "game:inspector-node-history",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "node_id": "C004"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/node/C004/history/"

    # Spec 103: Trade surfaces URL routing
    def test_game_trade_flows_url(self) -> None:
        url = reverse(
            "game:game-trade-flows",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/trade-flows/"

    def test_game_county_exposure_url(self) -> None:
        url = reverse(
            "game:game-county-exposure",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/exposure/"

    def test_game_trade_panel_url(self) -> None:
        url = reverse(
            "game:game-trade-panel",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/trade-panel/"


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

    def test_inspector_node_history_unauthenticated_returns_403(self) -> None:
        factory = RequestFactory()
        request = factory.get("/api/games/some-uuid/node/C004/history/")
        from game.api import inspector_node_history

        response = inspector_node_history(request, game_id="some-uuid", node_id="C004")
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
# fix/seed-scenario-loud: scenario validation on POST /api/games/
# ---------------------------------------------------------------------- #


@pytest.mark.unit
@pytest.mark.django_db
class TestCreateGameScenarioValidation:
    """fix/seed-scenario-loud: unknown scenario -> 400, never a silent 'us' game."""

    def _login_client(self) -> Client:
        from django.contrib.auth.models import User

        User.objects.create_user(username="scenuser", password="scenpass123")  # type: ignore[no-untyped-call]
        client = Client()
        client.login(username="scenuser", password="scenpass123")
        return client

    def test_unknown_scenario_returns_400_and_never_reaches_bridge(self) -> None:
        from unittest.mock import MagicMock

        import game.api

        client = self._login_client()
        mock_bridge = MagicMock()
        game.api._bridge_instance = mock_bridge

        response = client.post(
            "/api/games/",
            data=json.dumps({"scenario": "atlantis"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["status"] == "error"
        assert "Unknown scenario" in data["message"]
        mock_bridge.create_game.assert_not_called()

    def test_catalog_scenario_key_returns_201(self) -> None:
        import uuid as uuid_mod
        from unittest.mock import MagicMock

        import game.api

        client = self._login_client()
        mock_bridge = MagicMock()
        mock_bridge.create_game.return_value = uuid_mod.uuid4()
        game.api._bridge_instance = mock_bridge

        response = client.post(
            "/api/games/",
            data=json.dumps({"scenario": "us_nationwide"}),
            content_type="application/json",
        )

        assert response.status_code == 201
        mock_bridge.create_game.assert_called_once()


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


def _make_recover_session(status: str = "resolving") -> tuple[Client, Any]:
    """Create a logged-in client plus a session in the given status."""
    import uuid as uuid_mod

    from django.contrib.auth.models import User

    from game.models import GameSession

    user = User.objects.create_user(username="recuser", password="recpass")  # type: ignore[no-untyped-call]
    client = Client()
    client.login(username="recuser", password="recpass")
    session = GameSession.objects.create(
        id=uuid_mod.uuid4(),
        player_id=user.id,
        scenario="two_node",
        current_tick=3,
        status=status,
    )
    return client, session


def _backdate_session(session: Any, seconds: int) -> None:
    """Push a session's updated_at into the past.

    ``QuerySet.update()`` bypasses ``auto_now`` — exactly why this works,
    and exactly why the resolve transitions must stamp it explicitly.
    """
    import datetime as dt

    from django.utils import timezone

    from game.models import GameSession

    GameSession.objects.filter(id=session.id).update(
        updated_at=timezone.now() - dt.timedelta(seconds=seconds)
    )


@pytest.mark.unit
@pytest.mark.django_db
class TestRecoverEndpoint:
    """C.13: a session wedged in 'resolving' by a dead worker is recoverable."""

    def test_recover_resets_stale_resolving_session(self) -> None:
        client, session = _make_recover_session("resolving")
        _backdate_session(session, 600)

        response = client.post(f"/api/games/{session.id}/recover/")

        assert response.status_code == 200
        session.refresh_from_db()
        assert session.status == "active"

    def test_recover_rejects_fresh_resolving_session(self) -> None:
        """A resolve younger than the threshold may still be in flight."""
        client, session = _make_recover_session("resolving")  # updated_at = now

        response = client.post(f"/api/games/{session.id}/recover/")

        assert response.status_code == 409
        session.refresh_from_db()
        assert session.status == "resolving"

    def test_recover_rejects_active_session(self) -> None:
        client, session = _make_recover_session("active")
        _backdate_session(session, 600)

        response = client.post(f"/api/games/{session.id}/recover/")

        assert response.status_code == 400

    def test_recover_logs_recovery_event(self) -> None:
        from game.models import GameEventLog

        client, session = _make_recover_session("resolving")
        _backdate_session(session, 600)

        response = client.post(f"/api/games/{session.id}/recover/")

        assert response.status_code == 200
        assert GameEventLog.objects.filter(
            session_id=session.id,
            category="game_recover",
        ).exists()

    def test_recovered_session_can_resolve_again(self) -> None:
        """End-to-end wedge escape: recover, then resolve succeeds."""
        from unittest.mock import MagicMock

        import game.api

        client, session = _make_recover_session("resolving")
        _backdate_session(session, 600)
        assert client.post(f"/api/games/{session.id}/recover/").status_code == 200

        mock_bridge = MagicMock()
        mock_bridge.resolve_tick.return_value = {"tick": 4, "events": []}
        game.api._bridge_instance = mock_bridge
        try:
            response = client.post(f"/api/games/{session.id}/resolve/")
        finally:
            game.api._bridge_instance = None

        assert response.status_code == 200
        session.refresh_from_db()
        assert session.status == "active"
        assert session.current_tick == 4


@pytest.mark.unit
@pytest.mark.django_db
class TestResolveStampsUpdatedAt:
    """The staleness clock: every resolve transition must touch updated_at."""

    def test_successful_resolve_advances_updated_at(self) -> None:
        from unittest.mock import MagicMock

        import game.api

        client, session = _make_recover_session("active")
        _backdate_session(session, 600)
        session.refresh_from_db()
        before = session.updated_at

        mock_bridge = MagicMock()
        mock_bridge.resolve_tick.return_value = {"tick": 4, "events": []}
        game.api._bridge_instance = mock_bridge
        try:
            response = client.post(f"/api/games/{session.id}/resolve/")
        finally:
            game.api._bridge_instance = None

        assert response.status_code == 200
        session.refresh_from_db()
        assert session.updated_at > before

    def test_failed_resolve_advances_updated_at(self) -> None:
        from unittest.mock import MagicMock

        import game.api

        client, session = _make_recover_session("active")
        _backdate_session(session, 600)
        session.refresh_from_db()
        before = session.updated_at

        mock_bridge = MagicMock()
        mock_bridge.resolve_tick.side_effect = RuntimeError("boom")
        game.api._bridge_instance = mock_bridge
        try:
            response = client.post(f"/api/games/{session.id}/resolve/")
        finally:
            game.api._bridge_instance = None

        assert response.status_code == 500
        session.refresh_from_db()
        assert session.status == "active"
        assert session.updated_at > before


@pytest.mark.unit
@pytest.mark.django_db
class TestScenarioList:
    """T033: Verify GET /api/scenarios/ returns scenario catalog."""

    def test_scenario_list_url(self) -> None:
        url = reverse("game:scenario-list")
        assert url == "/api/scenarios/"

    def test_scenario_list_returns_scenarios(self) -> None:
        from django.contrib.auth.models import User
        from django.test import Client

        User.objects.create_user(username="scenuser", password="scenpass123")  # type: ignore[no-untyped-call]
        client = Client()
        client.login(username="scenuser", password="scenpass123")

        response = client.get("/api/scenarios/")
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "ok"
        scenarios = data["data"]
        assert len(scenarios) >= 2

        # Each scenario has required metadata fields
        for scenario in scenarios:
            assert "key" in scenario
            assert "name" in scenario
            assert "description" in scenario
            assert "territory_count" in scenario

    def test_scenario_list_contains_us_nationwide(self) -> None:
        from django.contrib.auth.models import User
        from django.test import Client

        User.objects.create_user(username="scenuser2", password="scenpass123")  # type: ignore[no-untyped-call]
        client = Client()
        client.login(username="scenuser2", password="scenpass123")

        response = client.get("/api/scenarios/")
        data = json.loads(response.content)
        scenarios = data["data"]
        keys = [s["key"] for s in scenarios]
        assert "us_nationwide" in keys

    def test_scenario_list_unauthenticated_returns_403(self) -> None:
        factory = RequestFactory()
        request = factory.get("/api/scenarios/")
        from game.api import scenario_list

        response = scenario_list(request)
        assert response.status_code == 403
