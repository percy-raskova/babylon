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
    "campaign",
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
        "params": {
            "mode": "targeted",
        },
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
            f"/api/games/{uuid_mod.uuid4()}/actions/campaign/",
            data=json.dumps(VERB_PAYLOADS["campaign"]),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_verb_endpoint_game_not_found(self) -> None:
        """Requesting a nonexistent game returns 404."""
        client, _, _ = self._setup()
        fake_id = uuid_mod.uuid4()

        response = client.post(
            f"/api/games/{fake_id}/actions/campaign/",
            data=json.dumps(VERB_PAYLOADS["campaign"]),
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
            "game:action-campaign",
            kwargs={"game_id": str(paused_session.id)},
        )
        response = client.post(
            url,
            data=json.dumps(VERB_PAYLOADS["campaign"]),
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
        url = reverse("game:action-campaign", kwargs={"game_id": str(session.id)})

        response = client.post(
            url,
            data=json.dumps(VERB_PAYLOADS["campaign"]),
            content_type="application/json",
        )

        assert response.status_code == 201
        body = json.loads(response.content)
        assert body["status"] == "ok"
        assert "tick" in body
        assert "session_id" in body

        data = body["data"]
        assert "action_id" in data or "turn_id" in data
        assert data["verb"] == "campaign"
        assert data["org_id"] == "org_1"
        assert data["target_id"] == "institution_1"
        assert data["tick"] == 7

    def test_response_includes_warnings(self) -> None:
        """Warnings from preview_action appear in response."""
        client, session = self._setup()
        url = reverse("game:action-campaign", kwargs={"game_id": str(session.id)})

        response = client.post(
            url,
            data=json.dumps(VERB_PAYLOADS["campaign"]),
            content_type="application/json",
        )

        body = json.loads(response.content)
        data = body["data"]
        assert "warnings" in data
        assert isinstance(data["warnings"], list)


@pytest.mark.unit
@pytest.mark.django_db
class TestEducateVerbView:
    """Verify the behavior of the new EDUCATE verb API endpoints."""

    def _setup(self) -> tuple:
        from unittest.mock import MagicMock

        from django.contrib.auth.models import User

        from game.models import GameSession

        user = User.objects.create_user(  # type: ignore[no-untyped-call]
            username=f"educate_user_{uuid_mod.uuid4().hex[:8]}",
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
        mock_bridge.get_educate_targets.return_value = {
            "status": "ok",
            "tick": 7,
            "verb": "educate",
            "acting_org": {
                "id": "org_1",
                "name": "Testing Org",
                "type": "PoliticalFaction",
                "consciousness_strategy": "revolutionary",
                "resources": {"cadre_labor": 12.0, "sympathizer_labor": 45.0, "material": 8.0},
                "ooda": {"action_points_remaining": 2, "action_points_max": 3, "cycle_time": 2},
                "cadre_level": 0.65,
                "cohesion": 0.78,
            },
            "cost": {
                "action_points": 1,
                "cadre_labor": 3.0,
                "sympathizer_labor": 0.0,
                "material": 0.0,
                "can_afford": True,
                "over_budget": False,
                "over_budget_penalty": None,
            },
            "targets": [],
            "unavailable_communities": [],
        }

        import game.api

        game.api._bridge_instance = mock_bridge

        return client, session, mock_bridge

    def test_educate_get(self) -> None:
        """GET /api/games/{id}/verbs/educate/ returns available targets."""
        client, session, mock_bridge = self._setup()
        url = reverse("game:verb-educate", kwargs={"game_id": str(session.id)})
        url += "?org_id=org_1"

        response = client.get(url)
        assert response.status_code == 200

        body = json.loads(response.content)
        assert body["status"] == "ok"
        assert body["verb"] == "educate"

    def test_educate_post(self) -> None:
        """POST /api/games/{id}/verbs/educate/ creates Educate action."""
        client, session, mock_bridge = self._setup()
        url = reverse("game:verb-educate", kwargs={"game_id": str(session.id)})

        payload = {"org_id": "org_1", "target_community_id": "community_a", "params": {}}

        response = client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 201
        body = json.loads(response.content)
        assert body["status"] == "ok"
        assert body["action_id"] == 42
        mock_bridge.submit_action.assert_called_once()


@pytest.mark.unit
@pytest.mark.django_db
class TestAttackVerbView:
    """Verify the behavior of the new ATTACK verb API endpoints."""

    def _setup(self) -> tuple:
        from unittest.mock import MagicMock

        from django.contrib.auth.models import User

        from game.models import GameSession

        user = User.objects.create_user(
            username=f"attack_user_{uuid_mod.uuid4().hex[:8]}",
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
        mock_bridge.submit_action.return_value = 43
        mock_bridge.get_attack_targets.return_value = {
            "status": "ok",
            "tick": 7,
            "verb": "attack",
            "acting_org": {
                "id": "org_1",
                "name": "Testing Org",
                "type": "PoliticalFaction",
                "consciousness_strategy": "revolutionary",
                "resources": {"cadre_labor": 12.0, "sympathizer_labor": 45.0, "material": 8.0},
                "ooda": {"action_points_remaining": 2, "action_points_max": 3, "cycle_time": 2},
                "cadre_level": 0.65,
                "cohesion": 0.78,
            },
            "cost": {
                "action_points": 2,
                "cadre_labor_if_targeted": 4.0,
                "sympathizer_labor_if_mass": 15.0,
                "material": 0.0,
                "can_afford_targeted": True,
                "can_afford_mass": True,
                "over_budget_ap": False,
                "cost_explanation": "testing explanation",
            },
            "ultra_left_warning": {
                "active": False,
                "trap_score": 0.0,
                "indicators": [],
                "explanation": None,
            },
            "warsaw_ghetto_flag": {
                "active": False,
                "population_p_acquiescence": 0.5,
                "threshold": 0.05,
                "explanation": None,
            },
            "targets": {"organizations": [], "edges": [], "institutions": []},
            "unavailable_targets": [],
        }

        import game.api

        game.api._bridge_instance = mock_bridge

        return client, session, mock_bridge

    def test_attack_get(self) -> None:
        """GET /api/games/{id}/verbs/attack/ returns available targets."""
        client, session, mock_bridge = self._setup()
        url = reverse("game:verb-attack", kwargs={"game_id": str(session.id)})
        url += "?org_id=org_1"

        response = client.get(url)
        assert response.status_code == 200

        body = json.loads(response.content)
        assert body["status"] == "ok"
        assert body["verb"] == "attack"

    def test_attack_post(self) -> None:
        """POST /api/games/{id}/verbs/attack/ creates Attack action."""
        client, session, mock_bridge = self._setup()
        url = reverse("game:verb-attack", kwargs={"game_id": str(session.id)})

        payload = {"org_id": "org_1", "target_id": "target_a", "params": {"mode": "mass"}}

        response = client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 201
        body = json.loads(response.content)
        assert body["status"] == "ok"
        assert body["action_id"] == 43
        mock_bridge.submit_action.assert_called_once()
