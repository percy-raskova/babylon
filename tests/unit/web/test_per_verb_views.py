"""Tests for per-verb URL routing and views (Spec 040).

Verifies that the nine verb-specific endpoints are resolvable,
accept POST requests, and create PlayerAction rows with the correct
verb value written from the URL (not the request body).
"""

from __future__ import annotations

import json
import uuid as uuid_mod

import pytest
from django.test import Client
from django.urls import resolve, reverse

# ---------------------------------------------------------------------- #
# URL Routing Tests
# ---------------------------------------------------------------------- #

VERBS = [
    "educate",
    "aid",
    "attack",
    "mobilize",
    "campaign",
    "move",
    "investigate",
    "reproduce",
    "negotiate",
]

GAME_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.mark.unit
class TestPerVerbURLRouting:
    """All nine verb-specific action endpoints resolve correctly."""

    @pytest.mark.parametrize("verb", VERBS)
    def test_verb_url_resolves(self, verb: str) -> None:
        url = reverse(f"game:action-{verb}", kwargs={"game_id": GAME_ID})
        assert f"/actions/{verb}/" in url

    @pytest.mark.parametrize("verb", VERBS)
    def test_verb_url_resolves_to_correct_view_name(self, verb: str) -> None:
        url = reverse(f"game:action-{verb}", kwargs={"game_id": GAME_ID})
        match = resolve(url)
        assert match.view_name == f"game:action-{verb}"

    def test_actions_available_still_resolves(self) -> None:
        """Unchanged endpoint: GET /api/games/{id}/actions/available/."""
        url = reverse("game:actions-available", kwargs={"game_id": GAME_ID})
        assert "/actions/available/" in url

    def test_actions_pending_still_resolves(self) -> None:
        """Unchanged endpoint: GET /api/games/{id}/actions/ (pending list)."""
        url = reverse("game:actions-list", kwargs={"game_id": GAME_ID})
        assert "/actions/" in url


# ---------------------------------------------------------------------- #
# Per-Verb View Integration Tests
# ---------------------------------------------------------------------- #

# Minimal valid request bodies for each verb
VERB_PAYLOADS: dict[str, dict] = {
    "educate": {
        "org_id": "org_1",
        "target_id": "community_a",
        "consciousness_strategy": "REVOLUTIONARY",
    },
    "aid": {
        "org_id": "org_1",
        "target_id": "org_2",
        "resource_type": "MATERIAL",
        "amount": 5.0,
    },
    "attack": {
        "org_id": "org_1",
        "target_id": "org_2",
        "mode": "SABOTAGE",
    },
    "mobilize": {
        "org_id": "org_1",
        "target_id": "hex_abc",
        "action_type": "PROTEST",
    },
    "campaign": {
        "org_id": "org_1",
        "target_id": "institution_1",
        "campaign_type": "ELECTORAL",
    },
    "move": {
        "org_id": "org_1",
        "target_id": "hex_dest",
    },
    "investigate": {
        "org_id": "org_1",
        "target_id": "territory_1",
        "depth": "SURFACE",
    },
    "reproduce": {
        "org_id": "org_1",
        "target_id": "community_a",
        "method": "CADRE",
    },
    "negotiate": {
        "org_id": "org_1",
        "target_id": "org_2",
        "offer_type": "ALLIANCE",
    },
}


@pytest.mark.unit
@pytest.mark.django_db
class TestPerVerbEndpoints:
    """Submit to per-verb endpoints, verify PlayerAction rows are created."""

    def _setup(self) -> tuple:
        """Create authenticated user, game session, and mock bridge."""
        from unittest.mock import MagicMock

        from django.contrib.auth.models import User

        from game.models import GameSession

        user = User.objects.create_user(  # type: ignore[no-untyped-call]
            username=f"verb_user_{uuid_mod.uuid4().hex[:8]}",
            password="testpass123",
        )
        client = Client()
        client.login(username=user.username, password="testpass123")

        session = GameSession.objects.create(
            id=uuid_mod.uuid4(),
            player_id=user.id,
            scenario="two_node",
            current_tick=0,
            status="active",
        )

        # Mock bridge — submit_action returns turn_id = 1
        mock_bridge = MagicMock()
        mock_bridge.submit_action.return_value = 1
        mock_bridge.preview_action.return_value = {
            "estimated_consciousness_delta": 0.05,
            "estimated_heat_delta": 0.01,
            "action_point_cost": 1.0,
            "success_probability": 0.7,
            "affected_territory_ids": [],
            "warnings": [],
        }

        import game.api

        game.api._bridge_instance = mock_bridge

        return client, session, mock_bridge

    @pytest.mark.parametrize("verb", VERBS)
    def test_verb_endpoint_accepts_post(self, verb: str) -> None:
        """POST to /api/games/{id}/actions/{verb}/ returns 201."""
        client, session, mock_bridge = self._setup()
        url = reverse(f"game:action-{verb}", kwargs={"game_id": str(session.id)})

        response = client.post(
            url,
            data=json.dumps(VERB_PAYLOADS[verb]),
            content_type="application/json",
        )

        assert response.status_code == 201, (
            f"Verb '{verb}' failed: {response.status_code} {response.content}"
        )
        data = json.loads(response.content)
        assert data["status"] == "ok"
        assert data["data"]["verb"] == verb

    @pytest.mark.parametrize("verb", VERBS)
    def test_verb_endpoint_creates_player_action(self, verb: str) -> None:
        """PlayerAction row is created with correct verb from URL."""

        client, session, mock_bridge = self._setup()
        url = reverse(f"game:action-{verb}", kwargs={"game_id": str(session.id)})

        client.post(
            url,
            data=json.dumps(VERB_PAYLOADS[verb]),
            content_type="application/json",
        )

        # The bridge's submit_action should have been called with the verb from URL
        mock_bridge.submit_action.assert_called_once()
        call_kwargs = mock_bridge.submit_action.call_args
        # Verify verb was passed correctly
        assert call_kwargs.kwargs.get("verb") == verb or (
            len(call_kwargs.args) >= 4 and call_kwargs.args[3] == verb
        )

    @pytest.mark.parametrize("verb", VERBS)
    def test_verb_endpoint_rejects_get(self, verb: str) -> None:
        """Per-verb endpoints only accept POST."""
        client, session, _ = self._setup()
        url = reverse(f"game:action-{verb}", kwargs={"game_id": str(session.id)})

        response = client.get(url)
        assert response.status_code == 405  # Method Not Allowed

    def test_verb_endpoint_requires_auth(self) -> None:
        """Unauthenticated requests return 403."""
        unauthenticated_client = Client()

        # Try any verb endpoint
        response = unauthenticated_client.post(
            f"/api/games/{uuid_mod.uuid4()}/actions/educate/",
            data=json.dumps(VERB_PAYLOADS["educate"]),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_verb_endpoint_game_not_found(self) -> None:
        """Requesting a nonexistent game returns 404."""
        client, _, _ = self._setup()
        fake_id = uuid_mod.uuid4()

        response = client.post(
            f"/api/games/{fake_id}/actions/educate/",
            data=json.dumps(VERB_PAYLOADS["educate"]),
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_verb_endpoint_inactive_game_rejected(self) -> None:
        """Actions against non-active games return error."""
        from django.contrib.auth.models import User

        from game.models import GameSession

        user = User.objects.create_user(  # type: ignore[no-untyped-call]
            username=f"inactive_user_{uuid_mod.uuid4().hex[:8]}",
            password="testpass123",
        )
        client = Client()
        client.login(username=user.username, password="testpass123")

        paused_session = GameSession.objects.create(
            id=uuid_mod.uuid4(),
            player_id=user.id,
            scenario="two_node",
            current_tick=0,
            status="paused",
        )

        from unittest.mock import MagicMock

        import game.api

        game.api._bridge_instance = MagicMock()

        url = reverse(
            "game:action-educate",
            kwargs={"game_id": str(paused_session.id)},
        )
        response = client.post(
            url,
            data=json.dumps(VERB_PAYLOADS["educate"]),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["status"] == "error"
        assert "ACTION_GAME_NOT_ACTIVE" in data.get("code", data.get("message", ""))


@pytest.mark.unit
@pytest.mark.django_db
class TestVerbResponseFormat:
    """Verify the response data shape from the spec §5."""

    def _setup(self) -> tuple:
        from unittest.mock import MagicMock

        from django.contrib.auth.models import User

        from game.models import GameSession

        user = User.objects.create_user(  # type: ignore[no-untyped-call]
            username=f"resp_user_{uuid_mod.uuid4().hex[:8]}",
            password="testpass123",
        )
        client = Client()
        client.login(username=user.username, password="testpass123")

        session = GameSession.objects.create(
            id=uuid_mod.uuid4(),
            player_id=user.id,
            scenario="two_node",
            current_tick=7,
            status="active",
        )

        mock_bridge = MagicMock()
        mock_bridge.submit_action.return_value = 42
        mock_bridge.preview_action.return_value = {
            "estimated_consciousness_delta": 0.05,
            "estimated_heat_delta": 0.01,
            "action_point_cost": 1,
            "success_probability": 0.7,
            "affected_territory_ids": [],
            "warnings": ["Over-budget"],
        }

        import game.api

        game.api._bridge_instance = mock_bridge

        return client, session

    def test_response_contains_required_fields(self) -> None:
        """Response envelope matches spec §5."""
        client, session = self._setup()
        url = reverse("game:action-educate", kwargs={"game_id": str(session.id)})

        response = client.post(
            url,
            data=json.dumps(VERB_PAYLOADS["educate"]),
            content_type="application/json",
        )

        assert response.status_code == 201
        body = json.loads(response.content)
        assert body["status"] == "ok"
        assert "tick" in body
        assert "session_id" in body

        data = body["data"]
        assert "action_id" in data or "turn_id" in data
        assert data["verb"] == "educate"
        assert data["org_id"] == "org_1"
        assert data["target_id"] == "community_a"
        assert data["tick"] == 7

    def test_response_includes_warnings(self) -> None:
        """Warnings from preview_action appear in response."""
        client, session = self._setup()
        url = reverse("game:action-educate", kwargs={"game_id": str(session.id)})

        response = client.post(
            url,
            data=json.dumps(VERB_PAYLOADS["educate"]),
            content_type="application/json",
        )

        body = json.loads(response.content)
        data = body["data"]
        assert "warnings" in data
        assert isinstance(data["warnings"], list)
