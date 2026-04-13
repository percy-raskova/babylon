"""Tests for MockEngineBridge deterministic progression.

Verifies:
- Initial snapshot shape matches GameSnapshot TypeScript interface
- Tick resolution advances tick, decays heat, persists state
- Verb effects (educate/mobilize/attack/campaign/aid/reproduce) apply correctly
- Available actions are returned for player orgs
- All data shapes feed 042 UI components
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest  # type: ignore[import-not-found]
from django.test import TestCase

from game.mock_bridge import MockEngineBridge, _build_initial_snapshot
from game.mock_defines import MockDefines
from game.models import ActionResult, GameSession

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
EXPECTED_ENTITY_COUNT = 5
EXPECTED_TERRITORY_COUNT = 10
EXPECTED_ORG_COUNT = 4
EXPECTED_INSTITUTION_COUNT = 2
EXPECTED_EDGE_COUNT = 11

REQUIRED_SNAPSHOT_KEYS = {
    "tick",
    "session_id",
    "entities",
    "territories",
    "organizations",
    "institutions",
    "edges",
    "economy",
    "events",
    "traps",
}

REQUIRED_ENTITY_KEYS = {
    "id",
    "name",
    "role",
    "wealth",
    "consciousness",
    "national_identity",
    "agitation",
    "organization",
    "repression",
    "p_acquiescence",
    "p_revolution",
    "subsistence",
    "population",
    "inequality",
    "active",
}

REQUIRED_TERRITORY_KEYS = {
    "id",
    "name",
    "h3_index",
    "heat",
    "sector_type",
    "territory_type",
    "profile",
    "rent_level",
    "population",
    "under_eviction",
    "biocapacity",
    "host_id",
    "occupant_id",
}


class TestInitialSnapshot(TestCase):
    """Verify the initial snapshot shape matches the GameSnapshot interface."""

    def test_snapshot_has_all_required_keys(self) -> None:
        snap = _build_initial_snapshot("test-session")
        assert snap.keys() >= REQUIRED_SNAPSHOT_KEYS

    def test_entity_count(self) -> None:
        snap = _build_initial_snapshot("test-session")
        assert len(snap["entities"]) == EXPECTED_ENTITY_COUNT

    def test_territory_count(self) -> None:
        snap = _build_initial_snapshot("test-session")
        assert len(snap["territories"]) == EXPECTED_TERRITORY_COUNT

    def test_organization_count(self) -> None:
        snap = _build_initial_snapshot("test-session")
        assert len(snap["organizations"]) == EXPECTED_ORG_COUNT

    def test_institution_count(self) -> None:
        snap = _build_initial_snapshot("test-session")
        assert len(snap["institutions"]) == EXPECTED_INSTITUTION_COUNT

    def test_edge_count(self) -> None:
        snap = _build_initial_snapshot("test-session")
        assert len(snap["edges"]) == EXPECTED_EDGE_COUNT

    def test_entities_have_required_keys(self) -> None:
        snap = _build_initial_snapshot("test-session")
        for entity in snap["entities"]:
            assert entity.keys() >= REQUIRED_ENTITY_KEYS, (
                f"Entity {entity['id']} missing keys: {REQUIRED_ENTITY_KEYS - entity.keys()}"
            )

    def test_territories_have_required_keys(self) -> None:
        snap = _build_initial_snapshot("test-session")
        for territory in snap["territories"]:
            assert territory.keys() >= REQUIRED_TERRITORY_KEYS, (
                f"Territory {territory['id']} missing keys: "
                f"{REQUIRED_TERRITORY_KEYS - territory.keys()}"
            )

    def test_all_territories_have_h3_index(self) -> None:
        snap = _build_initial_snapshot("test-session")
        for t in snap["territories"]:
            assert t["h3_index"] is not None, f"Territory {t['id']} missing h3_index"

    def test_player_orgs_have_vanguard(self) -> None:
        snap = _build_initial_snapshot("test-session")
        player_orgs = [o for o in snap["organizations"] if o.get("vanguard") is not None]
        assert len(player_orgs) >= 2, "Expected at least 2 player orgs with vanguard"

    def test_traps_have_required_structure(self) -> None:
        snap = _build_initial_snapshot("test-session")
        traps = snap["traps"]
        for trap_type in ("liberal", "ultra_left", "rightist"):
            assert trap_type in traps
            assert "severity" in traps[trap_type]
            assert "score" in traps[trap_type]
        assert "active_trap" in traps
        assert "game_over_trap" in traps

    def test_initial_tick_is_zero(self) -> None:
        snap = _build_initial_snapshot("test-session")
        assert snap["tick"] == 0


@pytest.mark.django_db(transaction=True)
class TestMockBridgeLifecycle(TestCase):
    """Test create_game → get_snapshot → resolve_tick cycle."""

    def setUp(self) -> None:
        self.bridge = MockEngineBridge()
        # Create admin user
        from django.contrib.auth.models import User

        self.user = User.objects.create_user("testuser", password="test")

    def test_create_game_returns_session_id(self) -> None:
        result = self.bridge.create_game(player_id=self.user.id)
        assert "id" in result
        assert result["status"] == "active"
        assert result["current_tick"] == 0

    def test_create_game_persists_session(self) -> None:
        result = self.bridge.create_game(player_id=self.user.id)
        session = GameSession.objects.get(id=result["id"])
        assert session.current_tick == 0
        assert session.status == "active"

    def test_get_snapshot_returns_full_data(self) -> None:
        result = self.bridge.create_game(player_id=self.user.id)
        snap = self.bridge.get_snapshot(uuid.UUID(result["id"]))
        assert snap.keys() >= REQUIRED_SNAPSHOT_KEYS
        assert snap["tick"] == 0

    def test_resolve_tick_advances_tick(self) -> None:
        result = self.bridge.create_game(player_id=self.user.id)
        session_id = uuid.UUID(result["id"])
        snap = self.bridge.resolve_tick(session_id)
        assert snap["tick"] == 1

    def test_resolve_tick_persists_new_tick(self) -> None:
        result = self.bridge.create_game(player_id=self.user.id)
        session_id = uuid.UUID(result["id"])
        self.bridge.resolve_tick(session_id)
        session = GameSession.objects.get(id=result["id"])
        assert session.current_tick == 1

    def test_heat_decays_on_tick(self) -> None:
        result = self.bridge.create_game(player_id=self.user.id)
        session_id = uuid.UUID(result["id"])

        before = self.bridge.get_snapshot(session_id)
        initial_heat = before["territories"][0]["heat"]

        after = self.bridge.resolve_tick(session_id)
        new_heat = after["territories"][0]["heat"]

        expected = initial_heat * MockDefines().HEAT_DECAY
        assert abs(new_heat - expected) < 1e-10

    def test_tick_resolved_event_emitted(self) -> None:
        result = self.bridge.create_game(player_id=self.user.id)
        session_id = uuid.UUID(result["id"])
        snap = self.bridge.resolve_tick(session_id)
        event_types = [e["type"] for e in snap["events"]]
        assert "TICK_RESOLVED" in event_types


@pytest.mark.django_db(transaction=True)
class TestVerbEffects(TestCase):
    """Test that verb effects mutate snapshot deterministically."""

    def setUp(self) -> None:
        from django.contrib.auth.models import User

        self.bridge = MockEngineBridge()
        self.user = User.objects.create_user("testuser2", password="test")
        result = self.bridge.create_game(player_id=self.user.id)
        self.session_id = uuid.UUID(result["id"])

    def _submit_and_resolve(self, verb: str, target_id: str = "terr-wayne-01") -> dict[str, Any]:
        """Submit a single action and resolve the tick."""
        self.bridge.submit_action(
            session_id=self.session_id,
            org_id="org-peoples-front",
            verb=verb,
            target_id=target_id,
        )
        return self.bridge.resolve_tick(self.session_id)

    def test_educate_raises_consciousness(self) -> None:
        before = self.bridge.get_snapshot(self.session_id)
        initial_c = before["entities"][0]["consciousness"]

        after = self._submit_and_resolve("educate")
        new_c = after["entities"][0]["consciousness"]

        assert new_c > initial_c

    def test_mobilize_raises_heat(self) -> None:
        before = self.bridge.get_snapshot(self.session_id)
        target = "terr-wayne-03"
        initial_heat = next(t["heat"] for t in before["territories"] if t["id"] == target)

        after = self._submit_and_resolve("mobilize", target_id=target)
        new_heat = next(t["heat"] for t in after["territories"] if t["id"] == target)

        # Heat term = (initial * decay) + MOBILIZE_HEAT
        assert new_heat > initial_heat * MockDefines().HEAT_DECAY

    def test_attack_reduces_wealth(self) -> None:
        before = self.bridge.get_snapshot(self.session_id)
        initial_wealth = before["entities"][0]["wealth"]

        after = self._submit_and_resolve("attack")
        new_wealth = after["entities"][0]["wealth"]

        assert new_wealth < initial_wealth

    def test_aid_increases_proletariat_wealth(self) -> None:
        before = self.bridge.get_snapshot(self.session_id)
        proletariat = next(e for e in before["entities"] if e["role"] == "PROLETARIAT")
        initial_wealth = proletariat["wealth"]

        after = self._submit_and_resolve("aid")
        new_proletariat = next(e for e in after["entities"] if e["role"] == "PROLETARIAT")

        assert new_proletariat["wealth"] > initial_wealth

    def test_reproduce_increases_cohesion(self) -> None:
        before = self.bridge.get_snapshot(self.session_id)
        org = next(o for o in before["organizations"] if o["id"] == "org-peoples-front")
        initial_cohesion = org["cohesion"]

        after = self._submit_and_resolve("reproduce")
        new_org = next(o for o in after["organizations"] if o["id"] == "org-peoples-front")

        assert new_org["cohesion"] > initial_cohesion

    def test_action_result_created(self) -> None:
        self._submit_and_resolve("educate")
        assert ActionResult.objects.count() == 1
        ar = ActionResult.objects.first()
        assert ar is not None
        assert ar.action_type == "educate"
        assert ar.success is True

    def test_action_event_emitted(self) -> None:
        snap = self._submit_and_resolve("educate")
        event_types = [e["type"] for e in snap["events"]]
        assert "ACTION_EDUCATE" in event_types


@pytest.mark.django_db(transaction=True)
class TestAvailableActions(TestCase):
    """Test available actions endpoint."""

    def setUp(self) -> None:
        from django.contrib.auth.models import User

        self.bridge = MockEngineBridge()
        self.user = User.objects.create_user("testuser3", password="test")
        result = self.bridge.create_game(player_id=self.user.id)
        self.session_id = uuid.UUID(result["id"])

    def test_available_actions_returns_list(self) -> None:
        actions = self.bridge.get_available_actions(self.session_id)
        assert isinstance(actions, list)
        assert len(actions) > 0

    def test_actions_for_player_orgs_only(self) -> None:
        actions = self.bridge.get_available_actions(self.session_id)
        org_ids = {a["org_id"] for a in actions}
        # Only player orgs (with vanguard) should have actions
        assert "org-peoples-front" in org_ids
        assert "org-auto-union" in org_ids
        # Non-player orgs should not
        assert "org-state-apparatus" not in org_ids

    def test_actions_include_verbs(self) -> None:
        actions = self.bridge.get_available_actions(self.session_id)
        verbs = {a["verb"] for a in actions}
        expected_verbs = {"educate", "mobilize", "attack", "campaign", "aid", "reproduce"}
        assert expected_verbs <= verbs

    def test_filter_by_org_id(self) -> None:
        actions = self.bridge.get_available_actions(self.session_id, org_id="org-peoples-front")
        assert all(a["org_id"] == "org-peoples-front" for a in actions)


@pytest.mark.django_db(transaction=True)
class TestDeterminism(TestCase):
    """Verify identical inputs produce identical outputs."""

    def test_two_games_produce_identical_tick_1(self) -> None:
        from django.contrib.auth.models import User

        bridge = MockEngineBridge()
        user = User.objects.create_user("testuser4", password="test")

        r1 = bridge.create_game(player_id=user.id)
        r2 = bridge.create_game(player_id=user.id)

        s1 = bridge.resolve_tick(uuid.UUID(r1["id"]))
        s2 = bridge.resolve_tick(uuid.UUID(r2["id"]))

        # Tick, entities, territories should be identical
        assert s1["tick"] == s2["tick"]
        assert len(s1["entities"]) == len(s2["entities"])
        for i in range(len(s1["entities"])):
            assert s1["entities"][i]["consciousness"] == s2["entities"][i]["consciousness"]
            assert s1["entities"][i]["wealth"] == s2["entities"][i]["wealth"]
        for i in range(len(s1["territories"])):
            assert s1["territories"][i]["heat"] == s2["territories"][i]["heat"]
