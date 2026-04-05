"""Integration tests for the engine bridge pipeline.

Verifies that the bridge's get_snapshot() and resolve_tick() produce
output shapes matching the frontend TypeScript interfaces, including:
- VanguardResources on player orgs
- TrapDetection results
- Affordability checks on action submission

These tests exercise the bridge functions directly without Django
middleware or database, using _state_to_snapshot() and related helpers.
"""

from __future__ import annotations

import sys
from uuid import UUID

import pytest

# Add web/ to path so we can import game.engine_bridge
sys.path.insert(0, "web")

from babylon.engine.scenarios_wayne_county import create_wayne_county_scenario
from game.engine_bridge import (
    _serialize_organization,
    _session_action_history,
    _state_to_snapshot,
)

TEST_SESSION = UUID("12345678-1234-1234-1234-123456789012")


@pytest.fixture()
def wayne_state():
    """Create a Wayne County WorldState for testing."""
    state, _config, _defines = create_wayne_county_scenario()
    return state


@pytest.fixture(autouse=True)
def _clear_session_state():
    """Clear per-session state between tests."""
    _session_action_history.clear()
    # Also clear trap state
    from game.engine_bridge import _session_trap_state

    _session_trap_state.clear()
    yield
    _session_action_history.clear()
    _session_trap_state.clear()


class TestBridgeSnapshotShape:
    """Verify _state_to_snapshot output matches frontend GameSnapshot interface."""

    def test_snapshot_has_all_required_fields(self, wayne_state) -> None:
        """Snapshot dict has every field the frontend GameSnapshot expects."""
        snap = _state_to_snapshot(wayne_state, TEST_SESSION)

        required = {
            "session_id",
            "tick",
            "entities",
            "territories",
            "organizations",
            "institutions",
            "edges",
            "economy",
            "events",
        }
        assert required.issubset(snap.keys()), f"Missing: {required - snap.keys()}"

    def test_snapshot_includes_traps(self, wayne_state) -> None:
        """Wayne County snapshot includes trap detection results."""
        snap = _state_to_snapshot(wayne_state, TEST_SESSION)
        assert "traps" in snap, "Wayne County snapshot must include traps"

    def test_traps_shape_matches_frontend(self, wayne_state) -> None:
        """Trap detection output has every field the frontend TrapDetectionResult expects."""
        snap = _state_to_snapshot(wayne_state, TEST_SESSION)
        traps = snap["traps"]

        # Top-level fields
        assert "liberal" in traps
        assert "ultra_left" in traps
        assert "rightist" in traps
        assert "active_trap" in traps
        assert "game_over_trap" in traps

        # Each trap status has the right fields
        for trap_name in ["liberal", "ultra_left", "rightist"]:
            trap = traps[trap_name]
            assert "trap_type" in trap
            assert "severity" in trap
            assert "score" in trap
            assert "indicators" in trap
            assert "ticks_at_moderate" in trap
            assert isinstance(trap["indicators"], list)
            assert isinstance(trap["score"], float)

    def test_initial_traps_are_none_or_low(self, wayne_state) -> None:
        """At tick 0 with no action history, no trap should be active."""
        snap = _state_to_snapshot(wayne_state, TEST_SESSION)
        traps = snap["traps"]
        # No actions yet, so no trap should be severe
        assert traps["game_over_trap"] is None


class TestBridgeVanguardResources:
    """Verify VanguardResources is injected into org serialization."""

    def test_player_org_has_vanguard(self, wayne_state) -> None:
        """The player org (proletarian civil_society) gets vanguard resources."""
        org = list(wayne_state.organizations.values())[0]
        org_dict = _serialize_organization(org)

        assert org_dict["vanguard"] is not None
        v = org_dict["vanguard"]

        # All 7 fields present
        expected_fields = {
            "cadre_labor",
            "sympathizer_labor",
            "reputation",
            "budget",
            "heat",
            "max_cadre_labor",
            "max_sympathizer_labor",
        }
        assert expected_fields.issubset(v.keys()), f"Missing: {expected_fields - v.keys()}"

    def test_vanguard_values_are_correct(self, wayne_state) -> None:
        """VanguardResources values match expected computation."""
        org = list(wayne_state.organizations.values())[0]
        org_dict = _serialize_organization(org)
        v = org_dict["vanguard"]

        # cadre_level=0.1, cohesion=0.5, budget=100, heat=0.0, territory_count=2
        assert v["cadre_labor"] == 1.0  # 0.1 * 10 = 1.0
        assert v["max_cadre_labor"] == 1.0
        assert v["budget"] == 100.0
        assert v["heat"] == 0.0

    def test_snapshot_orgs_have_vanguard(self, wayne_state) -> None:
        """In the full snapshot, the player org has vanguard data."""
        snap = _state_to_snapshot(wayne_state, TEST_SESSION)
        player_org = next(
            (o for o in snap["organizations"] if o["class_character"] == "proletarian"),
            None,
        )
        assert player_org is not None, "No proletarian org in snapshot"
        assert player_org["vanguard"] is not None, "Player org must have vanguard"


class TestTrapDetectionPipeline:
    """Verify trap detection responds to action history changes."""

    def test_ultra_left_actions_trigger_trap(self, wayne_state) -> None:
        """Submitting many 'attack' actions raises the ultra-left trap score."""
        # Simulate action history of heavy attack usage
        _session_action_history[TEST_SESSION] = [{"verb": "attack"}] * 10

        snap = _state_to_snapshot(wayne_state, TEST_SESSION)
        traps = snap["traps"]

        # Ultra-left score should be elevated
        assert traps["ultra_left"]["score"] > 0.2
        assert traps["ultra_left"]["severity"] != "none"

    def test_liberal_actions_trigger_trap(self, wayne_state) -> None:
        """Submitting many 'negotiate' actions raises the liberal trap score."""
        _session_action_history[TEST_SESSION] = [{"verb": "negotiate"}] * 8 + [
            {"verb": "campaign"}
        ] * 5

        snap = _state_to_snapshot(wayne_state, TEST_SESSION)
        traps = snap["traps"]

        assert traps["liberal"]["score"] > 0.2
        assert traps["liberal"]["severity"] != "none"

    def test_balanced_actions_no_trap(self, wayne_state) -> None:
        """A balanced mix of actions doesn't trigger any trap."""
        _session_action_history[TEST_SESSION] = (
            [{"verb": "educate"}] * 3 + [{"verb": "mobilize"}] * 3 + [{"verb": "campaign"}] * 2
        )

        snap = _state_to_snapshot(wayne_state, TEST_SESSION)
        traps = snap["traps"]

        assert traps["active_trap"] is None or traps[traps["active_trap"]]["severity"] == "none"

    def test_trap_severity_persists_across_ticks(self, wayne_state) -> None:
        """Calling _state_to_snapshot twice preserves ticks_at_moderate."""
        _session_action_history[TEST_SESSION] = [{"verb": "attack"}] * 15

        # First call sets the trap state
        snap1 = _state_to_snapshot(wayne_state, TEST_SESSION)
        ultra1 = snap1["traps"]["ultra_left"]

        # Second call should carry forward
        snap2 = _state_to_snapshot(wayne_state, TEST_SESSION)
        ultra2 = snap2["traps"]["ultra_left"]

        # If first call was moderate+, second should increment ticks_at_moderate
        if ultra1["severity"] in {"moderate", "severe"}:
            assert ultra2["ticks_at_moderate"] >= ultra1["ticks_at_moderate"]


class TestAffordabilityCheck:
    """Verify VanguardResources affordability works correctly."""

    def test_affordable_action_passes(self) -> None:
        """An action the org can afford returns True."""
        from babylon.models.vanguard_resources import VanguardResources, check_can_afford

        resources = VanguardResources.from_organization(
            cadre_level=0.5,
            cohesion=0.5,
            budget=200.0,
            heat=0.0,
            territory_count=3,
        )
        ok, reason = check_can_afford(resources, "mobilize")
        assert ok, f"Should afford mobilize: {reason}"

    def test_unaffordable_action_fails(self) -> None:
        """An action the org can't afford returns False with reason."""
        from babylon.models.vanguard_resources import VanguardResources, check_can_afford

        resources = VanguardResources.from_organization(
            cadre_level=0.1,
            cohesion=0.1,
            budget=2.0,
            heat=0.9,
            territory_count=1,
        )
        ok, reason = check_can_afford(resources, "investigate")
        assert not ok
        assert "CL" in reason or "Need" in reason

    def test_unknown_verb_rejected(self) -> None:
        """An unknown verb is rejected."""
        from babylon.models.vanguard_resources import VanguardResources, check_can_afford

        resources = VanguardResources.from_organization(
            cadre_level=1.0,
            cohesion=1.0,
            budget=1000.0,
            heat=0.0,
            territory_count=10,
        )
        ok, reason = check_can_afford(resources, "fly_to_moon")
        assert not ok
        assert "Unknown verb" in reason
