"""Unit tests for the engine bridge (Phase 3).

Tests use mocks for RuntimePersistence and the step() function
to verify call ordering and output format without requiring
a real database or simulation engine.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph
from babylon.models.enums import EventType
from babylon.models.events import SimulationEvent
from game.engine_bridge import (
    EngineBridge,
    _build_initial_state_for_scenario,
    _heat_delta_by_territory,
    _hex_feature_properties,
    _hex_state_row,
    _org_count_by_territory,
    _serialize_territory,
    _state_to_snapshot,
    resolve_scenario,
)


def _make_mock_persistence() -> MagicMock:
    """Create a mock RuntimePersistence with standard method signatures."""
    mock = MagicMock()
    mock.create_session.return_value = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    mock.hydrate_graph.return_value = _build_initial_state_for_scenario("default").to_graph()
    mock.persist_tick.return_value = None
    mock.get_metadata.return_value = None
    mock.get_session.return_value = {"scenario": "default"}
    mock.mark_turns_resolved.return_value = 0
    mock.submit_turn.return_value = 42
    mock.get_pending_turns.return_value = []
    return mock


def _make_minimal_graph() -> nx.DiGraph[str]:
    """Create a minimal graph for hydration tests."""
    G = BabylonGraph()
    G.graph["tick"] = 0
    G.graph["economy"] = {"imperial_rent": 0.0}
    G.graph["state_finances"] = {}
    G.graph["events"] = []
    G.graph["event_log"] = []
    return G


@pytest.mark.unit
class TestEngineBridgeCreateGame:
    """Verify create_game delegates to persistence.create_session."""

    def test_create_game_returns_uuid(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        result = bridge.create_game(scenario="detroit", rng_seed=42)

        assert isinstance(result, uuid.UUID)
        assert result == uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    def test_create_game_passes_scenario(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        bridge.create_game(scenario="two_node")

        call_kwargs = mock_persistence.create_session.call_args
        assert call_kwargs.kwargs["scenario"] == "two_node"

    def test_create_game_passes_player_id(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        bridge.create_game(scenario="two_node", player_id=7)

        call_kwargs = mock_persistence.create_session.call_args
        assert call_kwargs.kwargs["player_id"] == 7

    def test_create_game_validates_config(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        # Valid config should pass
        bridge.create_game(scenario="two_node", config={"extraction_efficiency": 0.5})
        assert mock_persistence.create_session.called

    def test_create_game_serializes_defines(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        bridge.create_game(scenario="two_node", defines={})

        call_kwargs = mock_persistence.create_session.call_args
        # game_defines_json should be a dict (serialized GameDefines)
        assert isinstance(call_kwargs.kwargs["game_defines_json"], dict)

    def test_create_game_persists_initial_tick_state(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        bridge.create_game(scenario="default", rng_seed=42)

        assert mock_persistence.persist_tick.called
        persist_kwargs = mock_persistence.persist_tick.call_args.kwargs
        assert persist_kwargs["tick"] == 0
        assert persist_kwargs["session_id"] == uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        persisted_graph = persist_kwargs["graph"]
        assert isinstance(persisted_graph, BabylonGraph)
        assert len(persisted_graph.nodes) > 0

    def test_create_game_unknown_scenario_raises_before_session_created(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        with pytest.raises(ValueError, match="Unknown scenario"):
            bridge.create_game(scenario="atlantis", rng_seed=42)

        mock_persistence.create_session.assert_not_called()
        mock_persistence.persist_tick.assert_not_called()


@pytest.mark.unit
class TestScenarioBootstrap:
    """Verify scenario bootstrap selection for initial game state."""

    def test_unknown_scenario_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown scenario 'not-a-real-scenario'"):
            _build_initial_state_for_scenario("not-a-real-scenario")

    def test_aliases_resolve_to_canonical_names(self) -> None:
        assert resolve_scenario("default") == "us"
        assert resolve_scenario("us_nationwide") == "us"
        assert resolve_scenario("wayne") == "wayne_county"
        assert resolve_scenario("detroit") == "wayne_county"

    def test_known_scenario_builds_tick_zero_state(self) -> None:
        state = _build_initial_state_for_scenario("two_node")

        assert state.tick == 0
        assert len(state.entities) > 0

    def test_every_catalog_key_is_seedable(self) -> None:
        """Guard against SCENARIO_CATALOG/bridge drift (the us_nationwide bug)."""
        from game.api import SCENARIO_CATALOG

        for entry in SCENARIO_CATALOG:
            assert resolve_scenario(entry["key"])


@pytest.mark.unit
class TestEngineBridgeHydrate:
    """Verify hydrate_state loads graph and reconstructs WorldState."""

    def test_hydrate_calls_persistence(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        bridge.hydrate_state(sid)

        mock_persistence.hydrate_graph.assert_called_once_with(tick=None, session_id=sid)

    def test_hydrate_with_specific_tick(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        bridge.hydrate_state(sid, tick=5)

        mock_persistence.hydrate_graph.assert_called_once_with(tick=5, session_id=sid)

    def test_hydrate_returns_world_state_and_graph(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        state, graph = bridge.hydrate_state(sid)

        assert state.tick == 0
        assert isinstance(graph, BabylonGraph)

    def test_hydrate_bootstraps_when_graph_unseeded(self) -> None:
        mock_persistence = _make_mock_persistence()
        empty_graph = BabylonGraph()
        seeded_graph = _build_initial_state_for_scenario("default").to_graph()
        mock_persistence.hydrate_graph.side_effect = [empty_graph, seeded_graph]

        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        _state, _graph = bridge.hydrate_state(sid)

        assert mock_persistence.persist_tick.called
        assert mock_persistence.hydrate_graph.call_count == 2


@pytest.mark.unit
class TestEngineBridgeResolveTick:
    """Verify resolve_tick calls hydrate → step → persist in order."""

    @patch("game.engine_bridge.step")
    def test_resolve_tick_calls_step(self, mock_step: MagicMock) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        # Make step return a minimal WorldState at tick 1
        mock_new_state = MagicMock()
        mock_new_state.tick = 1
        mock_new_state.entities = {}
        mock_new_state.territories = {}
        mock_new_state.organizations = {}
        mock_new_state.institutions = {}
        mock_new_state.economy = MagicMock()
        mock_new_state.economy.model_dump.return_value = {}
        mock_new_state.relationships = []
        mock_new_state.events = []
        mock_new_state.to_graph.return_value = _make_minimal_graph()
        mock_step.return_value = mock_new_state

        bridge.resolve_tick(sid)

        # Verify step was called
        assert mock_step.called
        # Verify persist_tick was called with new tick
        assert mock_persistence.persist_tick.called
        persist_kwargs = mock_persistence.persist_tick.call_args
        assert persist_kwargs.kwargs["tick"] == 1
        assert persist_kwargs.kwargs["session_id"] == sid

    @patch("game.engine_bridge.step")
    def test_resolve_tick_returns_snapshot(self, mock_step: MagicMock) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        mock_new_state = MagicMock()
        mock_new_state.tick = 1
        mock_new_state.entities = {}
        mock_new_state.territories = {}
        mock_new_state.organizations = {}
        mock_new_state.institutions = {}
        mock_new_state.economy = MagicMock()
        mock_new_state.economy.model_dump.return_value = {}
        mock_new_state.relationships = []
        mock_new_state.events = []
        mock_new_state.to_graph.return_value = _make_minimal_graph()
        mock_step.return_value = mock_new_state

        result = bridge.resolve_tick(sid)

        assert isinstance(result, dict)
        assert result["tick"] == 1
        assert result["session_id"] == str(sid)
        # Spec 052 §5: snapshot has organizations/institutions/territories,
        # not a top-level "entities" key.
        assert "organizations" in result
        assert "institutions" in result
        assert "territories" in result

    @patch("game.engine_bridge.step")
    def test_resolve_tick_events_are_json_safe(self, mock_step: MagicMock) -> None:
        """P0 #6 defense-in-depth: event dicts passed to persist_tick must be
        JSON-serializable WITHOUT a fallback encoder (no raw datetimes) —
        ``model_dump(mode="json")`` renders ``timestamp`` as an ISO string."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        mock_new_state = MagicMock()
        mock_new_state.tick = 1
        mock_new_state.entities = {}
        mock_new_state.territories = {}
        mock_new_state.organizations = {}
        mock_new_state.institutions = {}
        mock_new_state.economy = MagicMock()
        mock_new_state.economy.model_dump.return_value = {}
        mock_new_state.relationships = []
        mock_new_state.events = [
            SimulationEvent(
                event_type=EventType.UPRISING,
                tick=1,
                timestamp=datetime(2026, 7, 8, 1, 0),
            ),
        ]
        mock_new_state.to_graph.return_value = _make_minimal_graph()
        mock_step.return_value = mock_new_state

        bridge.resolve_tick(sid)

        events_arg = mock_persistence.persist_tick.call_args.kwargs["events"]
        assert events_arg is not None
        json.dumps(events_arg)  # raises TypeError if a datetime leaks through
        assert events_arg[0]["timestamp"] == "2026-07-08T01:00:00"


@pytest.mark.unit
class TestEngineBridgeSnapshot:
    """Verify get_snapshot returns properly structured dict."""

    def test_snapshot_keys(self) -> None:
        """Snapshot has the keys defined by Spec 052 §5.

        Spec 052 (and ``GameSnapshotSerializer`` docstring at
        ``web/game/serializers.py:267``) explicitly forbids a top-level
        ``entities`` key and a top-level ``economy`` key. Class data
        lives under ``derived.class_aggregates``; economy data lives
        under ``derived.economy``. Hyperedges and the derived block were
        added in commit 6eeb7bd6.
        """
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        snapshot = bridge.get_snapshot(sid)

        # ``traps`` is optional (only present for snapshots whose session
        # ran trap detection) — assert subset, not equality.
        required_keys = {
            "session_id",
            "tick",
            "territories",
            "organizations",
            "institutions",
            "hyperedges",
            "edges",
            "events",
            "derived",
        }
        assert required_keys.issubset(snapshot.keys()), (
            f"Missing Spec 052 keys: {required_keys - snapshot.keys()}"
        )

        # Spec 052 negative assertions.
        assert "entities" not in snapshot
        assert "economy" not in snapshot

    def test_snapshot_session_id_is_string(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        snapshot = bridge.get_snapshot(sid)
        assert snapshot["session_id"] == str(sid)

    def test_snapshot_entity_collections_are_lists(self) -> None:
        """Spec 052 §5: organizations/institutions/territories/edges are lists.

        Replaces the pre-Spec-052 assertion that ``snapshot["entities"]``
        is a list; Spec 052 split the single ``entities`` collection into
        these per-type lists.
        """
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        snapshot = bridge.get_snapshot(sid)
        for key in ("organizations", "institutions", "territories", "edges", "hyperedges"):
            assert isinstance(snapshot[key], list), f"snapshot[{key!r}] is not a list"


@pytest.mark.unit
class TestEngineBridgeActions:
    """Verify action submission and retrieval."""

    def test_submit_action_delegates_to_persistence(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        result = bridge.submit_action(
            session_id=sid,
            tick=0,
            org_id="org_workers",
            verb="RECRUIT",
            target_id="territory_detroit",
        )

        assert result == 42
        mock_persistence.submit_turn.assert_called_once()

    def test_get_pending_actions(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = [
            {"org_id": "org_workers", "verb": "RECRUIT", "resolved": False}
        ]
        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        result = bridge.get_pending_actions(sid, tick=0)

        assert len(result) == 1
        assert result[0]["org_id"] == "org_workers"


@pytest.mark.unit
class TestStateToSnapshot:
    """Test the _state_to_snapshot helper function."""

    def test_empty_state_produces_valid_snapshot(self) -> None:
        """An empty WorldState produces a Spec-052-shaped snapshot with empty collections.

        Per Spec 052 §5 there is no top-level ``entities`` key; collections
        are split by type. The ``derived`` block (Spec 052 §11) is always
        present with its six sub-fields, and each is empty for an empty
        WorldState.
        """
        mock_state = MagicMock()
        mock_state.tick = 0
        mock_state.entities = {}
        mock_state.territories = {}
        mock_state.organizations = {}
        mock_state.institutions = {}
        mock_state.relationships = []
        mock_state.economy = MagicMock()
        mock_state.economy.model_dump.return_value = {}
        mock_state.events = []

        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        result = _state_to_snapshot(mock_state, sid)

        assert result["tick"] == 0
        assert result["territories"] == []
        assert result["organizations"] == []
        assert result["institutions"] == []
        assert result["hyperedges"] == []
        assert result["edges"] == []
        assert result["events"] == []
        assert "entities" not in result, "Spec 052 §5 forbids a top-level 'entities' key"

        # Spec 052 §11 derived block.
        assert "derived" in result
        assert result["derived"]["economy"] == {}
        assert result["derived"]["class_aggregates"] == {}


# ---------------------------------------------------------------------- #
# Phase 3 / US1: Action injection, result persistence, endgame (T009-T013)
# ---------------------------------------------------------------------- #


def _make_mock_new_state(tick: int = 1) -> MagicMock:
    """Create a mock WorldState returned by step()."""
    mock_new_state = MagicMock()
    mock_new_state.tick = tick
    mock_new_state.entities = {}
    mock_new_state.territories = {}
    mock_new_state.organizations = {}
    mock_new_state.institutions = {}
    mock_new_state.economy = MagicMock()
    mock_new_state.economy.model_dump.return_value = {}
    mock_new_state.relationships = []
    mock_new_state.events = []
    mock_new_state.to_graph.return_value = _make_minimal_graph()
    return mock_new_state


@pytest.mark.unit
class TestActionInjection:
    """T009: Verify resolve_tick reads pending actions and passes them to step()."""

    @patch("game.engine_bridge.step")
    def test_resolve_tick_reads_pending_actions(self, mock_step: MagicMock) -> None:
        """resolve_tick() should call get_pending_actions for the current tick."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = [
            {"org_id": "political_faction_1", "verb": "educate", "target_id": "hex_abc"},
        ]
        mock_step.return_value = _make_mock_new_state()

        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        bridge.resolve_tick(sid)

        mock_persistence.get_pending_turns.assert_called_once()

    @patch("game.engine_bridge.step")
    def test_resolve_tick_passes_player_actions_to_step(self, mock_step: MagicMock) -> None:
        """Player actions should be formatted and passed as persistent_context."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = [
            {"org_id": "political_faction_1", "verb": "educate", "target_id": "hex_abc"},
        ]
        mock_step.return_value = _make_mock_new_state()

        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        bridge.resolve_tick(sid)

        # step() should receive persistent_context with player_actions
        call_kwargs = mock_step.call_args
        ctx = (
            call_kwargs.kwargs.get("persistent_context") or call_kwargs[2]
            if len(call_kwargs[0]) > 2
            else call_kwargs.kwargs.get("persistent_context")
        )
        assert ctx is not None, "persistent_context should not be None when actions exist"
        assert "player_actions" in ctx
        assert "political_faction_1" in ctx["player_actions"]

    @patch("game.engine_bridge.step")
    def test_resolve_tick_formats_action_type_from_verb(self, mock_step: MagicMock) -> None:
        """Verb should be mapped to ActionType via VERB_TO_ACTION_TYPE."""
        from game.engine_bridge import VERB_TO_ACTION_TYPE

        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = [
            {"org_id": "pf1", "verb": "educate", "target_id": "hex_abc"},
        ]
        mock_step.return_value = _make_mock_new_state()

        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        bridge.resolve_tick(sid)

        ctx = mock_step.call_args.kwargs.get("persistent_context")
        action = ctx["player_actions"]["pf1"][0]
        assert action["action_type"] == VERB_TO_ACTION_TYPE["educate"].value


@pytest.mark.unit
class TestActionResultPersistence:
    """T010: Verify ActionResult rows are written after resolve_tick()."""

    @patch("game.engine_bridge.step")
    def test_resolve_tick_persists_action_results(self, mock_step: MagicMock) -> None:
        """After step(), ActionResult rows should be written via persistence layer."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = [
            {"org_id": "pf1", "verb": "educate", "target_id": "hex_abc"},
        ]

        # Pre-step graph has target with known values
        pre_graph = _build_initial_state_for_scenario("default").to_graph()
        mock_persistence.hydrate_graph.return_value = pre_graph

        mock_step.return_value = _make_mock_new_state()

        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        bridge.resolve_tick(sid)

        # Check that persist_action_result was called (or ActionResult.objects.create)
        # The bridge should write results for each submitted action
        result_fn = getattr(mock_persistence, "persist_action_result", None)
        if result_fn is not None:
            assert result_fn.called, "persist_action_result should be called for each action"
        else:
            # If using Django ORM directly, we check via a different mechanism
            # This test verifies the bridge at least attempts result persistence
            pass  # Will be validated via integration test


@pytest.mark.unit
class TestEndgameDetection:
    """T013: Verify endgame detection integration."""

    @patch("game.engine_bridge.step")
    def test_resolve_tick_returns_endgame_in_snapshot(self, mock_step: MagicMock) -> None:
        """When EndgameDetector fires, snapshot should include endgame data."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = []

        # Create a mock state with an endgame event
        mock_new_state = _make_mock_new_state()
        endgame_event = MagicMock()
        endgame_event.event_type = "REVOLUTIONARY_VICTORY"
        endgame_event.tick = 1
        endgame_event.data = {"summary": "The people have risen"}
        mock_new_state.events = [endgame_event]
        mock_step.return_value = mock_new_state

        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        result = bridge.resolve_tick(sid)

        # The snapshot should contain the endgame event
        events = result.get("events", [])
        assert len(events) >= 1
        assert any(e.get("type") == "REVOLUTIONARY_VICTORY" for e in events)


# ---------------------------------------------------------------------- #
# Spec 092: tick_event persistence + journal/alerts dashboards
# ---------------------------------------------------------------------- #


@pytest.mark.unit
class TestTickEventPersistence:
    """Spec 092: resolve_tick writes tick_event rows for the journal/alerts
    dashboards to read back (R-CONS: endpoints built WITH their consumers)."""

    @patch("game.engine_bridge.step")
    def test_resolve_tick_persists_tick_events(self, mock_step: MagicMock) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = []

        mock_new_state = _make_mock_new_state(tick=7)
        uprising_event = MagicMock()
        uprising_event.event_type = "uprising"
        uprising_event.tick = 7
        uprising_event.data = {"org_id": "org1"}
        mock_new_state.events = [uprising_event]
        mock_step.return_value = mock_new_state

        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        bridge.resolve_tick(sid)

        assert mock_persistence.persist_tick_events.called
        call_args = mock_persistence.persist_tick_events.call_args
        assert call_args.args[0] == sid
        assert call_args.args[1] == 7
        rows = call_args.args[2]
        assert len(rows) == 1
        assert rows[0]["event_type"] == "uprising"
        assert rows[0]["severity"] == "critical"
        assert rows[0]["source_id"] == "org1"

    @patch("game.engine_bridge.step")
    def test_resolve_tick_skips_persist_when_no_events(self, mock_step: MagicMock) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = []
        mock_new_state = _make_mock_new_state(tick=3)
        mock_new_state.events = []
        mock_step.return_value = mock_new_state

        bridge = EngineBridge(mock_persistence)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        bridge.resolve_tick(sid)

        assert not mock_persistence.persist_tick_events.called


# ---------------------------------------------------------------------- #
# P0 #7: hex_latest projection at create_game / resolve_tick
# ---------------------------------------------------------------------- #


@pytest.mark.unit
@pytest.mark.django_db
class TestHexStateProjection:
    """P0 #7: create_game / resolve_tick project territories into hex_latest.

    Without this projection the map endpoint reads an empty table and
    renders zero features for every real game (only the ``seed_hex_data``
    mock-fixture command ever wrote rows).
    """

    _SID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    def _make_session_row(self) -> None:
        from game.models import GameSession

        GameSession.objects.create(
            id=self._SID, scenario="default", current_tick=0, status="active"
        )

    def test_create_game_writes_hex_latest_tick0(self) -> None:
        from game.models import HexState

        self._make_session_row()
        bridge = EngineBridge(_make_mock_persistence())

        bridge.create_game(scenario="wayne_county", rng_seed=42)

        assert HexState.objects.filter(game_id=self._SID, tick=0).count() > 0

    @patch("game.engine_bridge.step")
    def test_resolve_tick_upserts_hex_latest(self, mock_step: MagicMock) -> None:
        from babylon.models.entities import Territory
        from babylon.models.enums import SectorType
        from game.models import HexState

        self._make_session_row()
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = []

        cell = "862a91a17ffffff"  # 15-char lowercase hex, matches Territory pattern
        territory = Territory(
            id=cell, h3_index=cell, name="Test Hex", sector_type=SectorType.INDUSTRIAL
        )
        mock_new_state = _make_mock_new_state(tick=7)
        mock_new_state.territories = {cell: territory}
        mock_step.return_value = mock_new_state

        bridge = EngineBridge(mock_persistence)
        bridge.resolve_tick(self._SID)
        bridge.resolve_tick(self._SID)  # second resolve must UPDATE, not duplicate

        rows = HexState.objects.filter(game_id=self._SID)
        assert rows.count() == 1
        assert rows.first().tick == 7

    @patch("game.engine_bridge.step")
    def test_resolve_tick_skips_territories_without_h3(self, mock_step: MagicMock) -> None:
        """two_node-style territories (h3_index=None) must be skipped, not crash."""
        from babylon.models.entities import Territory
        from babylon.models.enums import SectorType
        from game.models import HexState

        self._make_session_row()
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = []
        territory = Territory(id="T001", name="Abstract", sector_type=SectorType.INDUSTRIAL)
        mock_new_state = _make_mock_new_state(tick=1)
        mock_new_state.territories = {"T001": territory}
        mock_step.return_value = mock_new_state

        EngineBridge(mock_persistence).resolve_tick(self._SID)

        assert HexState.objects.filter(game_id=self._SID).count() == 0

    @patch("game.engine_bridge.step")
    def test_resolve_tick_persists_org_count_heat_delta_and_habitability(
        self, mock_step: MagicMock
    ) -> None:
        """Spec-109 A2: org_count/heat_delta/habitability are real, not defaults."""
        from babylon.models.entities import Territory
        from babylon.models.entities.organization import CivilSocietyOrg
        from babylon.models.enums import ClassCharacter, SectorType, ServiceType
        from game.models import HexState

        self._make_session_row()
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = []

        cell = "862a91a17ffffff"  # 15-char lowercase hex, matches Territory pattern

        # Pre-step graph: territory node at heat=0.2 (what hydrate_state loads).
        # Needs every Territory-required field since hydrate_state round-trips
        # it through WorldState.from_graph().
        pre_graph = BabylonGraph()
        pre_graph.add_node(
            cell,
            node_type="territory",
            id=cell,
            h3_index=cell,
            name="Test Hex",
            sector_type="industrial",
            heat=0.2,
        )
        mock_persistence.hydrate_graph.return_value = pre_graph

        territory = Territory(
            id=cell, h3_index=cell, name="Test Hex", sector_type=SectorType.INDUSTRIAL, heat=0.7
        )
        org = CivilSocietyOrg(
            id="O001",
            name="Test Org",
            class_character=ClassCharacter.PROLETARIAN,
            service_type=ServiceType.MUTUAL_AID,
            territory_ids=[cell],
        )
        mock_new_state = _make_mock_new_state(tick=7)
        mock_new_state.territories = {cell: territory}
        mock_new_state.organizations = {"O001": org}

        # Post-step graph: same territory at heat=0.7 (matches Territory.heat
        # above) plus the graph-only habitability attr MetabolismSystem writes.
        post_graph = BabylonGraph()
        post_graph.add_node(cell, node_type="territory", heat=0.7, habitability=0.42)
        mock_new_state.to_graph.return_value = post_graph
        mock_step.return_value = mock_new_state

        bridge = EngineBridge(mock_persistence)
        bridge.resolve_tick(self._SID)

        row = HexState.objects.get(game_id=self._SID, h3_index=cell)
        assert row.org_count == 1
        assert row.heat_delta == pytest.approx(0.5)
        assert row.attributes.get("habitability") == pytest.approx(0.42)
        # No county_fips on this territory -> state_fips falls to the model
        # default rather than a fabricated derivation.
        assert row.state_fips == "26"


@pytest.mark.unit
class TestSerializeTerritoryGraphThreading:
    """Spec-109 A2: _serialize_territory reads graph-only attrs, never fakes them."""

    def _make_territory(self) -> Any:
        from babylon.models.entities import Territory
        from babylon.models.enums import SectorType

        return Territory(
            id="T001",
            name="Test Territory",
            sector_type=SectorType.INDUSTRIAL,
            wealth=12.5,
            median_wage=3.0,
            max_biocapacity=88.0,
        )

    def test_no_graph_yields_none_for_graph_only_attrs(self) -> None:
        territory = self._make_territory()

        result = _serialize_territory(territory)

        assert result["habitability"] is None
        assert result["dispossession_intensity"] is None
        assert result["wage_pressure"] is None
        assert result["consciousness"] is None
        assert result["solidarity"] is None
        assert result["dominant_community"] is None

    def test_graph_present_but_node_missing_yields_none(self) -> None:
        territory = self._make_territory()
        graph = BabylonGraph()  # T001 not in this graph

        result = _serialize_territory(territory, graph=graph)

        assert result["habitability"] is None

    def test_graph_supplies_habitability_when_written(self) -> None:
        territory = self._make_territory()
        graph = BabylonGraph()
        graph.add_node("T001", node_type="territory", habitability=0.61)

        result = _serialize_territory(territory, graph=graph)

        assert result["habitability"] == pytest.approx(0.61)

    def test_real_territory_fields_are_never_fabricated(self) -> None:
        """wealth/median_wage/max_biocapacity are real Territory fields."""
        territory = self._make_territory()

        result = _serialize_territory(territory)

        assert result["wealth"] == pytest.approx(12.5)
        assert result["median_wage"] == pytest.approx(3.0)
        assert result["max_biocapacity"] == pytest.approx(88.0)


@pytest.mark.unit
class TestOrgCountByTerritory:
    def test_counts_orgs_per_territory(self) -> None:
        orgs = [
            {"id": "O1", "territory_ids": ["T001", "T002"]},
            {"id": "O2", "territory_ids": ["T001"]},
            {"id": "O3", "territory_ids": []},
        ]

        counts = _org_count_by_territory(orgs)

        assert counts == {"T001": 2, "T002": 1}

    def test_empty_orgs_yields_empty_map(self) -> None:
        assert _org_count_by_territory([]) == {}


@pytest.mark.unit
class TestHeatDeltaByTerritory:
    def test_computes_real_post_minus_pre_diff(self) -> None:
        pre = BabylonGraph()
        pre.add_node("T001", node_type="territory", heat=0.2)
        post = BabylonGraph()
        post.add_node("T001", node_type="territory", heat=0.5)

        deltas = _heat_delta_by_territory(pre, post, ["T001"])

        assert deltas["T001"] == pytest.approx(0.3)

    def test_territory_absent_from_either_graph_is_skipped(self) -> None:
        pre = BabylonGraph()
        pre.add_node("T001", node_type="territory", heat=0.2)
        post = BabylonGraph()  # T001 never made it to the post-step graph

        deltas = _heat_delta_by_territory(pre, post, ["T001"])

        assert "T001" not in deltas


@pytest.mark.unit
class TestHexFeaturePropertiesHabitability:
    def test_habitability_read_from_attributes_json(self) -> None:
        from types import SimpleNamespace

        row = SimpleNamespace(
            h3_index="h1",
            county_fips="26163",
            county_name="Wayne",
            bea_ea_code=None,
            msa_code=None,
            profit_rate=None,
            exploitation_rate=None,
            occ=None,
            imperial_rent=None,
            heat=0.1,
            org_count=0,
            dominant_class=None,
            pop_total=0,
            attributes={"habitability": 0.77},
        )

        props = _hex_feature_properties(row)

        assert props["habitability"] == pytest.approx(0.77)

    def test_missing_attributes_yields_none_not_zero(self) -> None:
        from types import SimpleNamespace

        row = SimpleNamespace(
            h3_index="h1",
            county_fips="26163",
            county_name="Wayne",
            bea_ea_code=None,
            msa_code=None,
            profit_rate=None,
            exploitation_rate=None,
            occ=None,
            imperial_rent=None,
            heat=0.1,
            org_count=0,
            dominant_class=None,
            pop_total=0,
            attributes={},
        )

        props = _hex_feature_properties(row)

        assert props["habitability"] is None


@pytest.mark.unit
class TestHexStateRowStateFips:
    _SID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    def test_state_fips_derived_from_county_fips(self) -> None:
        row = _hex_state_row(
            self._SID,
            3,
            {"h3_index": "862a91a17ffffff", "county_fips": "26163", "name": "Wayne"},
        )

        assert row is not None
        assert row["state_fips"] == "26"

    def test_state_fips_absent_when_no_county_fips(self) -> None:
        row = _hex_state_row(
            self._SID,
            3,
            {"h3_index": "862a91a17ffffff", "county_fips": None, "name": "Abstract"},
        )

        assert row is not None
        assert "state_fips" not in row


@pytest.mark.unit
class TestJournalDashboard:
    """Spec 092: get_journal_dashboard reads persisted tick_event history."""

    def test_returns_empty_when_persistence_lacks_query_method(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_session_events = None  # simulate SQLite RuntimeDatabase
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_journal_dashboard(uuid.uuid4())

        assert result == {"events": []}

    def test_returns_events_from_query_session_events(self) -> None:
        mock_persistence = _make_mock_persistence()
        sid = uuid.uuid4()
        mock_persistence.query_session_events.return_value = [
            {
                "game_id": str(sid),
                "tick": 5,
                "event_id": 3,
                "event_type": "uprising",
                "severity": "critical",
                "source_id": "org1",
                "target_id": None,
                "county_fips": None,
                "h3_index": None,
                "summary": "Uprising erupts",
                "detail": {"org_id": "org1"},
            }
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_journal_dashboard(sid)

        assert len(result["events"]) == 1
        event = result["events"][0]
        assert event["type"] == "uprising"
        assert event["severity"] == "critical"
        assert event["tick"] == 5
        assert event["body"] == "Uprising erupts"
        assert event["data"] == {"org_id": "org1"}

    def test_query_failure_degrades_to_empty(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_session_events.side_effect = RuntimeError("boom")
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_journal_dashboard(uuid.uuid4())

        assert result == {"events": []}


@pytest.mark.unit
class TestAlertsDashboard:
    """Spec 092: get_alerts_dashboard filters the latest tick's events to
    critical/warning severities (the Tick Resolution screen's alert feed)."""

    def test_returns_empty_when_persistence_lacks_query_method(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_tick_events = None  # simulate SQLite RuntimeDatabase
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_alerts_dashboard(uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))

        assert result == {"alerts": []}

    def test_returns_critical_and_warning_only(self) -> None:
        mock_persistence = _make_mock_persistence()
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        mock_persistence.query_tick_events.return_value = [
            {
                "game_id": str(sid),
                "tick": 0,
                "event_id": 1,
                "event_type": "uprising",
                "severity": "critical",
                "source_id": None,
                "target_id": None,
                "county_fips": None,
                "h3_index": None,
                "summary": "Uprising",
                "detail": {},
            },
            {
                "game_id": str(sid),
                "tick": 0,
                "event_id": 2,
                "event_type": "wage_payment",
                "severity": "informational",
                "source_id": None,
                "target_id": None,
                "county_fips": None,
                "h3_index": None,
                "summary": "Wages paid",
                "detail": {},
            },
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_alerts_dashboard(sid)

        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["type"] == "uprising"


@pytest.mark.unit
class TestWireFeed:
    """Spec 094: get_wire_feed produces a WireFeed via DeterministicNarrator."""

    def test_returns_valid_wirefeed_shape(self) -> None:
        mock_persistence = _make_mock_persistence()
        sid = uuid.uuid4()
        mock_persistence.query_session_events.return_value = [
            {
                "game_id": str(sid),
                "tick": 5,
                "event_id": 1,
                "event_type": "uprising",
                "severity": "critical",
                "source_id": "org1",
                "target_id": None,
                "county_fips": None,
                "h3_index": None,
                "summary": "Uprising erupts",
                "detail": {"org_id": "org1", "territory_id": "t_hamtramck"},
            }
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_wire_feed(sid)

        assert "meta" in result
        assert "index" in result
        assert "euphemisms" in result
        assert "story" in result
        assert "filters" in result
        assert len(result["filters"]) == 5
        assert len(result["index"]) == 1

    def test_empty_events_produces_empty_feed(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_session_events = None
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_wire_feed(uuid.uuid4())

        assert result["index"] == []
        assert result["euphemisms"] == {}
        assert result["story"] is None
        assert len(result["filters"]) == 5

    def test_feed_is_deterministic(self) -> None:
        mock_persistence = _make_mock_persistence()
        sid = uuid.uuid4()
        mock_persistence.query_session_events.return_value = [
            {
                "game_id": str(sid),
                "tick": 5,
                "event_id": 1,
                "event_type": "uprising",
                "severity": "critical",
                "source_id": "org1",
                "target_id": None,
                "county_fips": None,
                "h3_index": None,
                "summary": "Uprising",
                "detail": {"territory_id": "t_hamtramck"},
            }
        ]
        bridge = EngineBridge(mock_persistence)

        import json

        out_a = bridge.get_wire_feed(sid)
        out_b = bridge.get_wire_feed(sid)
        assert json.dumps(out_a, sort_keys=True) == json.dumps(out_b, sort_keys=True)


# --------------------------------------------------------------------- #
# Spec 093: Territory Detail / Org Detail / Map Lens Set — shared fixture
# --------------------------------------------------------------------- #
#
# NOTE: WorldState.from_graph() reconstructs every non-territory/
# organization/key_figure/institution/industry node as a SocialClass, whose
# model_config is `extra="forbid"` — so a graph containing spec-070
# `faction`/`sovereign`/`community` nodes crashes `hydrate_state()`'s
# internal `WorldState.from_graph()` call (confirmed empirically; a
# pre-existing engine-layer gap, out of this spec's `web/**` ownership).
# Tests that need those node types patch `EngineBridge.hydrate_state`
# directly so they exercise the same `graph` object the real bridge
# methods already read via `graph.nodes[...]`, without going through the
# crashing reconstruction path.


def _patched_hydrate_state(bridge: EngineBridge, graph: BabylonGraph, tick: int = 10) -> Any:
    """Patch ``bridge.hydrate_state`` to return ``(mock_state, graph)`` directly."""
    mock_state = MagicMock()
    mock_state.tick = tick
    return patch.object(bridge, "hydrate_state", return_value=(mock_state, graph))


def _make_balkanization_graph() -> BabylonGraph:
    """Build a graph with orgs, territories, social classes, and spec-070
    faction/sovereign/INFLUENCES/CLAIMS data for de-fixture + balkanization
    tests. Territory "T1" is contested (two factions close in influence);
    "T2" has a single dominant faction and a sovereign claim.

    Matches the real engine's graph shape:
    - extraction_intensity lives on Territory nodes (ProductionSystem)
    - edge_mode is a separate attribute from edge_type (EdgeTransitionSystem)
    - No community nodes in the main graph (they live in XGI hypergraph)
    """
    g = BabylonGraph()
    g.graph["tick"] = 10
    g.graph["economy"] = {"imperial_rent": 0.0}
    g.graph["state_finances"] = {}
    g.graph["events"] = []
    g.graph["event_log"] = []

    g.add_node(
        "org-player",
        "organization",
        name="Vanguard Cell",
        org_type="political_faction",
        cadre_level=5.0,
        cohesion=0.6,
        budget=200.0,
        heat=0.3,
        territory_ids=["T1", "T2"],
    )
    g.add_node(
        "T1",
        "territory",
        name="Genesee County",
        county_fips="26049",
        heat=0.4,
        rent_level=1.2,
        population=5000,
        biocapacity=40.0,
        max_biocapacity=100.0,
        extraction_intensity=0.41,
    )
    g.add_node(
        "T2",
        "territory",
        name="Washtenaw County",
        county_fips="26161",
        heat=0.2,
        rent_level=0.9,
        population=8000,
        biocapacity=90.0,
        max_biocapacity=100.0,
    )
    g.add_node(
        "sc-genesee-proles",
        "social_class",
        name="Genesee Proletariat",
        role="proletariat",
        wealth=812.4,
        agitation=0.62,
        territory_ids=["T1"],
    )
    g.add_edge(
        "org-player",
        "sc-genesee-proles",
        "exploitation",
        edge_mode="extractive",
        value_flow=118.9,
        tension=0.34,
    )

    g.add_node("FAC_A", "faction", colonial_stance="UPHOLD", is_settler_formation=True)
    g.add_node("FAC_B", "faction", colonial_stance="IGNORE", is_settler_formation=True)
    g.add_node(
        "SOV_A",
        "sovereign",
        ruling_faction_id="FAC_A",
        extraction_policy="INTENSIFY",
        legitimacy=0.58,
    )
    # T1: contested — two factions within the 0.12 delta.
    g.add_edge("FAC_A", "T1", "influences", influence_level=0.47, support_type="ideological")
    g.add_edge("FAC_B", "T1", "influences", influence_level=0.41, support_type="material")
    # T2: dominant, claimed by SOV_A.
    g.add_edge("FAC_A", "T2", "influences", influence_level=0.71, support_type="ideological")
    g.add_edge("SOV_A", "T2", "claims", control_level=0.8, legal_status="de_jure")

    return g


@pytest.mark.unit
class TestGetEconomy:
    """Spec 093 US5: get_economy(session_id, territory_id) real per-territory summary."""

    def test_territory_not_found_returns_no_data(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_economy(uuid.uuid4(), territory_id="not-a-territory")

        assert result["has_data"] is False
        assert result["value_produced"] == 0.0
        assert result["rent_extracted"] == 0.0
        assert result["exploitation_rate"] is None

    def test_real_data_derived_from_nodes_and_edges(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_economy(uuid.uuid4(), territory_id="T1")

        assert result["has_data"] is True
        assert result["value_produced"] == pytest.approx(812.4)
        assert result["rent_extracted"] == pytest.approx(118.9)
        assert result["exploitation_rate"] is not None
        assert result["extraction_intensity"] == pytest.approx(0.41)

    def test_territory_with_no_economic_nodes_is_honest_zero(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_economy(uuid.uuid4(), territory_id="T2")

        assert result["has_data"] is False
        assert result["value_produced"] == 0.0
        assert result["exploitation_rate"] is None

    def test_no_territory_id_delegates_to_dashboard(self) -> None:
        # Spec 109 A4: get_economy_dashboard is real now (no longer a `{}`
        # stub) — the delegation contract this test verifies is that
        # omitting territory_id returns exactly what get_economy_dashboard
        # returns for the same session, not a fixed literal.
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        session_id = uuid.uuid4()

        result = bridge.get_economy(session_id)

        assert result == bridge.get_economy_dashboard(session_id)


@pytest.mark.unit
class TestBalkanizationMapFields:
    """Spec 093 US3: get_map_snapshot's balkanization block (real spec-070 graph reads)."""

    def test_balkanization_block_present_with_real_factions_and_sovereigns(self) -> None:
        mock_persistence = _make_mock_persistence()
        graph = _make_balkanization_graph()
        mock_persistence.hydrate_graph.return_value = graph
        with patch("game.models.GameSession") as mock_session_model:
            mock_session_row = MagicMock()
            mock_session_row.current_tick = 10
            mock_session_row.scenario = "default"
            mock_session_model.objects.get.return_value = mock_session_row
            with patch("game.models.HexState") as mock_hex_state:
                mock_hex_state.objects.filter.return_value = []
                bridge = EngineBridge(mock_persistence)
                result = bridge.get_map_snapshot(uuid.uuid4())

        balk = result["metadata"]["balkanization"]
        faction_ids = {f["id"] for f in balk["factions"]}
        assert faction_ids == {"FAC_A", "FAC_B"}
        assert balk["sovereigns"][0]["id"] == "SOV_A"
        assert balk["sovereigns"][0]["claimed_territory_ids"] == ["T2"]

        by_id = {t["territory_id"]: t for t in balk["territory_influence"]}
        assert by_id["T1"]["contested"] is True
        assert by_id["T1"]["dominant_faction_id"] == "FAC_A"
        assert by_id["T2"]["contested"] is False
        assert by_id["T2"]["current_sovereign_id"] == "SOV_A"
        assert by_id["T1"]["habitability"] == pytest.approx(0.4)


@pytest.mark.unit
class TestDefixturedVerbTargets:
    """Spec 093 US4: the 5 verb-target methods derive real graph data,
    iterate ALL of the org's territories, and never fall back to a
    hardcoded Wayne County / FIPS 26163 fixture."""

    NO_FIXTURE_LITERALS = ("Wayne County", "territory-26163", "wayne", "26163")

    def _assert_no_fixture_literals(self, payload: object) -> None:
        text = str(payload)
        for literal in self.NO_FIXTURE_LITERALS:
            assert literal not in text, f"found fixture literal {literal!r} in {text[:200]}"

    def test_educate_targets_reads_real_social_class_nodes(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_educate_targets(uuid.uuid4(), "org-player")

        assert result["status"] == "ok"
        assert len(result["targets"]) >= 1
        target = result["targets"][0]
        assert target["community_id"] == "sc-genesee-proles"
        assert target["material_readiness"]["avg_agitation"] == pytest.approx(0.62)
        self._assert_no_fixture_literals(result)

    def test_educate_targets_iterates_all_territories_not_just_first(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.add_node(
            "sc-washtenaw-proles",
            "social_class",
            name="Washtenaw Proletariat",
            role="proletariat",
            wealth=200.0,
            agitation=0.2,
            territory_ids=["T2"],
        )

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_educate_targets(uuid.uuid4(), "org-player")

        territory_ids = {t["territory_id"] for t in result["targets"]}
        assert territory_ids == {"T1", "T2"}

    def test_educate_targets_empty_when_org_has_no_territories(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.update_node("org-player", territory_ids=[])

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_educate_targets(uuid.uuid4(), "org-player")

        assert result["targets"] == []

    def test_aid_targets_reads_real_territory_data(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_aid_targets(uuid.uuid4(), "org-player")

        assert result["status"] == "ok"
        self._assert_no_fixture_literals(result)
        assert len(result["population_targets"]) >= 1

    def test_aid_targets_empty_when_org_has_no_territories(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.update_node("org-player", territory_ids=[])

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_aid_targets(uuid.uuid4(), "org-player")

        assert result["population_targets"] == []
        assert result["org_targets"] == []

    def test_mobilize_targets_no_fixture_literals(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_mobilize_targets(uuid.uuid4(), "org-player")

        self._assert_no_fixture_literals(result)

    def test_attack_targets_no_fixture_literals(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_attack_targets(uuid.uuid4(), "org-player")

        self._assert_no_fixture_literals(result)

    def test_reproduce_targets_no_fixture_literals(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_reproduce_targets(uuid.uuid4(), "org-player")

        self._assert_no_fixture_literals(result)


@pytest.mark.unit
class TestDefixturedQueryCorrectness:
    """Regression tests for spec-093 review findings #1-#4: the de-fixtured
    queries must read the CORRECT node types, attributes, and enum values
    that the real engine writes — not the wrong ones that silently returned
    empty results."""

    def test_extraction_intensity_read_from_territory_node(self) -> None:
        """Finding #3: extraction_intensity lives on Territory nodes, not
        social_class/organization nodes. The old code read it from the wrong
        node type and always got empty."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_economy(uuid.uuid4(), territory_id="T1")

        assert result["extraction_intensity"] == pytest.approx(0.41)

    def test_extractive_edges_read_edge_mode_attribute(self) -> None:
        """Finding #2: the engine writes edge_mode as a separate attribute
        from edge_type. The old code read edge_type (which carries EdgeType
        values like 'exploitation') and compared against EdgeMode values
        like 'extractive' — always empty."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_economy(uuid.uuid4(), territory_id="T1")

        assert result["rent_extracted"] == pytest.approx(118.9)

    def test_educate_targets_uses_social_class_not_community(self) -> None:
        """Finding #1: community nodes live in the XGI hypergraph, not the
        main graph. The old code queried _node_type=='community' which never
        exists in production. Correct targets are social_class nodes."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_educate_targets(uuid.uuid4(), "org-player")

        assert len(result["targets"]) >= 1
        target_ids = {t["community_id"] for t in result["targets"]}
        assert "sc-genesee-proles" in target_ids

    def test_mobilize_targets_uses_correct_org_type_enum(self) -> None:
        """Finding #4: OrgType.CIVIL_SOCIETY.value is 'civil_society', not
        'civil_society_org'. The old code filtered the wrong string and
        missed all civil-society organizations."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.add_node(
            "org-civil-society",
            "organization",
            name="Tenants Union",
            org_type="civil_society",
            heat=0.5,
            cohesion=0.4,
            territory_ids=["T1"],
        )

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_mobilize_targets(uuid.uuid4(), "org-player")

        target_ids = {t["id"] for t in result["targets"]}
        assert "org-civil-society" in target_ids


@pytest.mark.unit
class TestSessionScopedDefines:
    """C.13: resolve_tick must read GameDefines from the session's own
    game_session row, never from the global metadata blob."""

    @patch("game.engine_bridge.step")
    def test_resolve_tick_uses_session_defines(self, mock_step: MagicMock) -> None:
        """Defines stored on the session row must reach step()."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_session.return_value = {
            "scenario": "default",
            "game_defines_json": {"economy": {"extraction_efficiency": 0.5}},
        }
        mock_step.return_value = _make_mock_new_state()
        bridge = EngineBridge(mock_persistence)

        bridge.resolve_tick(uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))

        defines = mock_step.call_args.kwargs["defines"]
        assert defines.economy.extraction_efficiency == 0.5

    @patch("game.engine_bridge.step")
    def test_resolve_tick_ignores_global_metadata_blob(self, mock_step: MagicMock) -> None:
        """Another session's defines in the global metadata key must NOT leak in."""
        import json as json_mod

        mock_persistence = _make_mock_persistence()
        mock_persistence.get_metadata.return_value = json_mod.dumps(
            {"economy": {"extraction_efficiency": 0.1}}
        )
        mock_persistence.get_session.return_value = {
            "scenario": "default",
            "game_defines_json": {},
        }
        mock_step.return_value = _make_mock_new_state()
        bridge = EngineBridge(mock_persistence)

        bridge.resolve_tick(uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))

        defines = mock_step.call_args.kwargs["defines"]
        assert defines.economy.extraction_efficiency == 0.8  # library default, not 0.1

    @patch("game.engine_bridge.step")
    def test_resolve_tick_parses_string_defines(self, mock_step: MagicMock) -> None:
        """SQLite TEXT storage returns a JSON string — must still parse."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_session.return_value = {
            "scenario": "default",
            "game_defines_json": '{"economy": {"extraction_efficiency": 0.5}}',
        }
        mock_step.return_value = _make_mock_new_state()
        bridge = EngineBridge(mock_persistence)

        bridge.resolve_tick(uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))

        assert mock_step.call_args.kwargs["defines"].economy.extraction_efficiency == 0.5

    @patch("game.engine_bridge.step")
    def test_resolve_tick_defaults_when_row_missing(self, mock_step: MagicMock) -> None:
        """A missing session row degrades to library defaults, not a crash."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_session.return_value = None
        mock_step.return_value = _make_mock_new_state()
        bridge = EngineBridge(mock_persistence)

        bridge.resolve_tick(uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))

        assert mock_step.call_args.kwargs["defines"].economy.extraction_efficiency == 0.8


@pytest.mark.unit
class TestResolveTickConsumesEngineResults:
    """Verb-dispatch engine: resolve_tick persists the REAL per-action results
    from the engine's TurnResolution — not the old blind ``success=True`` /
    ``class_consciousness`` pre/post diff.
    """

    _SID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    @patch("game.engine_bridge.step")
    def test_persists_success_and_ci_from_turn_resolution(self, mock_step: MagicMock) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = [
            {"org_id": "pf1", "verb": "educate", "target_id": "hex_abc"},
        ]

        def fake_step(*_args: Any, **kwargs: Any) -> MagicMock:
            ctx = kwargs.get("persistent_context")
            assert ctx is not None, "persistent_context must be threaded to step"
            ctx["turn_resolution"] = {
                "action_phase_results": [
                    {
                        "action": {
                            "org_id": "pf1",
                            "action_type": "educate",
                            "target_id": "hex_abc",
                        },
                        "success": True,
                        "consciousness_delta": {"collective_identity_delta": 0.05},
                        "direct_effects": {"note": "real"},
                        "failure_reason": None,
                    }
                ]
            }
            return _make_mock_new_state()

        mock_step.side_effect = fake_step
        bridge = EngineBridge(mock_persistence)
        bridge.resolve_tick(self._SID)

        mock_persistence.persist_action_result.assert_called_once()
        kwargs = mock_persistence.persist_action_result.call_args.kwargs
        assert kwargs["success"] is True
        assert kwargs["consciousness_delta"] == 0.05
        assert kwargs["details"]["direct_effects"] == {"note": "real"}
        assert kwargs["details"]["failure_reason"] is None

    @patch("game.engine_bridge.step")
    def test_missing_engine_result_is_loud_failure(self, mock_step: MagicMock) -> None:
        """No turn_resolution for the org => success=False persisted (never
        the old blind ``success=True``)."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = [
            {"org_id": "pf1", "verb": "educate", "target_id": "hex_abc"},
        ]
        mock_step.return_value = _make_mock_new_state()  # writes no turn_resolution
        bridge = EngineBridge(mock_persistence)
        bridge.resolve_tick(self._SID)

        mock_persistence.persist_action_result.assert_called_once()
        kwargs = mock_persistence.persist_action_result.call_args.kwargs
        assert kwargs["success"] is False
        assert kwargs["details"]["failure_reason"] is not None


# ---------------------------------------------------------------------- #
# Spec-111: resolve_tick's narrative_service hook (region-disjoint,
# additive-only — see game/narrative_service.py)
# ---------------------------------------------------------------------- #


@pytest.mark.unit
class TestResolveTickNarrativeServiceHook:
    """Verify resolve_tick schedules narrative generation without blocking."""

    @patch("game.engine_bridge.step")
    def test_resolve_tick_calls_narrative_service_schedule(self, mock_step: MagicMock) -> None:
        mock_persistence = _make_mock_persistence()
        mock_new_state = _make_mock_new_state()
        mock_step.return_value = mock_new_state
        mock_narrative_service = MagicMock()
        mock_narrative_service.schedule.return_value = None

        bridge = EngineBridge(mock_persistence, narrative_service=mock_narrative_service)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        bridge.resolve_tick(sid)

        mock_narrative_service.schedule.assert_called_once()
        call_args = mock_narrative_service.schedule.call_args.args
        assert call_args[0] == sid
        # previous_state is the hydrated pre-step WorldState; new_state is
        # whatever step() returned — both passed through unmodified.
        assert call_args[2] is mock_new_state

    @patch("game.engine_bridge.step")
    def test_resolve_tick_returns_snapshot_without_waiting_on_narrative(
        self, mock_step: MagicMock
    ) -> None:
        """resolve_tick must not block on narrative generation (never blocks /resolve/)."""
        mock_persistence = _make_mock_persistence()
        mock_step.return_value = _make_mock_new_state()

        blocking_service = MagicMock()

        def _never_finishes(*_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("resolve_tick must not synchronously await narrative generation")

        # schedule() itself must be safe to call synchronously (fire-and-forget
        # submission to a background executor) — resolve_tick calling it
        # directly, and getting back immediately, IS the non-blocking
        # contract; a real NarrativeService.schedule() never runs generation
        # on the calling thread. This mock just proves resolve_tick doesn't
        # try to read a result back from schedule()'s return value.
        blocking_service.schedule.return_value = MagicMock()

        bridge = EngineBridge(mock_persistence, narrative_service=blocking_service)
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        result = bridge.resolve_tick(sid)

        assert isinstance(result, dict)
        assert result["tick"] == 1
        blocking_service.schedule.assert_called_once()

    @patch("game.engine_bridge.step")
    def test_resolve_tick_default_narrative_service_flag_off_is_inert(
        self, mock_step: MagicMock
    ) -> None:
        """With no narrative_service injected and the flag off (test default),
        resolve_tick behaves exactly as before spec-111 — no exception, same
        snapshot shape."""
        mock_persistence = _make_mock_persistence()
        mock_step.return_value = _make_mock_new_state()
        bridge = EngineBridge(mock_persistence)  # narrative_service=None -> lazy default
        sid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        result = bridge.resolve_tick(sid)

        assert result["tick"] == 1
