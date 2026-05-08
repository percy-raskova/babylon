"""Unit tests for the engine bridge (Phase 3).

Tests use mocks for RuntimePersistence and the step() function
to verify call ordering and output format without requiring
a real database or simulation engine.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import networkx as nx
import pytest

from game.engine_bridge import EngineBridge, _build_initial_state_for_scenario, _state_to_snapshot


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
    G: nx.DiGraph[str] = nx.DiGraph()
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

        result = bridge.create_game(scenario="detroit_1967", rng_seed=42)

        assert isinstance(result, uuid.UUID)
        assert result == uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    def test_create_game_passes_scenario(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        bridge.create_game(scenario="test_scenario")

        call_kwargs = mock_persistence.create_session.call_args
        assert call_kwargs.kwargs["scenario"] == "test_scenario"

    def test_create_game_passes_player_id(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        bridge.create_game(scenario="test", player_id=7)

        call_kwargs = mock_persistence.create_session.call_args
        assert call_kwargs.kwargs["player_id"] == 7

    def test_create_game_validates_config(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        # Valid config should pass
        bridge.create_game(scenario="test", config={"extraction_efficiency": 0.5})
        assert mock_persistence.create_session.called

    def test_create_game_serializes_defines(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        bridge.create_game(scenario="test", defines={})

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
        assert isinstance(persisted_graph, nx.DiGraph)
        assert len(persisted_graph.nodes) > 0


@pytest.mark.unit
class TestScenarioBootstrap:
    """Verify scenario bootstrap selection for initial game state."""

    def test_unknown_scenario_falls_back_to_default_state(self) -> None:
        state = _build_initial_state_for_scenario("not-a-real-scenario")

        assert state.tick == 0
        assert len(state.territories) > 0
        assert len(state.entities) > 0


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
        assert isinstance(graph, nx.DiGraph)

    def test_hydrate_bootstraps_when_graph_unseeded(self) -> None:
        mock_persistence = _make_mock_persistence()
        empty_graph: nx.DiGraph[str] = nx.DiGraph()
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
