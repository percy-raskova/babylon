"""Tests for MockEngineBridge deterministic progression.

Verifies:
- Initial snapshot shape matches Spec 052 WorldState Snapshot Contract v0
- Tick resolution advances tick, decays heat, persists state
- Verb effects (educate/mobilize/attack/campaign/aid/reproduce) apply correctly
- Available actions are returned for player orgs
- All data shapes feed 042 UI components

.. note::
    Entity-level tests have been removed — classes are derived aggregations,
    not top-level agents (Spec 052 invariant 1).
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
# Constants — Spec 052 contract compliance
# --------------------------------------------------------------------------- #
EXPECTED_TERRITORY_COUNT = 10
EXPECTED_ORG_COUNT = 5
EXPECTED_INSTITUTION_COUNT = 2
EXPECTED_EDGE_COUNT = 6
EXPECTED_HYPEREDGE_COUNT = 5

REQUIRED_SNAPSHOT_KEYS = {
    "tick",
    "session_id",
    "organizations",
    "institutions",
    "territories",
    "hyperedges",
    "edges",
    "events",
    "traps",
    "derived",
}

REQUIRED_TERRITORY_KEYS = {
    "id",
    "name",
    "h3_index",
    "h3_resolution",
    "county_fips",
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

REQUIRED_ORG_KEYS = {
    "id",
    "name",
    "org_type",
    "class_character",
    "cohesion",
    "cadre_level",
    "budget",
    "heat",
    "territory_ids",
    "hyperedge_memberships",
    "consciousness",
    "ooda",
}

REQUIRED_CONSCIOUSNESS_KEYS = {"liberal", "fascist", "revolutionary"}

REQUIRED_EDGE_KEYS = {
    "id",
    "source_id",
    "target_id",
    "mode",
    "value_flow",
    "tension",
    "repression_flow",
}

REQUIRED_HYPEREDGE_KEYS = {
    "id",
    "category",
    "label",
    "contradiction_partner_id",
    "member_ids",
    "material_basis",
    "ideological_dimension",
}

REQUIRED_DERIVED_KEYS = {
    "value_tensor",
    "imperial_rent",
    "dept_iii_visibility",
    "class_aggregates",
    "economy",
    "predictions",
}


class TestInitialSnapshot(TestCase):
    """Verify the initial snapshot shape matches Spec 052."""

    def test_snapshot_has_all_required_keys(self) -> None:
        snap = _build_initial_snapshot("test-session")
        assert snap.keys() >= REQUIRED_SNAPSHOT_KEYS

    def test_snapshot_has_no_legacy_keys(self) -> None:
        """Spec 052 invariant: no top-level 'entities' or 'economy'."""
        snap = _build_initial_snapshot("test-session")
        assert "entities" not in snap
        assert "economy" not in snap

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

    def test_hyperedge_count(self) -> None:
        snap = _build_initial_snapshot("test-session")
        assert len(snap["hyperedges"]) == EXPECTED_HYPEREDGE_COUNT

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

    def test_orgs_have_required_keys(self) -> None:
        snap = _build_initial_snapshot("test-session")
        for org in snap["organizations"]:
            assert org.keys() >= REQUIRED_ORG_KEYS, (
                f"Org {org['id']} missing keys: {REQUIRED_ORG_KEYS - org.keys()}"
            )

    def test_org_consciousness_is_ternary_vector(self) -> None:
        """Spec 052 §6 — consciousness is never a scalar."""
        snap = _build_initial_snapshot("test-session")
        for org in snap["organizations"]:
            c = org["consciousness"]
            assert isinstance(c, dict)
            assert c.keys() >= REQUIRED_CONSCIOUSNESS_KEYS
            total = c["liberal"] + c["fascist"] + c["revolutionary"]
            assert abs(total - 1.0) < 1e-10, (
                f"Org {org['id']} consciousness doesn't sum to 1.0: {total}"
            )

    def test_org_ooda_profile(self) -> None:
        snap = _build_initial_snapshot("test-session")
        for org in snap["organizations"]:
            ooda = org["ooda"]
            assert isinstance(ooda, dict)
            for key in ("observe", "orient", "decide", "act", "cycle_ticks"):
                assert key in ooda

    def test_edges_have_required_keys(self) -> None:
        snap = _build_initial_snapshot("test-session")
        for edge in snap["edges"]:
            assert edge.keys() >= REQUIRED_EDGE_KEYS, (
                f"Edge {edge.get('id', '?')} missing keys: {REQUIRED_EDGE_KEYS - edge.keys()}"
            )

    def test_edges_use_mode_not_edge_type(self) -> None:
        """Spec 052 §10 — edges use 'mode' enum."""
        snap = _build_initial_snapshot("test-session")
        for edge in snap["edges"]:
            assert "mode" in edge
            assert "edge_type" not in edge

    def test_hyperedges_have_required_keys(self) -> None:
        snap = _build_initial_snapshot("test-session")
        for hx in snap["hyperedges"]:
            assert hx.keys() >= REQUIRED_HYPEREDGE_KEYS, (
                f"Hyperedge {hx['id']} missing keys: {REQUIRED_HYPEREDGE_KEYS - hx.keys()}"
            )

    def test_hyperedge_contradiction_pairs_are_symmetric(self) -> None:
        """Each contradiction_pair should reference its partner."""
        snap = _build_initial_snapshot("test-session")
        pairs = [hx for hx in snap["hyperedges"] if hx["category"] == "contradiction_pair"]
        for hx in pairs:
            partner_id = hx["contradiction_partner_id"]
            assert partner_id is not None, f"Contradiction pair {hx['id']} missing partner"
            partner = next((p for p in pairs if p["id"] == partner_id), None)
            assert partner is not None, f"Partner {partner_id} not found for {hx['id']}"

    def test_derived_block_has_required_keys(self) -> None:
        snap = _build_initial_snapshot("test-session")
        assert snap["derived"].keys() >= REQUIRED_DERIVED_KEYS

    def test_derived_class_aggregates_have_keys(self) -> None:
        snap = _build_initial_snapshot("test-session")
        aggs = snap["derived"]["class_aggregates"]
        assert "proletariat" in aggs
        assert "bourgeoisie" in aggs
        for cls_data in aggs.values():
            for key in ("population", "wage_share", "agitation_proxy"):
                assert key in cls_data

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
    """Test that verb effects mutate snapshot deterministically.

    Verb effects now target organizations and derived data, not entities.
    """

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

    def test_educate_raises_revolutionary_consciousness(self) -> None:
        """Educate shifts org consciousness toward revolutionary."""
        before = self.bridge.get_snapshot(self.session_id)
        org_before = next(o for o in before["organizations"] if o["id"] == "org-auto-union")
        initial_rev = org_before["consciousness"]["revolutionary"]

        after = self._submit_and_resolve("educate")
        org_after = next(o for o in after["organizations"] if o["id"] == "org-auto-union")
        new_rev = org_after["consciousness"]["revolutionary"]

        assert new_rev > initial_rev

    def test_mobilize_raises_heat(self) -> None:
        before = self.bridge.get_snapshot(self.session_id)
        target = "terr-wayne-03"
        initial_heat = next(t["heat"] for t in before["territories"] if t["id"] == target)

        after = self._submit_and_resolve("mobilize", target_id=target)
        new_heat = next(t["heat"] for t in after["territories"] if t["id"] == target)

        # Heat term = (initial * decay) + MOBILIZE_HEAT
        assert new_heat > initial_heat * MockDefines().HEAT_DECAY

    def test_attack_reduces_budget(self) -> None:
        """Attack reduces org budget (wealth damage)."""
        before = self.bridge.get_snapshot(self.session_id)
        org_before = next(o for o in before["organizations"] if o["id"] == "org-auto-union")
        initial_budget = org_before["budget"]

        after = self._submit_and_resolve("attack")
        org_after = next(o for o in after["organizations"] if o["id"] == "org-auto-union")
        new_budget = org_after["budget"]

        assert new_budget < initial_budget

    def test_aid_increases_proletariat_wage_share(self) -> None:
        """Aid increases proletariat wage_share in derived.class_aggregates."""
        before = self.bridge.get_snapshot(self.session_id)
        initial_ws = before["derived"]["class_aggregates"]["proletariat"]["wage_share"]

        after = self._submit_and_resolve("aid")
        new_ws = after["derived"]["class_aggregates"]["proletariat"]["wage_share"]

        assert new_ws > initial_ws

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

        # Tick, organizations, territories should be identical
        assert s1["tick"] == s2["tick"]
        assert len(s1["organizations"]) == len(s2["organizations"])
        for i in range(len(s1["organizations"])):
            assert (
                s1["organizations"][i]["consciousness"] == s2["organizations"][i]["consciousness"]
            )
            assert s1["organizations"][i]["budget"] == s2["organizations"][i]["budget"]
        for i in range(len(s1["territories"])):
            assert s1["territories"][i]["heat"] == s2["territories"][i]["heat"]
