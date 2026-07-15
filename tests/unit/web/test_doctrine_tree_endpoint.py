"""Unit tests for the read-only Doctrine Tree canvas endpoint (the 5th takeover).

``EngineBridge.get_doctrine_tree`` serves the static 11-node MVP Doctrine
Tree (``babylon.domain.doctrine``, Epoch 3 Wave 6 Phase 0 data foundation) —
the same payload for every session, since no ``DoctrineSystem``/acquisition
wiring exists yet (those depend on six pending owner rulings and are
explicitly out of scope for this canvas). Mirrors the structure of
``tests/unit/web/test_org_network.py`` (AW4-R1): bridge unit tests against
real data, stub-bridge parity tests, and one API-view smoke test.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def _bridge() -> Any:
    """An EngineBridge with a mock persistence layer.

    ``get_doctrine_tree`` never calls :meth:`hydrate_state` (the tree is
    static game-data, not session-derived), so the mock's
    ``hydrate_graph`` is never exercised — it exists only so constructing
    ``EngineBridge`` doesn't require a real persistence backend.
    """
    from game.engine_bridge import EngineBridge

    return EngineBridge(MagicMock())


# --------------------------------------------------------------------- #
# EngineBridge.get_doctrine_tree
# --------------------------------------------------------------------- #


class TestGetDoctrineTreeEngineBridge:
    def test_returns_all_eleven_nodes(self) -> None:
        result = _bridge().get_doctrine_tree(uuid.uuid4())

        assert len(result["nodes"]) == 11

    def test_root_id_is_class_consciousness(self) -> None:
        result = _bridge().get_doctrine_tree(uuid.uuid4())

        assert result["root_id"] == "class_consciousness"

    def test_all_three_trunks_present(self) -> None:
        result = _bridge().get_doctrine_tree(uuid.uuid4())

        trunks = {node["trunk"] for node in result["nodes"] if node["trunk"] is not None}
        assert trunks == {"reformist", "scientific", "insurrectionist"}

    def test_acquired_ids_is_honest_empty(self) -> None:
        """No acquisition system is wired yet — Constitution III.11: an
        honest empty beats a fabricated partial-progress list."""
        result = _bridge().get_doctrine_tree(uuid.uuid4())

        assert result["acquired_ids"] == []

    def test_tags_match_corpus_starting_values(self) -> None:
        result = _bridge().get_doctrine_tree(uuid.uuid4())

        assert result["tags"] == {
            "class_analysis": 1,
            "mass_link": 1,
            "militancy": 0,
        }

    def test_trap_nodes_are_flagged_with_conditions(self) -> None:
        result = _bridge().get_doctrine_tree(uuid.uuid4())
        by_id = {node["id"]: node for node in result["nodes"]}

        assert by_id["liquidationism"]["is_trap"] is True
        assert by_id["liquidationism"]["trap_condition"] == "CLASS_ANALYSIS <= 0 AND MILITANCY <= 0"
        assert by_id["adventurism"]["is_trap"] is True
        assert by_id["adventurism"]["trap_condition"] == "MASS_LINK <= 0"

    def test_goal_node_is_flagged(self) -> None:
        result = _bridge().get_doctrine_tree(uuid.uuid4())
        by_id = {node["id"]: node for node in result["nodes"]}

        assert by_id["united_front"]["is_goal"] is True
        non_goal_ids = {n["id"] for n in result["nodes"]} - {"united_front"}
        assert all(by_id[node_id]["is_goal"] is False for node_id in non_goal_ids)

    def test_node_shape_matches_frontend_contract(self) -> None:
        """Every node dict carries exactly the fields the frontend types."""
        result = _bridge().get_doctrine_tree(uuid.uuid4())
        expected_keys = {
            "id",
            "name",
            "tier",
            "parents",
            "description",
            "tag_deltas",
            "cost_tl",
            "trunk",
            "unlocks",
            "warning",
            "is_trap",
            "trap_condition",
            "narrative",
            "is_goal",
        }

        for node in result["nodes"]:
            assert set(node.keys()) == expected_keys

    def test_does_not_touch_persistence(self) -> None:
        """Static game-data — no hydrate_graph call, unlike every other
        dashboard method (Constitution III.11: not fabricating session
        derivation that doesn't exist)."""
        from game.engine_bridge import EngineBridge

        mock_persistence = MagicMock()
        bridge = EngineBridge(mock_persistence)

        bridge.get_doctrine_tree(uuid.uuid4())

        mock_persistence.hydrate_graph.assert_not_called()


# --------------------------------------------------------------------- #
# StubEngineBridge.get_doctrine_tree — must match the real bridge exactly
# --------------------------------------------------------------------- #


class TestGetDoctrineTreeStubBridge:
    def test_stub_matches_real_bridge_payload(self) -> None:
        from game.stub_bridge import StubEngineBridge

        stub_result = StubEngineBridge().get_doctrine_tree(uuid.uuid4())
        real_result = _bridge().get_doctrine_tree(uuid.uuid4())

        assert stub_result == real_result

    def test_stub_returns_eleven_nodes(self) -> None:
        from game.stub_bridge import StubEngineBridge

        result = StubEngineBridge().get_doctrine_tree(uuid.uuid4())

        assert len(result["nodes"]) == 11
        assert result["acquired_ids"] == []


# --------------------------------------------------------------------- #
# API view: GET /api/games/{id}/doctrine-tree/
# --------------------------------------------------------------------- #


@pytest.mark.django_db
class TestGetDoctrineTreeAPIView:
    def test_view_returns_envelope_with_full_tree(self) -> None:
        from django.contrib.auth.models import User
        from django.test import Client
        from django.urls import reverse

        import game.api
        from game.engine_bridge import EngineBridge
        from game.models import GameSession

        user = User.objects.create_user(  # type: ignore[no-untyped-call]
            username="doctrinetreeuser", password="doctrinetreepass123"
        )
        client = Client()
        client.login(username="doctrinetreeuser", password="doctrinetreepass123")
        session = GameSession.objects.create(
            id=uuid.UUID("cccccccc-dddd-eeee-ffff-000000000003"),
            player_id=user.id,
            scenario="wayne_county",
            current_tick=0,
            status="active",
        )
        game.api._bridge_instance = EngineBridge(MagicMock())

        url = reverse("game:game-doctrine-tree", kwargs={"game_id": str(session.id)})
        response = client.get(url)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert len(body["data"]["nodes"]) == 11
        assert body["data"]["root_id"] == "class_consciousness"
        assert body["data"]["acquired_ids"] == []

    def test_view_404s_for_unknown_game(self) -> None:
        from django.contrib.auth.models import User
        from django.test import Client
        from django.urls import reverse

        User.objects.create_user(  # type: ignore[no-untyped-call]
            username="doctrinetreemissing", password="doctrinetreepass123"
        )
        client = Client()
        client.login(username="doctrinetreemissing", password="doctrinetreepass123")

        url = reverse(
            "game:game-doctrine-tree",
            kwargs={"game_id": str(uuid.uuid4())},
        )
        response = client.get(url)

        assert response.status_code == 404
