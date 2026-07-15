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

from babylon.models.enums import EventType
from babylon.models.events import SimulationEvent
from babylon.topology.graph import BabylonGraph
from game.engine_bridge import (
    _MAP_HISTORY_WINDOW_CAP,
    EngineBridge,
    _build_initial_state_for_scenario,
    _heat_delta_by_territory,
    _hex_feature_properties,
    _hex_state_row,
    _mean_territory_attr,
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
    def test_resolve_tick_upsert_updates_phi_columns_on_second_write(
        self, mock_step: MagicMock
    ) -> None:
        """Program 17 / Item 1a-followup: ``_persist_hex_state_safe``'s bulk_create
        ``update_fields`` omitted profit_rate/exploitation_rate/occ/imperial_rent,
        so once Phi went non-zero these 4 columns populated on the FIRST insert
        but froze on every later tick's UPSERT (the map reads hex_latest). A
        second resolve_tick with DIFFERENT tick_-attr values must actually move
        these columns, not leave them stuck at the first tick's numbers.
        """
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

        mock_new_state_1 = _make_mock_new_state(tick=1)
        mock_new_state_1.territories = {cell: territory}
        graph_tick1 = BabylonGraph()
        graph_tick1.add_node(
            cell,
            node_type="territory",
            tick_profit_rate=0.10,
            tick_exploitation_rate=0.20,
            tick_occ=0.30,
            tick_phi_hour=0.40,
        )
        mock_new_state_1.to_graph.return_value = graph_tick1
        mock_step.return_value = mock_new_state_1

        bridge = EngineBridge(mock_persistence)
        bridge.resolve_tick(self._SID)

        row = HexState.objects.get(game_id=self._SID, h3_index=cell)
        assert row.profit_rate == pytest.approx(0.10)
        assert row.exploitation_rate == pytest.approx(0.20)
        assert row.occ == pytest.approx(0.30)
        assert row.imperial_rent == pytest.approx(0.40)

        # Second tick: DIFFERENT values. Before the fix, these 4 columns
        # would stay frozen at the first tick's numbers on this UPSERT.
        mock_new_state_2 = _make_mock_new_state(tick=2)
        mock_new_state_2.territories = {cell: territory}
        graph_tick2 = BabylonGraph()
        graph_tick2.add_node(
            cell,
            node_type="territory",
            tick_profit_rate=0.55,
            tick_exploitation_rate=0.65,
            tick_occ=0.75,
            tick_phi_hour=0.85,
        )
        mock_new_state_2.to_graph.return_value = graph_tick2
        mock_step.return_value = mock_new_state_2

        bridge.resolve_tick(self._SID)

        row.refresh_from_db()
        assert row.profit_rate == pytest.approx(0.55)
        assert row.exploitation_rate == pytest.approx(0.65)
        assert row.occ == pytest.approx(0.75)
        assert row.imperial_rent == pytest.approx(0.85)

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

    def test_no_graph_yields_none_for_group_a_b_tick_attrs(self) -> None:
        """Wave 2 Gap-1: Group A/B tick_* reads are honest None without a graph."""
        territory = self._make_territory()

        result = _serialize_territory(territory)

        assert result["crisis_phase"] is None
        assert result["crisis_duration"] is None
        assert result["bifurcation_score"] is None
        assert result["wage_compression"] is None
        assert result["capital_stock"] is None
        assert result["class_distribution"] is None
        assert result["unemployment_rate"] is None
        assert result["tick_median_wage"] is None

    def test_graph_supplies_group_a_b_tick_attrs_when_written(self) -> None:
        """Wave 2 Gap-1: Group A/B surface from the graph-only tick_* attrs."""
        territory = self._make_territory()
        graph = BabylonGraph()
        dist = {
            "bourgeoisie": 0.02,
            "petit_bourgeoisie": 0.08,
            "labor_aristocracy": 0.30,
            "proletariat": 0.40,
            "lumpenproletariat": 0.20,
        }
        graph.add_node(
            "T001",
            node_type="territory",
            tick_crisis_phase="deep",
            tick_crisis_duration=7,
            tick_bifurcation_score=-0.65,
            tick_wage_compression=0.22,
            tick_capital_stock=1e9,
            tick_class_distribution=dist,
            tick_unemployment_rate=0.081,
            tick_median_wage=21.0,
        )

        result = _serialize_territory(territory, graph=graph)

        assert result["crisis_phase"] == "deep"
        assert result["crisis_duration"] == 7
        assert result["bifurcation_score"] == pytest.approx(-0.65)
        assert result["wage_compression"] == pytest.approx(0.22)
        assert result["capital_stock"] == pytest.approx(1e9)
        assert result["class_distribution"] == dist
        assert result["unemployment_rate"] == pytest.approx(0.081)
        assert result["tick_median_wage"] == pytest.approx(21.0)
        # tick_median_wage must not collide with the real Territory.median_wage
        # field (Feature 021) — both are present, distinctly.
        assert result["median_wage"] == pytest.approx(3.0)


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
class TestMeanTerritoryAttr:
    """Wave 2 Gap-1 Backend-1: get_economy_dashboard's profit_rate/occ mean."""

    def test_averages_non_null_values_across_territories(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T001", node_type="territory", tick_profit_rate=0.10)
        graph.add_node("T002", node_type="territory", tick_profit_rate=0.20)

        result = _mean_territory_attr(graph, "tick_profit_rate")

        assert result == pytest.approx(0.15)

    def test_excludes_territories_missing_the_attr_never_fabricates_zero(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T001", node_type="territory", tick_profit_rate=0.10)
        graph.add_node("T002", node_type="territory")  # no boundary yet this session

        result = _mean_territory_attr(graph, "tick_profit_rate")

        assert result == pytest.approx(0.10)

    def test_ignores_non_territory_nodes(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T001", node_type="territory", tick_profit_rate=0.10)
        graph.add_node("C001", node_type="social_class", tick_profit_rate=99.0)

        result = _mean_territory_attr(graph, "tick_profit_rate")

        assert result == pytest.approx(0.10)

    def test_no_territory_carries_attr_yields_none(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T001", node_type="territory")

        assert _mean_territory_attr(graph, "tick_profit_rate") is None

    def test_empty_graph_yields_none(self) -> None:
        graph = BabylonGraph()

        assert _mean_territory_attr(graph, "tick_profit_rate") is None


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

    def test_class_scoped_event_narrates_the_scenario_name_not_the_canonical_map(self) -> None:
        """W1.7: wayne_county reuses canonical class ids under different
        names (its C002 is "Suburban Petty Bourgeoisie"; the registry's C002
        is the Comprador). ``get_wire_feed`` must pass the hydrated state's
        real names to the narrator via ``meta["class_names"]`` so a
        class-scoped event never narrates a confidently wrong name."""
        from game.engine_bridge import _build_initial_state_for_scenario

        mock_persistence = _make_mock_persistence()
        mock_persistence.hydrate_graph.return_value = _build_initial_state_for_scenario(
            "wayne_county"
        ).to_graph()
        sid = uuid.uuid4()
        mock_persistence.query_session_events.return_value = [
            {
                "game_id": str(sid),
                "tick": 5,
                "event_id": 1,
                "event_type": "fascist_drift",
                "severity": "warning",
                "source_id": None,
                "target_id": None,
                "county_fips": None,
                "h3_index": None,
                "summary": "Class drifted fascist",
                "detail": {
                    "node_id": "C002",
                    "fascist_pull": 0.71,
                    "fascist_alignment": 0.42,
                    "entitlement": 0.66,
                    "solidarity": 0.12,
                    "regime": "crisis",
                },
            }
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_wire_feed(sid)

        feed_json = json.dumps(result)
        assert "Suburban Petty Bourgeoisie" in feed_json
        assert "Comprador" not in feed_json
        assert "class_names" not in result["meta"]

    def test_org_scoped_event_narrates_the_scenario_org_name(self) -> None:
        """AW3-R1: RED_BROWN_COUP is org-scoped (``org_id``), not
        class- or territory-scoped. ``get_wire_feed`` must pass the
        hydrated state's real org names to the narrator via
        ``meta["org_names"]`` so the story names the org (wayne_county's
        ORG001 is "Wayne County Organizing Committee") rather than the
        raw id or a fabricated "Wayne County" location — mirrors
        ``test_class_scoped_event_narrates_the_scenario_name_not_the_canonical_map``."""
        from game.engine_bridge import _build_initial_state_for_scenario

        mock_persistence = _make_mock_persistence()
        mock_persistence.hydrate_graph.return_value = _build_initial_state_for_scenario(
            "wayne_county"
        ).to_graph()
        sid = uuid.uuid4()
        mock_persistence.query_session_events.return_value = [
            {
                "game_id": str(sid),
                "tick": 5,
                "event_id": 1,
                "event_type": "red_brown_coup",
                "severity": "critical",
                "source_id": None,
                "target_id": None,
                "county_fips": None,
                "h3_index": None,
                "summary": "Majority LA defection",
                "detail": {
                    "org_id": "ORG001",
                    "defections": 4,
                    "member_count": 6,
                },
            }
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_wire_feed(sid)

        feed_json = json.dumps(result)
        assert "Wayne County Organizing Committee" in feed_json
        assert "org_names" not in result["meta"]

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


@pytest.mark.unit
class TestClassSnapshotRows:
    """Wave 2 W2.5b (owner ruling 3): ``_class_snapshot_rows`` projects
    ``_serialize_entity`` dicts onto ``class_snapshot`` columns — mirrors
    ``_org_snapshot_rows``/``_territory_snapshot_rows``."""

    def test_maps_survival_calculus_and_material_fields(self) -> None:
        from game.engine_bridge import _class_snapshot_rows

        entities = [
            {
                "id": "C004",
                "name": "Dearborn Industrial Workers",
                "role": "periphery_proletariat",
                "wealth": 0.35,
                "consciousness": 0.1,
                "national_identity": 0.6,
                "agitation": 0.2,
                "organization": 0.15,
                "repression": 0.4,
                "p_acquiescence": 0.6,
                "p_revolution": 0.3,
                "subsistence": 0.25,
                "population": 300000,
                "inequality": 0.5,
                "active": True,
            }
        ]

        rows = _class_snapshot_rows(entities)

        assert len(rows) == 1
        row = rows[0]
        assert row["class_id"] == "C004"
        assert row["role"] == "periphery_proletariat"
        assert row["wealth"] == pytest.approx(0.35)
        assert row["subsistence_threshold"] == pytest.approx(0.25)
        assert row["organization"] == pytest.approx(0.15)
        assert row["repression_faced"] == pytest.approx(0.4)
        assert row["class_consciousness"] == pytest.approx(0.1)
        assert row["national_identity"] == pytest.approx(0.6)
        assert row["agitation"] == pytest.approx(0.2)
        assert row["p_acquiescence"] == pytest.approx(0.6)
        assert row["p_revolution"] == pytest.approx(0.3)
        assert row["population"] == 300000
        assert row["inequality"] == pytest.approx(0.5)
        assert row["active"] is True
        assert isinstance(row["attributes"], dict)

    def test_skips_entities_missing_id_or_role(self) -> None:
        from game.engine_bridge import _class_snapshot_rows

        entities = [{"id": None, "role": "proletariat"}, {"id": "C001", "role": None}]

        assert _class_snapshot_rows(entities) == []

    def test_persist_snapshots_safe_wires_class_rows(self) -> None:
        """``_persist_snapshots_safe`` must reactivate ``_serialize_entity``
        (dead code, zero call sites pre-W2.5b) and pass ``classes=`` to
        ``persist_full_tick`` alongside territories/orgs/edges — the exact
        real ``wayne_county`` C001-C004 roster, DB-free via a MagicMock."""
        from game.engine_bridge import _build_initial_state_for_scenario, _persist_snapshots_safe

        state = _build_initial_state_for_scenario("wayne_county")
        mock_persistence = MagicMock()

        _persist_snapshots_safe(mock_persistence, uuid.uuid4(), state)

        mock_persistence.persist_full_tick.assert_called_once()
        _, kwargs = mock_persistence.persist_full_tick.call_args
        assert "classes" in kwargs
        class_ids = {row["class_id"] for row in kwargs["classes"]}
        assert class_ids == {"C001", "C002", "C003", "C004"}


@pytest.mark.unit
class TestGetClassHistory:
    """Wave 2 W2.5b (owner ruling 3): real ``class_snapshot`` history + the
    honest UPRISING/revolutionary_pressure rupture markers — mirrors
    ``get_org_history``/``get_territory_history``."""

    def test_returns_empty_when_persistence_lacks_query_methods(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_class_snapshot_history = None  # simulate SQLite RuntimeDatabase
        mock_persistence.query_node_uprising_events = None
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_class_history(uuid.uuid4(), "C004")

        assert result == {"class_id": "C004", "history": [], "ruptures": []}

    def test_returns_history_rows_and_rupture_markers(self) -> None:
        mock_persistence = _make_mock_persistence()
        sid = uuid.uuid4()
        mock_persistence.query_class_snapshot_history.return_value = [
            {"tick": 0, "p_acquiescence": 0.7, "p_revolution": 0.1},
            {"tick": 1, "p_acquiescence": 0.6, "p_revolution": 0.4},
        ]
        mock_persistence.query_node_uprising_events.return_value = [
            {
                "tick": 1,
                "event_type": "uprising",
                "severity": "critical",
                "source_id": None,
                "target_id": None,
                "county_fips": None,
                "h3_index": None,
                "summary": "Uprising erupts",
                "detail": {"node_id": "C004", "trigger": "revolutionary_pressure"},
            }
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_class_history(sid, "C004")

        assert result["class_id"] == "C004"
        assert len(result["history"]) == 2
        assert result["history"][0]["tick"] == 0
        assert len(result["ruptures"]) == 1
        rupture = result["ruptures"][0]
        assert rupture["type"] == "uprising"
        assert rupture["tick"] == 1
        assert rupture["data"]["trigger"] == "revolutionary_pressure"
        mock_persistence.query_class_snapshot_history.assert_called_once_with(sid, "C004")
        mock_persistence.query_node_uprising_events.assert_called_once_with(sid, "C004")

    def test_history_query_failure_degrades_to_empty(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_class_snapshot_history.side_effect = RuntimeError("boom")
        mock_persistence.query_node_uprising_events.return_value = []
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_class_history(uuid.uuid4(), "C004")

        assert result["history"] == []

    def test_rupture_query_failure_degrades_to_empty(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_class_snapshot_history.return_value = []
        mock_persistence.query_node_uprising_events.side_effect = RuntimeError("boom")
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_class_history(uuid.uuid4(), "C004")

        assert result["ruptures"] == []


@pytest.mark.unit
class TestGetEdgeHistory:
    """Audit Wave 4 straggler (task #76): the edge-weight history sparkline
    — mirrors ``TestGetClassHistory``/``get_org_history``. ``edge_id`` uses
    the same ``"{source}->{target}"`` scheme ``get_inspector_edge`` set."""

    def test_returns_empty_when_persistence_lacks_query_method(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_edge_snapshot_history = None  # simulate SQLite RuntimeDatabase
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_edge_history(uuid.uuid4(), "C001->C004")

        assert result == {"edge_id": "C001->C004", "history": []}

    def test_malformed_edge_id_without_arrow_is_honest_empty(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_edge_history(uuid.uuid4(), "not-an-edge-id")

        assert result == {"edge_id": "not-an-edge-id", "history": []}
        mock_persistence.query_edge_snapshot_history.assert_not_called()

    def test_returns_history_rows_with_weight_from_value_flow(self) -> None:
        mock_persistence = _make_mock_persistence()
        sid = uuid.uuid4()
        mock_persistence.query_edge_snapshot_history.return_value = [
            {
                "tick": 0,
                "edge_type": "solidarity",
                "edge_mode": None,
                "value_flow": 1.5,
                "solidarity": 0.4,
                "tension": 0.1,
                "attributes": {},
            },
            {
                "tick": 1,
                "edge_type": "solidarity",
                "edge_mode": None,
                "value_flow": 2.0,
                "solidarity": 0.6,
                "tension": 0.2,
                "attributes": {},
            },
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_edge_history(sid, "C001->C004")

        assert result["edge_id"] == "C001->C004"
        assert result["history"] == [
            {"tick": 0, "weight": 1.5, "solidarity": 0.4, "tension": 0.1},
            {"tick": 1, "weight": 2.0, "solidarity": 0.6, "tension": 0.2},
        ]
        mock_persistence.query_edge_snapshot_history.assert_called_once_with(sid, "C001", "C004")

    def test_null_value_flow_is_an_honest_null_weight_not_zero(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_edge_snapshot_history.return_value = [
            {
                "tick": 0,
                "edge_type": "presence",
                "edge_mode": None,
                "value_flow": None,
                "solidarity": None,
                "tension": None,
                "attributes": {},
            }
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_edge_history(uuid.uuid4(), "ORG001->T001")

        assert result["history"] == [
            {"tick": 0, "weight": None, "solidarity": None, "tension": None}
        ]

    def test_decimal_value_flow_is_cast_to_float(self) -> None:
        """``value_flow`` is a Postgres NUMERIC column — psycopg returns
        Decimal; must be cast so JSON serialization doesn't choke."""
        from decimal import Decimal

        mock_persistence = _make_mock_persistence()
        mock_persistence.query_edge_snapshot_history.return_value = [
            {
                "tick": 0,
                "edge_type": "tribute",
                "edge_mode": None,
                "value_flow": Decimal("3.25"),
                "solidarity": None,
                "tension": 0.0,
                "attributes": {},
            }
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_edge_history(uuid.uuid4(), "C001->C002")

        weight = result["history"][0]["weight"]
        assert isinstance(weight, float)
        assert weight == pytest.approx(3.25)

    def test_history_query_failure_degrades_to_empty(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_edge_snapshot_history.side_effect = RuntimeError("boom")
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_edge_history(uuid.uuid4(), "C001->C004")

        assert result["history"] == []


# ---------------------------------------------------------------------- #
# Program 19/20 (Wave 3 Round 1, Backend-W3R1): get_field_state serializes
# the System-19/20 contradiction-field stack — honest omission (III.11) +
# deterministic sort (III.7).
# ---------------------------------------------------------------------- #

_FIELD_STATE_SESSION = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _graph_with_field_stack() -> BabylonGraph:
    """A real BabylonGraph carrying the Systems #19/#20 field stack.

    A real graph (not a MagicMock) is used because ``_tenancy_members_by_territory``
    reads ``graph.edges`` via both iteration AND ``__getitem__`` while
    ``_build_field_state_edges`` calls it AND ``graph.edges(data=True)`` —
    ``BabylonGraph``'s real ``EdgesView`` satisfies every one of those; a
    hand-rolled mock would have to reimplement all three.
    """
    g = BabylonGraph()
    g.graph["tick"] = 9
    g.graph["principal_field"] = {
        "field_name": "exploitation",
        "max_abs_df_dt": 0.05,
        "changed": True,
    }
    g.graph["dialectical_regime"] = {
        "regime": "crisis",
        "opposition": "capital_labor",
        "rate": 0.12,
    }
    # C002 is added before C001 — the serializer must sort by id regardless
    # of insertion/iteration order.
    g.add_node(
        "C002",
        "social_class",
        name="Suburban Petit-Bourgeois",
        contradiction_fields={"exploitation": 0.6, "atomization": 0.2},
        field_derivatives={
            "exploitation": {"laplacian": 0.1, "df_dt": 0.02, "d2f_dt2": 0.001},
            "atomization": {"laplacian": 0.0, "df_dt": None, "d2f_dt2": None},
        },
        fascist_alignment=0.4,
    )
    g.add_node(
        "C001",
        "social_class",
        name="Detroit Proletariat",
        contradiction_fields={"exploitation": 0.8, "atomization": 0.2},
        fascist_alignment=0.0,
    )
    # C003 carries NONE of the field-stack attrs — must be omitted entirely.
    g.add_node("C003", "social_class", name="Wayne County Bourgeoisie")
    # T001 is a territory — never eligible as a field-state node regardless
    # of any stray attrs.
    g.add_node("T001", "territory", name="Downtown Detroit")
    g.add_edge("C001", "T001", "TENANCY")
    g.add_edge("C002", "T001", "TENANCY")
    g.add_edge(
        "C001",
        "C002",
        "EXPLOITATION",
        field_gradients={"exploitation": -0.2, "atomization": 0.0},
    )
    return g


def _field_state_bridge() -> EngineBridge:
    mock_persistence = MagicMock()
    mock_persistence.hydrate_graph.return_value = _graph_with_field_stack()
    return EngineBridge(mock_persistence)


def _build_live_field_stack_graph() -> BabylonGraph:
    """A raw engine-shaped graph carrying the field stack PLUS ``role`` on
    every social_class node (unlike :func:`_graph_with_field_stack`, which
    the bridge reads RAW and never round-trips through ``WorldState``, so
    it never needed a required ``SocialClass.role``). Also stamps the
    ``field_stack`` graph attr via the production builder, so this fixture
    is exactly what ``FieldDerivativeSystem.step()`` would leave on a real
    engine graph at the end of a tick.
    """
    from babylon.engine.systems.field_derivative import _build_field_stack
    from babylon.models.enums import EdgeType, SocialRole

    g = BabylonGraph()
    g.graph["tick"] = 9
    g.graph["principal_field"] = {
        "field_name": "exploitation",
        "max_abs_df_dt": 0.05,
        "changed": True,
    }
    g.graph["dialectical_regime"] = {
        "regime": "crisis",
        "opposition": "capital_labor",
        "rate": 0.12,
    }
    g.add_node(
        "C002",
        "social_class",
        name="Suburban Petit-Bourgeois",
        role=SocialRole.LABOR_ARISTOCRACY.value,
        contradiction_fields={"exploitation": 0.6, "atomization": 0.2},
        field_derivatives={
            "exploitation": {"laplacian": 0.1, "df_dt": 0.02, "d2f_dt2": 0.001},
            "atomization": {"laplacian": 0.0, "df_dt": None, "d2f_dt2": None},
        },
        fascist_alignment=0.4,
    )
    g.add_node(
        "C001",
        "social_class",
        name="Detroit Proletariat",
        role=SocialRole.INTERNAL_PROLETARIAT.value,
        contradiction_fields={"exploitation": 0.8, "atomization": 0.2},
        fascist_alignment=0.0,
    )
    g.add_node(
        "C003",
        "social_class",
        name="Wayne County Bourgeoisie",
        role=SocialRole.CORE_BOURGEOISIE.value,
    )
    g.add_edge(
        "C001",
        "C002",
        EdgeType.EXPLOITATION.value,
        field_gradients={"exploitation": -0.2, "atomization": 0.0},
    )
    g.graph["field_stack"] = _build_field_stack(g)
    return g


@pytest.mark.unit
class TestGetFieldState:
    def test_nodes_honest_omission_of_absent_keys(self) -> None:
        bridge = _field_state_bridge()

        result = bridge.get_field_state(_FIELD_STATE_SESSION)

        by_id = {n["id"]: n for n in result["nodes"]}
        # C003 carries none of the 4 attrs -> omitted entirely (III.11).
        assert "C003" not in by_id

        # C001 has fields + fascist_alignment but no field_derivatives -> no
        # laplacian/df_dt keys at all (never a fabricated {} or 0.0).
        c001 = by_id["C001"]
        assert set(c001.keys()) == {"id", "name", "fields", "fascist_alignment"}
        assert "laplacian" not in c001
        assert "df_dt" not in c001

        # C002 has all 4; atomization's df_dt=None is honestly omitted from
        # the df_dt dict (only exploitation's real df_dt surfaces).
        c002 = by_id["C002"]
        assert c002["fields"] == {"exploitation": 0.6, "atomization": 0.2}
        assert c002["laplacian"] == {"exploitation": 0.1, "atomization": 0.0}
        assert c002["df_dt"] == {"exploitation": 0.02}
        assert c002["fascist_alignment"] == 0.4

    def test_nodes_sorted_deterministically_by_id(self) -> None:
        bridge = _field_state_bridge()

        result = bridge.get_field_state(_FIELD_STATE_SESSION)

        ids = [n["id"] for n in result["nodes"]]
        assert ids == ["C001", "C002"]

    def test_edges_territory_anchored_and_sorted(self) -> None:
        bridge = _field_state_bridge()

        result = bridge.get_field_state(_FIELD_STATE_SESSION)

        edges = result["edges"]
        assert [e["field"] for e in edges] == ["atomization", "exploitation"]
        for e in edges:
            assert e["source"] == "C001"
            assert e["target"] == "C002"
            assert e["source_territory"] == "T001"
            assert e["target_territory"] == "T001"
        atomization_edge = next(e for e in edges if e["field"] == "atomization")
        assert atomization_edge["gradient"] == 0.0
        exploitation_edge = next(e for e in edges if e["field"] == "exploitation")
        assert exploitation_edge["gradient"] == -0.2

    def test_edges_unresolvable_territory_is_null_not_omitted(self) -> None:
        g = BabylonGraph()
        g.graph["tick"] = 1
        g.add_node("C001", "social_class", name="A", contradiction_fields={"exploitation": 0.5})
        g.add_node("C002", "social_class", name="B", contradiction_fields={"exploitation": 0.1})
        g.add_edge("C001", "C002", "EXPLOITATION", field_gradients={"exploitation": -0.4})
        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = g
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_field_state(_FIELD_STATE_SESSION)

        assert len(result["edges"]) == 1
        edge = result["edges"][0]
        # Keep-key-use-null: the territory keys are PRESENT but None, matching
        # _serialize_territory's existing dominant_class/solidarity_index/
        # agitation convention for an unresolvable per-territory aggregate.
        assert "source_territory" in edge
        assert edge["source_territory"] is None
        assert "target_territory" in edge
        assert edge["target_territory"] is None

    def test_principal_field_extracts_field_name_from_graph_attr_dict(self) -> None:
        bridge = _field_state_bridge()

        result = bridge.get_field_state(_FIELD_STATE_SESSION)

        assert result["principal_field"] == "exploitation"

    def test_principal_field_and_regime_null_when_graph_attrs_absent(self) -> None:
        g = BabylonGraph()
        g.graph["tick"] = 3
        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = g
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_field_state(_FIELD_STATE_SESSION)

        assert result["principal_field"] is None
        assert result["dialectical_regime"] is None
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["tick"] == 3

    def test_dialectical_regime_passthrough(self) -> None:
        bridge = _field_state_bridge()

        result = bridge.get_field_state(_FIELD_STATE_SESSION)

        assert result["dialectical_regime"] == {
            "regime": "crisis",
            "opposition": "capital_labor",
            "rate": 0.12,
        }

    def test_tick_read_from_graph_attrs(self) -> None:
        bridge = _field_state_bridge()

        result = bridge.get_field_state(_FIELD_STATE_SESSION)

        assert result["tick"] == 9

    def test_populated_after_world_state_round_trip(self) -> None:
        """Program 19/20 Wave 3 Round 1 facade fix: the field stack survives
        a WorldState.from_graph(...).to_graph() round trip — the same
        round trip ``resolve_tick`` performs every real tick — and
        ``get_field_state`` on the ROUND-TRIPPED graph is populated exactly
        like the class docstring's "Known altitude gap" described as
        BROKEN before this carry landed. This test does not modify the
        bridge: it proves the bridge already lights up once WorldState
        carries the field stack.
        """
        from babylon.models.world_state import WorldState

        live_graph = _build_live_field_stack_graph()

        state = WorldState.from_graph(live_graph, tick=9)
        roundtripped = state.to_graph()

        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = roundtripped
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_field_state(_FIELD_STATE_SESSION)

        by_id = {n["id"]: n for n in result["nodes"]}
        # C003 never carried contradiction_fields/field_derivatives, so it
        # honestly has no 'fields'/'laplacian'/'df_dt' keys — but unlike the
        # raw-graph fixtures, a WorldState round trip stamps EVERY entity
        # with fascist_alignment (a real, always-defaulted SocialClass
        # field, per the registry's fascist_alignment row), so C003 DOES
        # appear (fascist_alignment=0.0 is a real value, not a fabrication)
        # while staying free of the three attrs that never survived before
        # this carry.
        assert by_id["C003"].keys() == {"id", "name", "fascist_alignment"}
        assert "fields" not in by_id["C003"]
        assert "laplacian" not in by_id["C003"]
        assert "df_dt" not in by_id["C003"]
        assert by_id["C001"]["fields"] == {"exploitation": 0.8, "atomization": 0.2}
        assert by_id["C002"]["laplacian"] == {"exploitation": 0.1, "atomization": 0.0}
        assert by_id["C002"]["df_dt"] == {"exploitation": 0.02}

        edge_fields = {e["field"] for e in result["edges"]}
        assert edge_fields == {"exploitation", "atomization"}

        assert result["principal_field"] == "exploitation"
        assert result["dialectical_regime"] == {
            "regime": "crisis",
            "opposition": "capital_labor",
            "rate": 0.12,
        }


@pytest.mark.unit
class TestGetFieldStateStubParity:
    """The hypergraph/communities cautionary tale (``GET .../hypergraph/
    communities/`` calls a bridge method neither bridge implements ->
    guaranteed 500) must not repeat here — StubEngineBridge needs its own
    honest-empty-but-well-formed ``get_field_state``."""

    def test_stub_returns_well_formed_empty_payload(self) -> None:
        from game.stub_bridge import StubEngineBridge

        stub = StubEngineBridge()

        result = stub.get_field_state(_FIELD_STATE_SESSION)

        assert result["tick"] == 0
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["principal_field"] is None
        assert result["dialectical_regime"] is None


@pytest.mark.unit
@pytest.mark.django_db
class TestGetFieldStateAPIView:
    """GET /api/games/{id}/field_state/ returns the standard envelope
    (mirrors get_contradiction_snapshot's view wiring)."""

    def test_view_returns_envelope(self) -> None:
        from django.contrib.auth.models import User
        from django.test import Client
        from django.urls import reverse

        import game.api
        from game.models import GameSession

        user = User.objects.create_user(  # type: ignore[no-untyped-call]
            username="fieldstateuser", password="fieldstatepass123"
        )
        client = Client()
        client.login(username="fieldstateuser", password="fieldstatepass123")
        session = GameSession.objects.create(
            id=uuid.UUID("bbbbbbbb-cccc-dddd-eeee-ffffffffffff"),
            player_id=user.id,
            scenario="wayne_county",
            current_tick=4,
            status="active",
        )
        mock_persistence = _make_mock_persistence()
        mock_persistence.hydrate_graph.return_value = _graph_with_field_stack()
        game.api._bridge_instance = EngineBridge(mock_persistence)

        url = reverse("game:game-field-state", kwargs={"game_id": str(session.id)})
        response = client.get(url)

        assert response.status_code == 200
        body = json.loads(response.content)
        assert body["status"] == "ok"
        assert body["session_id"] == str(session.id)
        data = body["data"]
        assert set(data.keys()) == {
            "tick",
            "nodes",
            "edges",
            "principal_field",
            "dialectical_regime",
        }
        assert data["principal_field"] == "exploitation"

    def test_view_404s_on_unknown_game(self) -> None:
        from django.contrib.auth.models import User
        from django.test import Client
        from django.urls import reverse

        import game.api

        User.objects.create_user(  # type: ignore[no-untyped-call]
            username="fieldstateghost", password="fieldstatepass123"
        )
        client = Client()
        client.login(username="fieldstateghost", password="fieldstatepass123")
        game.api._bridge_instance = MagicMock()

        url = reverse("game:game-field-state", kwargs={"game_id": str(uuid.uuid4())})
        response = client.get(url)

        assert response.status_code == 404


# ---------------------------------------------------------------------- #
# Program 17 Wave 1 W3R2 (Backend-W3R2aFix): UPRISING events anchor to a
# territory so the storm-marker map layer (stormMarkers.ts) can place
# them. ``_serialize_event`` resolves ``data.node_id`` (a social_class id)
# -> territory via the same ``_class_to_territory(_tenancy_members_by_
# territory(graph))`` inversion ``_build_field_state_edges`` already uses
# to territory-anchor social_class nodes (see ``_graph_with_field_stack``
# above). Constitution III.11: unresolvable is a real ``None``, never a
# guessed territory.
# ---------------------------------------------------------------------- #


def _graph_with_tenancy(*, class_to_territory: dict[str, str | None]) -> BabylonGraph:
    """A real BabylonGraph (not a MagicMock — see ``_graph_with_field_stack``'s
    docstring for why) with social_class nodes TENANCY-linked to territories
    per ``class_to_territory``. A ``None`` value adds the social_class node
    with NO TENANCY edge at all (an unresolvable class)."""
    g = BabylonGraph()
    g.graph["tick"] = 1
    seen_territories: set[str] = set()
    for class_id, territory_id in class_to_territory.items():
        g.add_node(class_id, "social_class", name=class_id)
        if territory_id is None:
            continue
        if territory_id not in seen_territories:
            g.add_node(territory_id, "territory", name=territory_id)
            seen_territories.add(territory_id)
        g.add_edge(class_id, territory_id, "TENANCY")
    return g


def _uprising_event(node_id: str, tick: int = 5) -> MagicMock:
    event = MagicMock()
    event.event_type = "uprising"
    event.tick = tick
    event.data = {"node_id": node_id, "trigger": "revolutionary_pressure"}
    event.narrative = None
    return event


@pytest.mark.unit
class TestSerializeEventUprisingTerritoryAnchoring:
    """Backend-W3R2aFix: territory_id enrichment for UPRISING events."""

    def test_uprising_gets_territory_id_when_class_has_tenancy_edge(self) -> None:
        from game.engine_bridge import _serialize_event

        graph = _graph_with_tenancy(class_to_territory={"C001": "T001"})
        event = _uprising_event("C001")

        result = _serialize_event(event, uuid.uuid4(), graph=graph)

        assert result["data"]["territory_id"] == "T001"

    def test_uprising_gets_null_territory_id_when_class_has_no_tenancy(self) -> None:
        from game.engine_bridge import _serialize_event

        graph = _graph_with_tenancy(class_to_territory={"C001": "T001", "C999": None})
        event = _uprising_event("C999")  # not TENANCY-linked to any territory

        result = _serialize_event(event, uuid.uuid4(), graph=graph)

        assert "territory_id" in result["data"]
        assert result["data"]["territory_id"] is None

    def test_uprising_gets_null_territory_id_when_graph_absent(self) -> None:
        from game.engine_bridge import _serialize_event

        event = _uprising_event("C001")

        result = _serialize_event(event, uuid.uuid4())

        assert result["data"]["territory_id"] is None

    def test_non_uprising_event_untouched(self) -> None:
        from game.engine_bridge import _serialize_event

        graph = _graph_with_tenancy(class_to_territory={"C001": "T001"})
        event = MagicMock()
        event.event_type = "wage_payment"
        event.tick = 5
        event.data = {"node_id": "C001", "amount": 10.0}
        event.narrative = None

        result = _serialize_event(event, uuid.uuid4(), graph=graph)

        assert "territory_id" not in result["data"]
        assert result["data"] == {"node_id": "C001", "amount": 10.0}

    def test_deterministic_across_repeated_calls(self) -> None:
        """Two classes in one territory + one class with zero TENANCY edges —
        repeated serialization off the same graph must resolve identically
        (Constitution III.7)."""
        from game.engine_bridge import _serialize_event

        graph = _graph_with_tenancy(
            class_to_territory={"C001": "T001", "C002": "T001", "C003": None}
        )
        session_id = uuid.uuid4()

        def _resolve(node_id: str) -> Any:
            return _serialize_event(_uprising_event(node_id), session_id, graph=graph)["data"][
                "territory_id"
            ]

        first = {node_id: _resolve(node_id) for node_id in ("C001", "C002", "C003")}
        second = {node_id: _resolve(node_id) for node_id in ("C001", "C002", "C003")}

        assert first == second == {"C001": "T001", "C002": "T001", "C003": None}

    def test_state_to_snapshot_threads_graph_into_uprising_events(self) -> None:
        """The bridge-wide enrichment point: ``_state_to_snapshot`` (called
        from ``resolve_tick``, the inspectors, and ``get_snapshot``) passes
        its ``graph`` argument through to ``_serialize_event`` so every
        downstream consumer of ``snapshot["events"]`` (toasts, and via
        ``_persist_tick_events_safe`` -> tick_event -> journal/ruptures)
        sees the same territory_id."""
        graph = _graph_with_tenancy(class_to_territory={"C001": "T001"})
        mock_state = MagicMock()
        mock_state.tick = 5
        mock_state.territories = {}
        mock_state.organizations = {}
        mock_state.institutions = {}
        mock_state.relationships = []
        mock_state.economy = None
        mock_state.events = [_uprising_event("C001")]

        snapshot = _state_to_snapshot(mock_state, uuid.uuid4(), graph=graph)

        assert snapshot["events"][0]["data"]["territory_id"] == "T001"


# ══════════════════════════════════════════════════════════════════════
# Backend-W3R3 (Program 17 Wave 3): GET /api/games/{id}/map/history/.
# Verified against a running canonical session (2026-07-15, tick 987):
# only heat/population (territory_snapshot) and profit_rate/
# exploitation_rate (view_runtime_trace_emission) have a genuine
# append-only per-tick historical source; the other 9 MAP_METRIC_PROPERTIES
# exist only in hex_latest (current-tick-only cache) and are rejected here
# with an honest "not_replayable" result rather than served as fabricated
# null frames (Constitution III.11).
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestGetMapHistory:
    """get_map_history: the map lens scrubber's real data source."""

    def test_unknown_metric_is_a_loud_error(self) -> None:
        bridge = EngineBridge(_make_mock_persistence())

        result = bridge.get_map_history(uuid.uuid4(), metric="not_a_real_metric")

        assert result["error"] == "unknown_metric"
        assert "not_a_real_metric" in result["message"]
        assert result["frames"] == []

    def test_non_replayable_metric_is_an_honest_error(self) -> None:
        """occ/imperial_rent/habitability/... exist only in hex_latest (live-only)."""
        bridge = EngineBridge(_make_mock_persistence())

        result = bridge.get_map_history(uuid.uuid4(), metric="occ")

        assert result["error"] == "not_replayable"
        assert "occ" in result["message"]
        # The error names what IS replayable, not just what isn't.
        assert "heat" in result["message"]
        assert "profit_rate" in result["message"]
        assert result["frames"] == []

    def test_degrades_to_honest_empty_when_persistence_lacks_query_methods(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_territory_snapshot_latest_tick = None
        mock_persistence.query_territory_snapshot_metric_frames = None
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="heat")

        assert result == {
            "metric": "heat",
            "from_tick": 0,
            "to_tick": 0,
            "capped": False,
            "frames": [],
        }

    def test_frames_sorted_by_tick_and_values_keyed_by_county(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_territory_snapshot_latest_tick.return_value = 1
        mock_persistence.query_territory_snapshot_metric_frames.return_value = [
            {"tick": 1, "county_fips": "26163", "heat": 0.2, "pop_total": 8000},
            {"tick": 0, "county_fips": "26163", "heat": 0.1, "pop_total": 8000},
            {"tick": 0, "county_fips": "26099", "heat": 0.05, "pop_total": 4000},
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="heat")

        assert result["metric"] == "heat"
        assert [f["tick"] for f in result["frames"]] == [0, 1]
        assert result["frames"][0]["values"] == {"26099": 0.05, "26163": 0.1}
        assert list(result["frames"][0]["values"].keys()) == ["26099", "26163"]
        assert result["frames"][1]["values"] == {"26163": 0.2}

    def test_population_metric_reads_pop_total_column(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_territory_snapshot_latest_tick.return_value = 0
        mock_persistence.query_territory_snapshot_metric_frames.return_value = [
            {"tick": 0, "county_fips": "26163", "heat": 0.1, "pop_total": 8000},
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="population")

        assert result["frames"][0]["values"] == {"26163": 8000.0}
        mock_persistence.query_territory_snapshot_metric_frames.assert_called_once()

    def test_county_trace_metric_reads_profit_rate_column(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_county_trace_latest_tick.return_value = 987
        mock_persistence.query_county_trace_metric_frames.return_value = [
            {
                "tick": 987,
                "county_fips": "26163",
                "profit_rate": 0.5398,
                "exploitation_rate": 1.3033,
            }
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="profit_rate")

        assert result["frames"][0]["values"] == {"26163": pytest.approx(0.5398)}
        # profit_rate must never read the sibling exploitation_rate column.
        mock_persistence.query_county_trace_metric_frames.assert_called_once()

    def test_null_value_in_a_frame_stays_null_not_fabricated(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_county_trace_latest_tick.return_value = 0
        mock_persistence.query_county_trace_metric_frames.return_value = [
            {"tick": 0, "county_fips": "26163", "profit_rate": None, "exploitation_rate": None},
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="profit_rate")

        assert result["frames"][0]["values"] == {"26163": None}

    def test_explicit_range_within_cap_is_not_capped(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_territory_snapshot_metric_frames.return_value = []
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="heat", from_tick=10, to_tick=20)

        assert result["capped"] is False
        assert result["from_tick"] == 10
        assert result["to_tick"] == 20
        mock_persistence.query_territory_snapshot_metric_frames.assert_called_once_with(
            mock_persistence.query_territory_snapshot_metric_frames.call_args[0][0], 10, 20
        )
        # Explicit range never triggers the "latest tick" lookup.
        mock_persistence.query_territory_snapshot_latest_tick.assert_not_called()

    def test_explicit_range_beyond_cap_is_honestly_clamped(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_territory_snapshot_metric_frames.return_value = []
        bridge = EngineBridge(mock_persistence)
        to_tick = _MAP_HISTORY_WINDOW_CAP + 50

        result = bridge.get_map_history(uuid.uuid4(), metric="heat", from_tick=0, to_tick=to_tick)

        assert result["capped"] is True
        assert result["to_tick"] == to_tick
        assert result["from_tick"] == to_tick - _MAP_HISTORY_WINDOW_CAP + 1
        span = result["to_tick"] - result["from_tick"] + 1
        assert span == _MAP_HISTORY_WINDOW_CAP

    def test_default_window_ends_at_latest_committed_tick(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_territory_snapshot_latest_tick.return_value = 5
        mock_persistence.query_territory_snapshot_metric_frames.return_value = []
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="heat")

        assert result["to_tick"] == 5
        assert result["from_tick"] == 0
        assert result["capped"] is False

    def test_default_window_beyond_cap_is_capped_even_with_no_explicit_range(self) -> None:
        mock_persistence = _make_mock_persistence()
        latest = _MAP_HISTORY_WINDOW_CAP + 100
        mock_persistence.query_territory_snapshot_latest_tick.return_value = latest
        mock_persistence.query_territory_snapshot_metric_frames.return_value = []
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="heat")

        assert result["capped"] is True
        assert result["to_tick"] == latest
        assert result["from_tick"] == latest - _MAP_HISTORY_WINDOW_CAP + 1

    def test_no_committed_ticks_yet_is_honest_empty(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_territory_snapshot_latest_tick.return_value = None
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="heat")

        assert result["frames"] == []
        assert result["capped"] is False

    def test_query_failure_degrades_to_empty_not_a_crash(self) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_territory_snapshot_latest_tick.return_value = 0
        mock_persistence.query_territory_snapshot_metric_frames.side_effect = RuntimeError("boom")
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="heat")

        assert result["frames"] == []

    def test_stub_bridge_parity(self) -> None:
        """StubEngineBridge serves the same envelope shape — honest empty."""
        from game.stub_bridge import StubEngineBridge

        stub = StubEngineBridge()

        replayable = stub.get_map_history(uuid.uuid4(), metric="heat")
        assert replayable == {
            "metric": "heat",
            "from_tick": 0,
            "to_tick": 0,
            "capped": False,
            "frames": [],
        }

        not_replayable = stub.get_map_history(uuid.uuid4(), metric="occ")
        assert not_replayable["error"] == "not_replayable"

        unknown = stub.get_map_history(uuid.uuid4(), metric="not_a_real_metric")
        assert unknown["error"] == "unknown_metric"


@pytest.mark.unit
class TestPersistSnapshotsGraphWiring:
    """Task #70 (W3 R3 crown-finding fix): ``_persist_snapshots_safe`` must
    thread ``graph=`` into ``_serialize_territory`` so ``territory_snapshot``'s
    occ/imperial_rent/profit_rate/exploitation_rate columns stop persisting
    NULL forever — the live ``/map/`` path already passes the graph; history
    silently didn't (verified all-NULL by live SQL, R3 backend report)."""

    def test_graph_kwarg_populates_territory_rate_columns(self) -> None:
        """With ``graph=`` supplied, the ``tick_*`` year-boundary rates land
        in the persisted territory rows instead of ``None``."""
        from game.engine_bridge import _build_initial_state_for_scenario, _persist_snapshots_safe

        state = _build_initial_state_for_scenario("wayne_county")
        graph = state.to_graph()
        territory_id = next(iter(state.territories))
        graph.update_node(
            territory_id,
            tick_phi_hour=1.25,
            tick_profit_rate=0.027,
            tick_occ=138.6,
            tick_exploitation_rate=3.79,
        )
        mock_persistence = MagicMock()

        _persist_snapshots_safe(mock_persistence, uuid.uuid4(), state, graph=graph)

        _, kwargs = mock_persistence.persist_full_tick.call_args
        rows = kwargs["territories"]
        assert rows, "wayne_county's county-keyed territory must produce a snapshot row"
        row = rows[0]
        assert row["profit_rate"] == 0.027
        assert row["occ"] == 138.6
        assert row["exploitation_rate"] == 3.79
        assert row["imperial_rent"] == 1.25

    def test_graph_omitted_stays_honest_none(self) -> None:
        """Bootstrap call sites pass no graph — rates stay honest ``None``
        (tick-0 has no TickDynamics output), never a fabricated 0.0."""
        from game.engine_bridge import _build_initial_state_for_scenario, _persist_snapshots_safe

        state = _build_initial_state_for_scenario("wayne_county")
        mock_persistence = MagicMock()

        _persist_snapshots_safe(mock_persistence, uuid.uuid4(), state)

        _, kwargs = mock_persistence.persist_full_tick.call_args
        row = kwargs["territories"][0]
        assert row["profit_rate"] is None
        assert row["occ"] is None
