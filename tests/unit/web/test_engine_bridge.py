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

import pytest

from babylon.models.entities.institution import InternalBalanceOfForces
from babylon.models.entities.social_class import IdeologicalProfile
from babylon.models.enums import ActionType, EventType
from babylon.models.events import SimulationEvent
from babylon.topology.graph import BabylonGraph
from game.engine_bridge import (
    _EVENT_SEVERITY,
    _MAP_HISTORY_WINDOW_CAP,
    VERB_TO_ACTION_TYPE,
    EngineBridge,
    _build_initial_state_for_scenario,
    _classify_event,
    _derive_intel_ledger,
    _heat_delta_by_territory,
    _hex_feature_properties,
    _hex_state_row,
    _investigate_field_snapshot,
    _mean_territory_attr,
    _org_count_by_territory,
    _query_investigate_action_results,
    _serialize_territory,
    _state_to_snapshot,
    resolve_scenario,
)
from game.verb_copy import VERB_INELIGIBILITY_COPY


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


def _make_minimal_graph() -> BabylonGraph:
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

        # The bridge batches the tick's action rows into one
        # persist_action_results call (task #43; pool present => Postgres path).
        assert mock_persistence.persist_action_results.called, (
            "persist_action_results should be called with the tick's action rows"
        )


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


@pytest.mark.unit
class TestPatternShiftSeverity:
    """Spec-116 Task 4: pattern_shift is a real EventType, classified warning."""

    def test_pattern_shift_is_a_string_literal_key(self) -> None:
        """``_EVENT_SEVERITY`` is ``dict[str, str]`` — every key (including
        this one) must be a plain string literal, never an EventType member,
        matching every existing entry in the map."""
        assert "pattern_shift" in _EVENT_SEVERITY
        assert all(isinstance(key, str) for key in _EVENT_SEVERITY)

    def test_pattern_shift_classified_as_warning(self) -> None:
        assert _classify_event("pattern_shift") == "warning"


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
        # Program 23 / ADR078: same graph-only-attr shape, honest None
        # without a graph.
        assert result["price_divergence"] is None
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

    def test_graph_supplies_negative_price_divergence_when_written(self) -> None:
        """Program 23 / ADR078: SIGNED — a negative reading (price below
        value) must survive, never coerced toward 0.0."""
        territory = self._make_territory()
        graph = BabylonGraph()
        graph.add_node("T001", node_type="territory", price_divergence=-0.37)

        result = _serialize_territory(territory, graph=graph)

        assert result["price_divergence"] == pytest.approx(-0.37)

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
class TestHexFeaturePropertiesVeilGate:
    """G4: the map lens's per-hex value-axis fields
    (profit_rate/exploitation_rate/occ/imperial_rent/price_divergence) gate
    on ``veil_tier`` exactly like every other endpoint in the sweep —
    ``get_map_snapshot``'s own real-tree wiring is covered indirectly via
    ``TestBalkanizationMapFields``; this pins the pure per-hex composer's
    gating contract directly (tier-0 sweep, acceptance criterion 1)."""

    @staticmethod
    def _row() -> Any:
        from types import SimpleNamespace

        return SimpleNamespace(
            h3_index="h1",
            county_fips="26163",
            county_name="Wayne",
            bea_ea_code=None,
            msa_code=None,
            profit_rate=0.15,
            exploitation_rate=0.30,
            occ=2.1,
            imperial_rent=0.05,
            heat=0.4,
            org_count=1,
            dominant_class=None,
            pop_total=5000,
            attributes={"price_divergence": 0.2},
        )

    def test_veil_tier_none_is_unfogged_byte_identical_to_before_g4(self) -> None:
        """The default (``veil_tier=None``, every pre-existing direct call
        site) stays real/ungated — G4 must not regress a single pre-G4 test."""
        props = _hex_feature_properties(self._row())
        assert props["profit_rate"] == pytest.approx(0.15)
        assert props["price_divergence"] == pytest.approx(0.2)

    def test_tier_zero_masks_every_value_axis_field(self) -> None:
        props = _hex_feature_properties(self._row(), veil_tier=0)
        assert props["profit_rate"] is None
        assert props["exploitation_rate"] is None
        assert props["occ"] is None
        assert props["imperial_rent"] is None
        assert props["price_divergence"] is None
        # Never touched — heat is money-form/political, not value-axis.
        assert props["heat"] == pytest.approx(0.4)

    def test_tier_one_unlocks_tier1_fields_but_not_the_scissors(self) -> None:
        props = _hex_feature_properties(self._row(), veil_tier=1)
        assert props["profit_rate"] == pytest.approx(0.15)
        assert props["exploitation_rate"] == pytest.approx(0.30)
        assert props["occ"] == pytest.approx(2.1)
        assert props["imperial_rent"] == pytest.approx(0.05)
        assert props["price_divergence"] is None

    def test_tier_two_unlocks_everything(self) -> None:
        props = _hex_feature_properties(self._row(), veil_tier=2)
        assert props["profit_rate"] == pytest.approx(0.15)
        assert props["price_divergence"] == pytest.approx(0.2)


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


def _stamp_unlocked_veil(graph: BabylonGraph, org_id: str = "org-player") -> None:
    """G4: stamp ``org_id`` as this graph's player org with BOTH veil
    threshold nodes acquired (Tier 2, fully unlocked) — for fixtures built
    before the Veil-of-Money program existed, whose tests are about real-
    data arithmetic, not veil gating, and should keep reading real numbers
    unchanged. See ``TestEconomyDashboardVeil``/``TestVeilGating`` for the
    dedicated tier-0/1/2 gating coverage."""
    graph.graph["player_org_id"] = org_id
    graph.nodes[org_id]["acquired_doctrine_ids"] = ("class_consciousness", "trade_unionism")


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
        id="org-player",
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
        # Real shape: agitation lives under ideology.agitation (nested, per
        # SocialClass.model_dump()) -- production never emits a flat
        # top-level "agitation" key. A flat stamp here would silently mask
        # the get_educate_targets/get_aid_targets bug it once did.
        ideology=IdeologicalProfile(agitation=0.62).model_dump(),
        # Deliberately NO territory_ids -- SocialClass has no such field in
        # production (only Organization/Institution do). The TENANCY edge
        # below is the real Occupant -> Territory link every verb-target
        # method resolves through now (Track 1 Task 8c renamed the old
        # organization-or-territory_ids helper to
        # `_territory_id_bearing_nodes` and scoped it to `organization`
        # nodes only -- a fabricated territory_ids here would be inert at
        # best and a task #45 vocabulary-sentinel violation at worst).
    )
    g.add_edge(
        "org-player",
        "sc-genesee-proles",
        "exploitation",
        edge_mode="extractive",
        value_flow=118.9,
        tension=0.34,
    )
    g.add_edge("sc-genesee-proles", "T1", "tenancy")

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
        _stamp_unlocked_veil(graph)

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
        _stamp_unlocked_veil(graph)

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

    def test_value_produced_includes_social_class_wealth_via_tenancy_not_territory_ids(
        self,
    ) -> None:
        """Track 1 Task 8c: ``SocialClass`` never carries a ``territory_ids``
        field in production (only ``Organization``/``Institution`` do) --
        it links to a territory via a real TENANCY edge instead. A
        territory with NO organization present but a social_class tenant
        purely via TENANCY (no fabricated ``territory_ids`` stamp,
        unlike the shared ``T1`` fixture) must still surface that class's
        wealth in ``value_produced`` -- proving the resolution goes through
        :func:`game.engine_bridge._tenancy_members_by_territory`, not the
        territory_ids field no social_class node actually has.
        """
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        _stamp_unlocked_veil(graph)
        graph.add_node(
            "T3",
            "territory",
            name="Oakland County",
            county_fips="26125",
            heat=0.1,
            population=3000,
        )
        graph.add_node(
            "sc-oakland-proles",
            "social_class",
            name="Oakland Proletariat",
            role="proletariat",
            wealth=555.5,
            ideology=IdeologicalProfile(agitation=0.1).model_dump(),
        )
        graph.add_edge("sc-oakland-proles", "T3", "tenancy")

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_economy(uuid.uuid4(), territory_id="T3")

        assert result["has_data"] is True
        assert result["value_produced"] == pytest.approx(555.5)


@pytest.mark.unit
class TestImperialRentGapByRegion:
    """spec-117 T2-6b: per-territory Fundamental Theorem reading.

    ``core_wages``/``wealth`` are population-scaled class-level totals (a
    class node IS its whole demographic block — ``ProductionSystem``:
    ``produced_value = effective_labor_power * population``), so their raw
    difference is NOT directly comparable across classes of different
    population. The per-capita normalization (``gap / population``) is the
    genuine intensive; ``ScaleAdjunction.aggregate_intensive`` population-
    share-weights it into the region's own total-gap-over-total-population.

    Adopted from the salvaged red-phase commit ``75b168f2`` (prior attempt
    died mid-red-phase) — verified correct against
    :meth:`ScaleAdjunction.aggregate_intensive`'s own math by hand before
    landing (see this task's report), then implemented fresh.
    """

    def _graph_with_two_tenants(self) -> BabylonGraph:
        g = BabylonGraph()
        g.graph["tick"] = 1
        g.add_node("T1", "territory", name="Genesee County", population=4000)
        g.add_node("T2", "territory", name="Washtenaw County", population=2000)
        # T1 tenant A: population 1000, wealth 500 (Vc/capita=0.5),
        # core_wages 800 (Wc/capita=0.8) -> gap/capita = +0.3.
        g.add_node("class-a", "social_class", name="A", role="proletariat", wealth=500.0)
        g.add_edge("class-a", "T1", "tenancy")
        g.add_edge("employer-a", "class-a", "wages", value_flow=800.0)
        g.nodes["class-a"]["population"] = 1000
        # T1 tenant B: population 3000, wealth 4500 (Vc/capita=1.5),
        # core_wages 1200 (Wc/capita=0.4) -> gap/capita = -1.1.
        g.add_node("class-b", "social_class", name="B", role="core_bourgeoisie", wealth=4500.0)
        g.add_edge("class-b", "T1", "tenancy")
        g.add_edge("employer-b", "class-b", "wages", value_flow=1200.0)
        g.nodes["class-b"]["population"] = 3000
        # T2 tenant C: population 2000, wealth 1000, core_wages 1000 ->
        # both per-capita 0.5, gap/capita = 0.0.
        g.add_node("class-c", "social_class", name="C", role="proletariat", wealth=1000.0)
        g.add_edge("class-c", "T2", "tenancy")
        g.add_edge("employer-c", "class-c", "wages", value_flow=1000.0)
        g.nodes["class-c"]["population"] = 2000
        return g

    def test_region_gap_is_population_weighted_mean_per_capita(self) -> None:
        from game.engine_bridge import _imperial_rent_gap_by_region

        graph = self._graph_with_two_tenants()
        rows = _imperial_rent_gap_by_region(graph)
        by_id = {r["territory_id"]: r for r in rows}

        # T1: (800+1200)/4000 Wc, (500+4500)/4000 Vc, gap = -3000/4000.
        assert by_id["T1"]["wc_per_capita"] == pytest.approx(0.5)
        assert by_id["T1"]["vc_per_capita"] == pytest.approx(1.25)
        assert by_id["T1"]["gap_per_capita"] == pytest.approx(-0.75)
        assert by_id["T1"]["population"] == pytest.approx(4000)

        # T2: single tenant, both per-capita 0.5 -> gap 0.
        assert by_id["T2"]["wc_per_capita"] == pytest.approx(0.5)
        assert by_id["T2"]["vc_per_capita"] == pytest.approx(0.5)
        assert by_id["T2"]["gap_per_capita"] == pytest.approx(0.0)

    def test_territory_with_only_zero_population_tenant_is_absent(self) -> None:
        from game.engine_bridge import _imperial_rent_gap_by_region

        graph = self._graph_with_two_tenants()
        graph.add_node("T3", "territory", name="Oakland County", population=0)
        graph.add_node("class-d", "social_class", name="D", role="proletariat", wealth=10.0)
        graph.add_edge("class-d", "T3", "tenancy")
        graph.nodes["class-d"]["population"] = 0

        rows = _imperial_rent_gap_by_region(graph)

        assert "T3" not in {r["territory_id"] for r in rows}

    def test_class_with_no_tenancy_edge_creates_no_phantom_region(self) -> None:
        from game.engine_bridge import _imperial_rent_gap_by_region

        graph = self._graph_with_two_tenants()
        graph.add_node("class-floating", "social_class", name="Floating", wealth=999.0)
        graph.nodes["class-floating"]["population"] = 500

        rows = _imperial_rent_gap_by_region(graph)

        assert {r["territory_id"] for r in rows} == {"T1", "T2"}

    def test_empty_graph_returns_empty_list(self) -> None:
        from game.engine_bridge import _imperial_rent_gap_by_region

        assert _imperial_rent_gap_by_region(BabylonGraph()) == []


@pytest.mark.unit
class TestEconomyDashboardFundamentalTheorem:
    """T2-6a/b (spec-117): get_economy_dashboard's graph-wide Wc/Vc gap
    (promoted from the per-class ``imperial_rent_gap`` already computed for
    the inspector popup — same ``core_wages - wealth`` sign convention, just
    summed graph-wide instead of read per-class) and the net-new per-region
    breakdown (:func:`_imperial_rent_gap_by_region`)."""

    def _dashboard_result(self, graph: BabylonGraph) -> dict[str, Any]:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        mock_state = MagicMock()
        mock_state.tick = 10
        # get_economy_dashboard reads state.economy.imperial_rent_pool /
        # .current_super_wage_rate -- a bare MagicMock() isn't a real number
        # and float(MagicMock()) raises, so this pins the "no economy state"
        # honest-None branch explicitly rather than exercising a MagicMock
        # by accident.
        mock_state.economy = None
        # G4: this class is about the imperial_rent_gap ARITHMETIC, not veil
        # gating (that's TestEconomyDashboardVeil's job) -- a real, fully-
        # unlocked player org keeps every assertion below reading real
        # numbers, matching this fixture's pre-veil-program intent.
        mock_state.organizations = {
            "org-player": MagicMock(acquired_doctrine_ids=("class_consciousness", "trade_unionism"))
        }
        mock_state.player_org_id = "org-player"
        with patch.object(bridge, "hydrate_state", return_value=(mock_state, graph)):
            return bridge.get_economy_dashboard(uuid.uuid4())

    def test_imperial_rent_gap_is_wage_flow_minus_value_produced(self) -> None:
        graph = _make_balkanization_graph()

        result = self._dashboard_result(graph)

        # _make_balkanization_graph seeds no WAGES edges -> wage_flow_total
        # is honestly 0.0; value_produced is sc-genesee-proles' wealth
        # (812.4, the graph's only social_class node).
        assert result["wage_flow_total"] == pytest.approx(0.0)
        assert result["value_produced"] == pytest.approx(812.4)
        assert result["imperial_rent_gap"] == pytest.approx(-812.4)

    def test_imperial_rent_gap_by_region_absent_without_population(self) -> None:
        graph = _make_balkanization_graph()

        result = self._dashboard_result(graph)

        # sc-genesee-proles is TENANCY-linked to T1 but carries no
        # `population` field of its own (only Territory nodes do in this
        # fixture) -> excluded, so the region list is honestly empty rather
        # than fabricating a per-capita reading with a phantom population.
        assert result["imperial_rent_gap_by_region"] == []

    def test_imperial_rent_gap_by_region_reflects_positive_population_tenant(self) -> None:
        graph = _make_balkanization_graph()
        graph.nodes["sc-genesee-proles"]["population"] = 5000
        graph.add_edge("employer-genesee", "sc-genesee-proles", "wages", value_flow=1000.0)

        result = self._dashboard_result(graph)

        rows = result["imperial_rent_gap_by_region"]
        assert len(rows) == 1
        assert rows[0]["territory_id"] == "T1"
        assert rows[0]["population"] == pytest.approx(5000)
        assert rows[0]["wc_per_capita"] == pytest.approx(round(1000.0 / 5000, 4))
        assert rows[0]["vc_per_capita"] == pytest.approx(round(812.4 / 5000, 4))
        assert rows[0]["gap_per_capita"] == pytest.approx(round(1000.0 / 5000 - 812.4 / 5000, 4))


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
            ideology=IdeologicalProfile(agitation=0.2).model_dump(),
            # No territory_ids -- SocialClass has no such field in production;
            # the TENANCY edge below is the real link (see the comment on
            # sc-genesee-proles in _make_balkanization_graph above).
        )
        graph.add_edge("sc-washtenaw-proles", "T2", "tenancy")

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

    def test_aid_targets_agitation_level_reads_real_ideology_agitation(self) -> None:
        """Track 1 audit (task #45): ``get_aid_targets`` read a flat
        top-level ``agitation`` key off social_class node data, but
        ``SocialClass.model_dump()`` (what ``WorldState.to_graph()`` stamps)
        nests it under ``ideology.agitation`` -- no production graph ever
        carries a flat ``agitation`` key, so every real game's
        ``agitation_level`` was silently ``0.0``. This had NO prior test
        coverage at all (unlike ``get_educate_targets``'s ``avg_agitation``,
        which a fixture that mirrored the same flat shape had masked).
        """
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_aid_targets(uuid.uuid4(), "org-player")

        target = next(
            t for t in result["population_targets"] if t["community_id"] == "sc-genesee-proles"
        )
        assert target["material_conditions"]["agitation_level"] == pytest.approx(0.62)

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

    def test_reproduce_targets_base_population_from_tenancy_not_territory_ids(
        self,
    ) -> None:
        """Track 1 Task 8c: ``base_population`` filtered
        ``_node_type == "social_class"`` over a helper (``_nodes_in_territory``)
        that resolves via the ``territory_ids`` field -- a field
        ``SocialClass`` never carries in production (only
        ``Organization``/``Institution`` do). Structurally always 0 against
        real data. A social_class tenant (real TENANCY edge, no fabricated
        ``territory_ids``) to one of the org's own territories must
        contribute its population.
        """
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.add_node(
            "sc-real-tenancy",
            "social_class",
            name="Detroit Proletariat",
            role="proletariat",
            wealth=0.0,
            population=250_000,
        )
        graph.add_edge("sc-real-tenancy", "T1", "tenancy")

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_reproduce_targets(uuid.uuid4(), "org-player")

        base_population = result["targets"][0]["modes"]["mass_recruitment"]["recruitment_pool"][
            "base_population"
        ]
        assert base_population >= 250_000

    def test_reproduce_targets_base_population_dedups_class_across_org_territories(
        self,
    ) -> None:
        """A county-scale social class commonly tenants many hex
        territories the org also operates in -- summing per owned
        territory-id without dedup would double- (or N-times-) count the
        same class's population. org-player operates T1 and T2
        (``_make_balkanization_graph``); tenant the same class to both and
        assert it is counted exactly once.
        """
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.add_node(
            "sc-real-tenancy",
            "social_class",
            name="Detroit Proletariat",
            role="proletariat",
            wealth=0.0,
            population=250_000,
        )
        graph.add_edge("sc-real-tenancy", "T1", "tenancy")
        graph.add_edge("sc-real-tenancy", "T2", "tenancy")

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_reproduce_targets(uuid.uuid4(), "org-player")

        base_population = result["targets"][0]["modes"]["mass_recruitment"]["recruitment_pool"][
            "base_population"
        ]
        # sc-genesee-proles (tenant to T1, population unset -> 0) +
        # sc-real-tenancy (250_000, tenant to BOTH org territories, counted once).
        assert base_population == 250_000

    def test_attack_targets_p_acquiescence_resolves_via_tenancy_not_territory_ids(
        self,
    ) -> None:
        """Track 1 Task 9: ``get_attack_targets``'s inline ``p_acquiescence``
        collection filtered ``_node_type == "social_class"`` AND
        ``tid in data.get("territory_ids", [])`` -- the same root-cause bug
        Tasks 8/8b/8c fixed elsewhere. ``SocialClass`` has no
        ``territory_ids`` field in production, so that condition
        structurally never matched, and ``warsaw_ghetto_flag`` was
        permanently inert (``population_p_acquiescence`` always ``None``,
        ``active`` always ``False``) regardless of real survival-probability
        data. A social_class tenant (real TENANCY edge, no fabricated
        ``territory_ids``) with ``p_acquiescence`` at/below the Warsaw
        Ghetto threshold must trip the flag.
        """
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.add_node(
            "sc-desperate-tenancy",
            "social_class",
            name="Desperate Detroit Proletariat",
            role="proletariat",
            wealth=0.0,
            p_acquiescence=0.02,
        )
        graph.add_edge("sc-desperate-tenancy", "T1", "tenancy")

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_attack_targets(uuid.uuid4(), "org-player")

        assert result["warsaw_ghetto_flag"]["population_p_acquiescence"] == pytest.approx(0.02)
        assert result["warsaw_ghetto_flag"]["active"] is True


@pytest.mark.unit
class TestInvestigateTargetsDemocked:
    """Track 1 Task 9 (2026-07-18): ``get_investigate_targets`` de-mock.

    The grounding audit found: a hardcoded ``observe_capability``, a literal
    ``"org-police-union"`` target, a hardcoded ``active_moles_suspected=1``.
    Only ``territory_scans``' ``target_id``/``name``/``heat`` read the real
    graph before this task.
    """

    def test_observe_capability_honest_null_before_any_engine_tick(self) -> None:
        """A fresh graph with no EH shadow attrs (no engine tick has run
        EpistemicHorizonSystem yet) must NOT fabricate the old 0.6/TARGETED
        constant -- honest absence instead."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_investigate_targets(uuid.uuid4(), "org-player")

        assert result["observe_capability"] == {
            "intel_network_strength": None,
            "max_scan_depth": "UNKNOWN",
        }

    def test_observe_capability_reads_real_eh_shadow_attrs(self) -> None:
        """Once EH shadow attrs exist on the org's own territories (written
        by ``compute_epistemic_horizon``/``_carry_epistemic_horizon`` at
        tick-resolution time), ``observe_capability`` must reflect them."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.update_node("T1", intel_confidence=0.4, vision_state="mud")
        graph.update_node("T2", intel_confidence=0.6, vision_state="water")

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_investigate_targets(uuid.uuid4(), "org-player")

        assert result["observe_capability"]["intel_network_strength"] == pytest.approx(0.5)
        assert result["observe_capability"]["max_scan_depth"] == "DEEP"

    def test_targeted_scans_reads_real_organization_not_fixture_literal(self) -> None:
        """The prior hardcoded ``"org-police-union"``/``"Fraternal Order of
        Police"`` literal named a node that never existed in any scenario.
        A real hostile organization sharing the player's territory must
        appear instead, and the fixture literal must never appear."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.add_node(
            "org-state-police",
            "organization",
            name="Genesee County Sheriff",
            org_type="state_apparatus",
            budget=500.0,
            territory_ids=["T1"],
        )

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_investigate_targets(uuid.uuid4(), "org-player")

        target_ids = {t["target_id"] for t in result["targets"]["targeted_scans"]}
        assert "org-state-police" in target_ids
        assert "org-police-union" not in target_ids
        payload_text = str(result)
        assert "Fraternal Order of Police" not in payload_text

    def test_targeted_scans_empty_when_no_hostile_org_present(self) -> None:
        """Constitution III.11: no hostile organization/institution in the
        org's own territories means an honestly empty list, never a
        fabricated placeholder target."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_investigate_targets(uuid.uuid4(), "org-player")

        assert result["targets"]["targeted_scans"] == []

    def test_counter_intelligence_active_moles_suspected_is_honest_none(self) -> None:
        """No engine path ever writes an infiltration/mole record anywhere
        the bridge can read (``resolve_infiltrate`` has zero non-test call
        sites) -- the prior ``1`` was fabricated. Must be ``None``, not a
        fabricated count."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_investigate_targets(uuid.uuid4(), "org-player")

        assert result["targets"]["counter_intelligence"]["active_moles_suspected"] is None

    def test_territory_scans_likely_reveals_matches_real_resolver_reveal_table(self) -> None:
        """The prior hardcoded ``likely_reveals`` (``material_readiness``/
        ``hidden_factions``/``state_deployment``) did not match a single
        field ``resolve_investigate`` actually reveals for a territory
        (``heat``/``rent_level``/``population``/``under_eviction``). Must
        reuse the resolver's own reveal table, not a hand-written list that
        can silently drift from it."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_investigate_targets(uuid.uuid4(), "org-player")

        scan = result["targets"]["territory_scans"][0]
        assert set(scan["projected_reveals"]["likely_reveals"]) == {
            "heat",
            "rent_level",
            "population",
            "under_eviction",
        }

    def test_targets_bounded_to_own_territories_within_organizing_reach(self) -> None:
        """Fog decision (Track 1 Task 9): this target list is NOT
        reach-gated, because every target here is already bounded to
        org_id's own PRESENCE territories -- exactly organizing_reach's
        first hop. Pin that property directly: every scan target id is
        inside the org's own organizing reach.

        ``organizing_reach``'s PRESENCE hop walks real PRESENCE edges, not
        the ``territory_ids`` attribute directly (``Organization.
        territory_ids`` is materialized as PRESENCE edges by the real
        engine's ``WorldState.to_graph()`` -- ``game.fog.reach``'s module
        docstring) -- ``_make_balkanization_graph`` is hand-built and
        predates that materialization, so this test adds the PRESENCE edges
        explicitly to exercise the real property rather than an
        accidentally-empty reach.
        """
        from game.engine_bridge import _current_organizing_reach

        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.set_graph_attr("player_org_id", "org-player")
        graph.add_edge("org-player", "T1", "presence")
        graph.add_edge("org-player", "T2", "presence")

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_investigate_targets(uuid.uuid4(), "org-player")
            reach = _current_organizing_reach(graph)

        for scan in result["targets"]["territory_scans"]:
            assert scan["target_id"] in reach


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
        _stamp_unlocked_veil(graph)

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
class TestEducateTargetsResolveViaTenancy:
    """Track 1 / Task 8 (2026-07-18): ``get_educate_targets`` must resolve
    social_class targets via TENANCY edges (the real Occupant -> Territory
    link ``_tenancy_members_by_territory`` already walks for
    ``_dominant_class_by_territory``/``_solidarity_index_by_territory`` at
    ``/map/``), not via ``territory_ids`` on the social_class node —
    ``SocialClass`` has no such field in production (``to_graph`` dumps
    model fields verbatim; only ``Organization``/``Institution`` carry
    ``territory_ids``). The old ``_nodes_in_territory``-based lookup
    structurally always returned ``[]`` for the social_class half of its
    ``_node_type in ("social_class", "organization")`` check, so every
    territory landed in ``unavailable_communities`` regardless of real
    TENANCY data.
    """

    def _production_faithful_graph(self) -> BabylonGraph:
        """A graph shaped exactly like a real hydrated session: the
        social_class node carries NO ``territory_ids`` key at all (unlike
        ``_make_balkanization_graph``'s ``sc-genesee-proles``, which still
        carries the fictitious attribute for the other, out-of-scope
        verb-target tests that key off it) — only a live TENANCY edge
        connects it to its territory.
        """
        g = BabylonGraph()
        g.graph["tick"] = 3
        g.add_node(
            "org-player",
            "organization",
            id="org-player",
            name="Cell",
            org_type="political_faction",
            cadre_level=1.0,
            cohesion=0.4,
            budget=50.0,
            heat=0.1,
            territory_ids=["T1"],
        )
        g.add_node("T1", "territory", name="Genesee County")
        g.add_node(
            "sc-genesee-proles",
            "social_class",
            id="sc-genesee-proles",
            name="Genesee Proletariat",
            role="proletariat",
            wealth=800.0,
            ideology=IdeologicalProfile(agitation=0.5).model_dump(),
        )
        g.add_edge("sc-genesee-proles", "T1", "tenancy")
        return g

    def test_resolves_social_class_via_tenancy_edge_no_territory_ids_field(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = self._production_faithful_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_educate_targets(uuid.uuid4(), "org-player")

        target_ids = {t["community_id"] for t in result["targets"]}
        assert "sc-genesee-proles" in target_ids
        assert result["unavailable_communities"] == []

    def test_territory_with_no_tenancy_members_is_honestly_unavailable(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = self._production_faithful_graph()
        graph.remove_edge("sc-genesee-proles", "T1")

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_educate_targets(uuid.uuid4(), "org-player")

        assert result["targets"] == []
        unavailable_ids = {u["community_id"] for u in result["unavailable_communities"]}
        assert "community-unknown-T1" in unavailable_ids


def _make_wayne_tick0_graph() -> BabylonGraph:
    """Tick-0 wayne_county-shaped graph for eligibility tests.

    ORG001 (civil_society, the player) and ORG002 (state_apparatus,
    Detroit PD) share hex-1/hex-2, mirroring ``_legacy_wayne.py``. The
    social_class node is production-faithful: NO ``territory_ids``
    (``SocialClass`` has no such field; ``to_graph`` dumps model fields
    verbatim), so EDUCATE is structurally ineligible — the exact tick-0
    dead-end FR-116-4.8 converts into disabled-with-reason.
    """
    g = BabylonGraph()
    g.graph["tick"] = 0
    g.add_node(
        "ORG001",
        "organization",
        name="Wayne County Organizing Committee",
        org_type="civil_society",
        cadre_level=0.1,
        cohesion=0.5,
        budget=100.0,
        heat=0.0,
        territory_ids=["hex-1", "hex-2"],
    )
    g.add_node(
        "ORG002",
        "organization",
        name="Detroit Police Department",
        org_type="state_apparatus",
        cadre_level=5.0,
        cohesion=0.8,
        budget=5000.0,
        heat=0.3,
        territory_ids=["hex-1", "hex-2", "hex-3"],
    )
    g.add_node("hex-1", "territory", name="Downtown Detroit", heat=0.2, population=5000)
    g.add_node("hex-2", "territory", name="Dearborn", heat=0.1, population=4000)
    g.add_node(
        "C001",
        "social_class",
        name="Detroit Proletariat",
        role="proletariat",
        wealth=15.0,
        ideology=IdeologicalProfile(agitation=0.2).model_dump(),
    )
    return g


@pytest.mark.unit
class TestVerbEligibility:
    """Spec-116 FR-4.8: get_verb_eligibility derives per-verb eligibility
    from the SAME predicates that empty the per-verb target lists, on ONE
    shared hydration, with the server-side reason/remedy copy table."""

    def _eligibility(self, graph: BabylonGraph) -> tuple[dict[str, Any], MagicMock]:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        with _patched_hydrate_state(bridge, graph, tick=0) as mock_hydrate:
            result = bridge.get_verb_eligibility(uuid.uuid4(), "ORG001")
        return result, mock_hydrate

    def test_all_nine_verbs_present_with_full_row_shape(self) -> None:
        result, _ = self._eligibility(_make_wayne_tick0_graph())
        assert result["org_id"] == "ORG001"
        assert result["tick"] == 0
        assert {v["verb"] for v in result["verbs"]} == set(VERB_TO_ACTION_TYPE)
        for row in result["verbs"]:
            assert set(row) == {
                "verb",
                "eligible",
                "reason",
                "remedy",
                "can_afford",
                "afford_note",
            }

    def test_tick0_wayne_educate_ineligible_with_reason_and_remedy(self) -> None:
        result, _ = self._eligibility(_make_wayne_tick0_graph())
        by_verb = {v["verb"]: v for v in result["verbs"]}
        assert by_verb["educate"]["eligible"] is False
        assert by_verb["educate"]["reason"] == "No organized community in your territories yet."
        assert by_verb["educate"]["remedy"] == VERB_INELIGIBILITY_COPY["educate"][1]

    def test_tick0_wayne_mobilize_ineligible_state_apparatus_does_not_count(self) -> None:
        result, _ = self._eligibility(_make_wayne_tick0_graph())
        by_verb = {v["verb"]: v for v in result["verbs"]}
        assert by_verb["mobilize"]["eligible"] is False
        assert by_verb["mobilize"]["reason"] == VERB_INELIGIBILITY_COPY["mobilize"][0]
        assert by_verb["mobilize"]["remedy"] == VERB_INELIGIBILITY_COPY["mobilize"][1]

    def test_tick0_wayne_eligible_verbs_carry_null_copy(self) -> None:
        result, _ = self._eligibility(_make_wayne_tick0_graph())
        by_verb = {v["verb"]: v for v in result["verbs"]}
        # ORG002 shares hex-1/hex-2 -> aid (org arm), attack, negotiate.
        # Territory nodes exist -> campaign, move. Own territories -> investigate.
        for verb in ("aid", "attack", "negotiate", "campaign", "move", "investigate", "reproduce"):
            assert by_verb[verb]["eligible"] is True, verb
            assert by_verb[verb]["reason"] is None, verb
            assert by_verb[verb]["remedy"] is None, verb

    def test_educate_flips_eligible_when_social_class_shares_territory(self) -> None:
        # A live TENANCY edge (the real Occupant -> Territory link), not a
        # fabricated `territory_ids` stamp on the social_class node --
        # SocialClass has no such field in production (Task 8 / Task 8b).
        graph = _make_wayne_tick0_graph()
        graph.add_edge("C001", "hex-1", "tenancy")
        result, _ = self._eligibility(graph)
        by_verb = {v["verb"]: v for v in result["verbs"]}
        assert by_verb["educate"]["eligible"] is True
        assert by_verb["educate"]["reason"] is None

    def test_exactly_one_hydration(self) -> None:
        _result, mock_hydrate = self._eligibility(_make_wayne_tick0_graph())
        assert mock_hydrate.call_count == 1, (
            "get_verb_eligibility must evaluate all nine predicates on ONE "
            "shared hydration (the 9x get_*_targets loop would cost ~18)"
        )

    def test_org_not_found_is_honest_error(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        with _patched_hydrate_state(bridge, _make_wayne_tick0_graph(), tick=0):
            result = bridge.get_verb_eligibility(uuid.uuid4(), "NOT-AN-ORG")
        assert result == {"status": "error", "error": "Org not found"}


@pytest.mark.unit
class TestVerbEligibilityAgreesWithTargetsRealWayneCounty:
    """Track 1 / Task 8b (2026-07-18): ``get_verb_eligibility`` must agree,
    verb-by-verb, with whatever the corresponding ``get_*_targets`` method
    actually returns -- on the REAL ``wayne_county`` scenario graph, not a
    hand-built fixture.

    This is the exact class of contradiction Task 8 left behind:
    ``get_educate_targets`` was fixed to resolve social_class targets via
    TENANCY (:func:`_tenancy_members_by_territory`), but
    ``get_verb_eligibility``'s ``has_social_class`` predicate still checked
    the nonexistent ``territory_ids`` field on social_class nodes, so
    ``educate`` could report ineligible while real targets existed. Pinning
    eligibility against the target list directly -- rather than testing
    either side alone -- is what would have caught it.
    """

    @staticmethod
    def _bridge_with_real_wayne_graph() -> tuple[EngineBridge, BabylonGraph]:
        state = _build_initial_state_for_scenario("wayne_county")
        graph = state.to_graph()
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        return bridge, graph

    @pytest.mark.parametrize("org_id", ["ORG001", "ORG002"])
    def test_educate_eligibility_agrees_with_educate_targets(self, org_id: str) -> None:
        bridge, graph = self._bridge_with_real_wayne_graph()
        with _patched_hydrate_state(bridge, graph, tick=0):
            targets = bridge.get_educate_targets(uuid.uuid4(), org_id)
            eligibility = bridge.get_verb_eligibility(uuid.uuid4(), org_id)

        by_verb = {v["verb"]: v for v in eligibility["verbs"]}
        assert by_verb["educate"]["eligible"] == bool(targets["targets"]), (
            f"educate eligible={by_verb['educate']['eligible']!r} disagrees with "
            f"get_educate_targets returning {len(targets['targets'])} targets for {org_id}"
        )

    @pytest.mark.parametrize("org_id", ["ORG001", "ORG002"])
    def test_aid_eligibility_agrees_with_aid_targets(self, org_id: str) -> None:
        bridge, graph = self._bridge_with_real_wayne_graph()
        with _patched_hydrate_state(bridge, graph, tick=0):
            targets = bridge.get_aid_targets(uuid.uuid4(), org_id)
            eligibility = bridge.get_verb_eligibility(uuid.uuid4(), org_id)

        by_verb = {v["verb"]: v for v in eligibility["verbs"]}
        has_any_target = bool(targets["population_targets"]) or bool(targets["org_targets"])
        assert by_verb["aid"]["eligible"] == has_any_target, (
            f"aid eligible={by_verb['aid']['eligible']!r} disagrees with get_aid_targets "
            f"returning {len(targets['population_targets'])} population + "
            f"{len(targets['org_targets'])} org targets for {org_id}"
        )

    def test_aid_population_targets_resolves_via_tenancy_real_wayne_county(self) -> None:
        """``get_aid_targets``'s population arm has the SAME
        ``_nodes_in_territory``/``territory_ids`` root-cause bug as
        pre-fix ``get_educate_targets`` -- ``ORG001``'s own territories
        (``862ab21b7ffffff``, ``862ab2c57ffffff``) are real TENANCY homes
        for ``C001`` in the ``wayne_county`` scenario, so the population
        arm must not come back empty. The ``aid`` eligibility bit alone
        does not catch this: ``has_org_in_reach`` (ORG001/ORG002 share
        territory) keeps ``aid`` eligible regardless, masking a fully
        empty population arm -- hence this direct assertion.
        """
        bridge, graph = self._bridge_with_real_wayne_graph()
        with _patched_hydrate_state(bridge, graph, tick=0):
            targets = bridge.get_aid_targets(uuid.uuid4(), "ORG001")

        assert targets["population_targets"], (
            "get_aid_targets population arm returned no targets for ORG001 despite "
            "real TENANCY-linked social_class C001 in its own territories"
        )

    def test_attack_targets_p_acquiescence_resolves_via_tenancy_real_wayne_county(
        self,
    ) -> None:
        """Track 1 Task 9: confirmed empirically against the real
        ``wayne_county`` scenario -- ``C001`` (real ``p_acquiescence=0.0``)
        tenants ORG001's own territory via TENANCY, but the pre-fix inline
        loop's ``tid in data.get("territory_ids", [])`` check on
        social_class nodes never matched (SocialClass carries no
        ``territory_ids`` in production), so ``p_acquiescence_values`` was
        always ``[]`` and ``warsaw_ghetto_flag.population_p_acquiescence``
        was always ``None``. After the fix it must surface the real value.
        """
        bridge, graph = self._bridge_with_real_wayne_graph()
        with _patched_hydrate_state(bridge, graph, tick=0):
            result = bridge.get_attack_targets(uuid.uuid4(), "ORG001")

        assert result["warsaw_ghetto_flag"]["population_p_acquiescence"] is not None

    def test_investigate_targeted_scans_finds_real_state_apparatus_real_wayne_county(
        self,
    ) -> None:
        """Track 1 Task 9: ``ORG002`` (Detroit Police Department,
        ``org_type=state_apparatus``) shares territory
        ``862ab21b7ffffff``/``862ab2c57ffffff`` with ``ORG001`` in the real
        ``wayne_county`` scenario. The pre-fix ``targeted_scans`` always
        returned the fictional literal ``"org-police-union"`` regardless;
        after the fix it must surface the real ORG002 node instead."""
        bridge, graph = self._bridge_with_real_wayne_graph()
        with _patched_hydrate_state(bridge, graph, tick=0):
            result = bridge.get_investigate_targets(uuid.uuid4(), "ORG001")

        target_ids = {t["target_id"] for t in result["targets"]["targeted_scans"]}
        assert "ORG002" in target_ids
        assert "org-police-union" not in target_ids


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

        # Batched path (task #43): one plural persist_action_results call per
        # tick carrying every action's row (pool present => Postgres path).
        mock_persistence.persist_action_results.assert_called_once()
        mock_persistence.persist_action_result.assert_not_called()
        call = mock_persistence.persist_action_results.call_args
        results = call.args[1]  # (tick, results, *, session_id=...)
        assert call.kwargs["session_id"] == self._SID
        assert len(results) == 1
        row = results[0]
        assert row["success"] is True
        assert row["consciousness_delta"] == 0.05
        assert row["details"]["direct_effects"] == {"note": "real"}
        assert row["details"]["failure_reason"] is None

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

        mock_persistence.persist_action_results.assert_called_once()
        results = mock_persistence.persist_action_results.call_args.args[1]
        assert len(results) == 1
        row = results[0]
        assert row["success"] is False
        assert row["details"]["failure_reason"] is not None

    @patch("game.engine_bridge.step")
    def test_batches_all_action_results_into_one_call(self, mock_step: MagicMock) -> None:
        """Two pending actions => a single persist_action_results call whose
        results list carries both rows (task #43 batched activation)."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = [
            {"org_id": "pf1", "verb": "educate", "target_id": "hex_a"},
            {"org_id": "pf2", "verb": "educate", "target_id": "hex_b"},
        ]
        mock_step.return_value = _make_mock_new_state()
        bridge = EngineBridge(mock_persistence)
        bridge.resolve_tick(self._SID)

        mock_persistence.persist_action_results.assert_called_once()
        mock_persistence.persist_action_result.assert_not_called()
        results = mock_persistence.persist_action_results.call_args.args[1]
        assert len(results) == 2
        assert {r["org_id"] for r in results} == {"pf1", "pf2"}


# ---------------------------------------------------------------------- #
# Track 1 / Task 3 (2026-07-18): the intel ledger's writer
# ---------------------------------------------------------------------- #


@pytest.mark.unit
class TestInvestigateFieldSnapshot:
    """``_investigate_field_snapshot`` is the write-side half of the intel
    ledger (``game.fog.ledger.IntelLedger``): it freezes the fields an
    INVESTIGATE resolution named as revealed (field NAMES only —
    ``resolve_investigate``'s ``direct_effects`` carries no values) off the
    live post-tick graph, so a later fog read shows the TRUE value as of
    that tick, never a recomputation."""

    def _graph_with_territory(self, **attrs: Any) -> BabylonGraph:
        graph = BabylonGraph()
        graph.add_node("T1", _node_type="territory", **attrs)
        return graph

    def test_non_investigate_action_yields_none(self) -> None:
        graph = self._graph_with_territory(heat=0.42)
        result = _investigate_field_snapshot(
            ActionType.EDUCATE, "T1", {"revealed": {"T1": ["heat"]}}, graph
        )
        assert result is None

    def test_no_action_type_yields_none(self) -> None:
        graph = self._graph_with_territory(heat=0.42)
        result = _investigate_field_snapshot(None, "T1", {"revealed": {"T1": ["heat"]}}, graph)
        assert result is None

    def test_missing_target_id_yields_none(self) -> None:
        graph = self._graph_with_territory(heat=0.42)
        result = _investigate_field_snapshot(
            ActionType.MAP_NETWORK, None, {"revealed": {"T1": ["heat"]}}, graph
        )
        assert result is None

    def test_target_not_in_graph_yields_none(self) -> None:
        graph = self._graph_with_territory(heat=0.42)
        result = _investigate_field_snapshot(
            ActionType.MAP_NETWORK, "T-GONE", {"revealed": {"T-GONE": ["heat"]}}, graph
        )
        assert result is None

    def test_no_revealed_fields_for_target_yields_none(self) -> None:
        graph = self._graph_with_territory(heat=0.42)
        result = _investigate_field_snapshot(ActionType.MAP_NETWORK, "T1", {"revealed": {}}, graph)
        assert result is None

    def test_failed_investigate_with_empty_direct_effects_yields_none(self) -> None:
        """A failed INVESTIGATE (mass-receptivity gate) carries no
        ``revealed`` key at all — honest absence, not a crash."""
        graph = self._graph_with_territory(heat=0.42)
        result = _investigate_field_snapshot(ActionType.MAP_NETWORK, "T1", {}, graph)
        assert result is None

    def test_successful_investigate_captures_the_real_graph_values(self) -> None:
        graph = self._graph_with_territory(heat=0.42, rent_level=0.1, population=500)
        result = _investigate_field_snapshot(
            ActionType.MAP_NETWORK,
            "T1",
            {"scan_type": "territory_scan", "revealed": {"T1": ["heat", "population"]}},
            graph,
        )
        assert result == {
            "field_group": "territory:political",
            "value_snapshot": {"heat": 0.42, "population": 500},
        }

    def test_field_group_matches_apply_fogs_own_derivation(self) -> None:
        """Written under apply_fog's EXACT field_group format
        (``game.fog.filter.political_field_group``) — a mismatch would make
        the entry silently unreachable at read time."""
        from game.fog.filter import political_field_group

        graph = self._graph_with_territory(heat=0.42)
        result = _investigate_field_snapshot(
            ActionType.MAP_NETWORK, "T1", {"revealed": {"T1": ["heat"]}}, graph
        )
        assert result is not None
        assert result["field_group"] == political_field_group("territory")

    def test_revealed_field_absent_from_the_node_is_not_fabricated(self) -> None:
        """``resolve_investigate``'s default revealed-field list can name a
        field the node doesn't actually carry — never invent a value."""
        graph = self._graph_with_territory(heat=0.42)  # no rent_level attr
        result = _investigate_field_snapshot(
            ActionType.MAP_NETWORK, "T1", {"revealed": {"T1": ["heat", "rent_level"]}}, graph
        )
        assert result == {
            "field_group": "territory:political",
            "value_snapshot": {"heat": 0.42},
        }


@pytest.mark.unit
class TestResolveTickPersistsInvestigateSnapshot:
    """End-to-end (mocked persistence): resolve_tick's per-action loop
    stashes the intel snapshot onto the persisted ``action_result`` row for
    a successful INVESTIGATE — the enrichment ``_derive_intel_ledger``
    later reads back."""

    _SID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    @patch("game.engine_bridge.step")
    def test_investigate_action_result_carries_the_intel_snapshot(
        self, mock_step: MagicMock
    ) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = [
            {"org_id": "pf1", "verb": "investigate", "target_id": "T1"},
        ]

        def fake_step(*_args: Any, **kwargs: Any) -> MagicMock:
            ctx = kwargs.get("persistent_context")
            assert ctx is not None
            ctx["turn_resolution"] = {
                "action_phase_results": [
                    {
                        "action": {
                            "org_id": "pf1",
                            "action_type": "map_network",
                            "target_id": "T1",
                        },
                        "success": True,
                        "consciousness_delta": None,
                        "direct_effects": {
                            "scan_type": "territory_scan",
                            "revealed": {"T1": ["heat"]},
                        },
                        "failure_reason": None,
                    }
                ]
            }
            new_state = _make_mock_new_state()
            graph = _make_minimal_graph()
            graph.add_node("T1", _node_type="territory", heat=0.734)
            new_state.to_graph.return_value = graph
            return new_state

        mock_step.side_effect = fake_step
        bridge = EngineBridge(mock_persistence)
        bridge.resolve_tick(self._SID)

        mock_persistence.persist_action_results.assert_called_once()
        results = mock_persistence.persist_action_results.call_args.args[1]
        assert len(results) == 1
        details = results[0]["details"]
        assert details["intel_field_group"] == "territory:political"
        assert details["intel_value_snapshot"] == {"heat": 0.734}

    @patch("game.engine_bridge.step")
    def test_non_investigate_action_carries_no_intel_snapshot(self, mock_step: MagicMock) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = [
            {"org_id": "pf1", "verb": "educate", "target_id": "T1"},
        ]

        def fake_step(*_args: Any, **kwargs: Any) -> MagicMock:
            ctx = kwargs.get("persistent_context")
            assert ctx is not None
            ctx["turn_resolution"] = {
                "action_phase_results": [
                    {
                        "action": {"org_id": "pf1", "action_type": "educate", "target_id": "T1"},
                        "success": True,
                        "consciousness_delta": None,
                        "direct_effects": {"note": "irrelevant"},
                        "failure_reason": None,
                    }
                ]
            }
            return _make_mock_new_state()

        mock_step.side_effect = fake_step
        bridge = EngineBridge(mock_persistence)
        bridge.resolve_tick(self._SID)

        results = mock_persistence.persist_action_results.call_args.args[1]
        details = results[0]["details"]
        assert "intel_field_group" not in details
        assert "intel_value_snapshot" not in details


@pytest.mark.unit
@pytest.mark.django_db
class TestDeriveIntelLedger:
    """Track 1 / Task 3: ``_derive_intel_ledger`` reads back persisted
    ``action_result`` rows and folds them via ``ledger_from_events`` — the
    real write-then-read loop, exercised against a real (test) database
    rather than a mock."""

    def _make_session(self) -> uuid.UUID:
        from game.models import GameSession

        sid = uuid.uuid4()
        GameSession.objects.create(id=sid, scenario="default", current_tick=0)
        return sid

    def test_fresh_session_yields_an_empty_ledger(self) -> None:
        sid = self._make_session()
        ledger = _derive_intel_ledger(sid)
        assert ledger.entries == ()

    def test_enriched_investigate_row_becomes_a_reachable_ledger_entry(self) -> None:
        from game.fog.ledger import read_intel
        from game.models import ActionResult

        sid = self._make_session()
        ActionResult.objects.create(
            session_id=sid,
            tick=10,
            org_id="PLAYER_ORG",
            action_type=ActionType.MAP_NETWORK.value,
            target_id="T1",
            initiative_score=0.0,
            action_cost=1.0,
            success=True,
            details={
                "direct_effects": {
                    "scan_type": "territory_scan",
                    "revealed": {"T1": ["heat"]},
                },
                "failure_reason": None,
                "intel_field_group": "territory:political",
                "intel_value_snapshot": {"heat": 0.734},
            },
        )

        ledger = _derive_intel_ledger(sid)

        reading = read_intel(
            ledger,
            node_id="T1",
            field_group="territory:political",
            tick=12,
            staleness_ticks=5,
            unknown_ticks=20,
        )
        assert reading.tier == "exact"
        assert reading.value_snapshot == {"heat": 0.734}

    def test_failed_investigate_row_is_excluded(self) -> None:
        """``success=False`` rows never reach the ledger (excluded by the
        query filter itself) — a failed INVESTIGATE (mass-receptivity gate)
        revealed nothing."""
        from game.models import ActionResult

        sid = self._make_session()
        ActionResult.objects.create(
            session_id=sid,
            tick=10,
            org_id="PLAYER_ORG",
            action_type=ActionType.MAP_NETWORK.value,
            target_id="T1",
            initiative_score=0.0,
            action_cost=1.0,
            success=False,
            details={"direct_effects": {}, "failure_reason": "masses do not trust you"},
        )

        ledger = _derive_intel_ledger(sid)
        assert ledger.entries == ()

    def test_row_without_the_enrichment_keys_is_excluded(self) -> None:
        """An ``action_result`` row with no ``intel_field_group``/
        ``intel_value_snapshot`` (e.g. any row persisted before this task
        shipped) is skipped, never fabricated (Constitution III.11)."""
        from game.models import ActionResult

        sid = self._make_session()
        ActionResult.objects.create(
            session_id=sid,
            tick=10,
            org_id="PLAYER_ORG",
            action_type=ActionType.MAP_NETWORK.value,
            target_id="T1",
            initiative_score=0.0,
            action_cost=1.0,
            success=True,
            details={"direct_effects": {"revealed": {"T1": ["heat"]}}, "failure_reason": None},
        )

        ledger = _derive_intel_ledger(sid)
        assert ledger.entries == ()

    def test_non_investigate_action_result_rows_are_excluded(self) -> None:
        from game.models import ActionResult

        sid = self._make_session()
        ActionResult.objects.create(
            session_id=sid,
            tick=10,
            org_id="PLAYER_ORG",
            action_type="educate",
            target_id="T1",
            initiative_score=0.0,
            action_cost=1.0,
            success=True,
            details={
                "direct_effects": {},
                "failure_reason": None,
                "intel_field_group": "territory:political",
                "intel_value_snapshot": {"heat": 0.1},
            },
        )

        ledger = _derive_intel_ledger(sid)
        assert ledger.entries == ()

    def test_query_helper_returns_plain_dicts_with_the_expected_keys(self) -> None:
        from game.models import ActionResult

        sid = self._make_session()
        ActionResult.objects.create(
            session_id=sid,
            tick=3,
            org_id="PLAYER_ORG",
            action_type=ActionType.MAP_NETWORK.value,
            target_id="T1",
            initiative_score=0.0,
            action_cost=1.0,
            success=True,
            details={
                "intel_field_group": "territory:political",
                "intel_value_snapshot": {"heat": 0.1},
            },
        )

        rows = _query_investigate_action_results(sid)

        assert len(rows) == 1
        assert rows[0]["tick"] == 3
        assert rows[0]["target_id"] == "T1"


@pytest.mark.unit
class TestDeriveIntelLedgerWithoutDjangoDb:
    """No ``@pytest.mark.django_db`` here on purpose: proves the best-effort
    fallback actually engages when the ORM query is blocked (pytest-django
    forbids DB access without the marker) — the same failure mode a
    headless/non-web context hits — rather than crashing every
    player-facing view that now calls ``_derive_intel_ledger``."""

    def test_blocked_db_access_yields_an_empty_ledger_not_a_crash(self) -> None:
        ledger = _derive_intel_ledger(uuid.uuid4())
        assert ledger.entries == ()


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


@pytest.mark.unit
class TestReactionaryVerbSeverityAndAnchoring:
    """spec-116 FR-116-4.7: pogrom/lockout/vigilantism severity tier +
    uprising-pattern territory anchoring on the TARGET community id."""

    @staticmethod
    def _verb_event(event_type: str, target_id: str) -> MagicMock:
        event = MagicMock()
        event.event_type = event_type
        event.tick = 5
        event.data = {
            "org_id": "ORG_FASH",
            "target_id": target_id,
            "repression_increment": 0.15,
        }
        event.narrative = None
        return event

    def test_verbs_classify_as_warning(self) -> None:
        from game.engine_bridge import _classify_event

        assert _classify_event("pogrom") == "warning"
        assert _classify_event("lockout") == "warning"
        assert _classify_event("vigilantism") == "warning"

    def test_pogrom_anchors_to_target_territory(self) -> None:
        from game.engine_bridge import _serialize_event

        graph = _graph_with_tenancy(class_to_territory={"C001": "T001"})
        result = _serialize_event(self._verb_event("pogrom", "C001"), uuid.uuid4(), graph=graph)

        assert result["data"]["territory_id"] == "T001"

    def test_lockout_and_vigilantism_anchor_too(self) -> None:
        from game.engine_bridge import _serialize_event

        graph = _graph_with_tenancy(class_to_territory={"C001": "T001"})
        for verb in ("lockout", "vigilantism"):
            result = _serialize_event(self._verb_event(verb, "C001"), uuid.uuid4(), graph=graph)
            assert result["data"]["territory_id"] == "T001"

    def test_unresolvable_target_yields_honest_none(self) -> None:
        from game.engine_bridge import _serialize_event

        graph = _graph_with_tenancy(class_to_territory={"C001": "T001", "C999": None})
        result = _serialize_event(
            self._verb_event("vigilantism", "C999"), uuid.uuid4(), graph=graph
        )

        assert "territory_id" in result["data"]
        assert result["data"]["territory_id"] is None

    def test_absent_graph_yields_none_never_guessed(self) -> None:
        from game.engine_bridge import _serialize_event

        result = _serialize_event(self._verb_event("pogrom", "C001"), uuid.uuid4())

        assert result["data"]["territory_id"] is None


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
        # G4: profit_rate is now veil-gated — this test is about the COLUMN
        # SELECTION (profit_rate vs exploitation_rate), not veil gating, so
        # stamp the player org fully unlocked (Tier 2).
        graph = mock_persistence.hydrate_graph.return_value
        graph.nodes[graph.graph["player_org_id"]]["acquired_doctrine_ids"] = (
            "class_consciousness",
            "trade_unionism",
        )
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

    def test_g4_veil_tier_zero_masks_profit_rate_frames(self) -> None:
        """G4: profit_rate/exploitation_rate are value-axis — below the
        player org's Veil Tier 1, every frame value masks to None even
        though the persisted history has real numbers (never a client-side-
        only hide; the scrubber must never see the real replay)."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_county_trace_latest_tick.return_value = 1
        mock_persistence.query_county_trace_metric_frames.return_value = [
            {"tick": 0, "county_fips": "26163", "profit_rate": 0.10, "exploitation_rate": 0.20},
            {"tick": 1, "county_fips": "26163", "profit_rate": 0.15, "exploitation_rate": 0.25},
        ]
        # Default fixture graph's player org starts at Tier 0 (empty
        # acquired_doctrine_ids) — no stamping needed for this test.
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="profit_rate")

        assert result["frames"][0]["values"] == {"26163": None}
        assert result["frames"][1]["values"] == {"26163": None}

    def test_g4_veil_never_gates_money_form_heat_metric(self) -> None:
        """heat/population are money-form/political, never veil-gated — no
        tier resolution overhead, no masking, regardless of tier."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.query_territory_snapshot_latest_tick.return_value = 0
        mock_persistence.query_territory_snapshot_metric_frames.return_value = [
            {"tick": 0, "county_fips": "26163", "heat": 0.42, "pop_total": 8000},
        ]
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_map_history(uuid.uuid4(), metric="heat")

        assert result["frames"][0]["values"] == {"26163": pytest.approx(0.42)}
        mock_persistence.hydrate_graph.assert_not_called()

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


class TestBuildTickSummaryMarketAxis:
    """Program 23 (ADR077): the scissors logs flow state.market → summary row."""

    def test_market_axis_flows_into_summary_columns(self) -> None:
        from web.game.engine_bridge import _build_tick_summary

        from babylon.models.market import MarketState
        from babylon.models.world_state import WorldState

        state = WorldState(
            tick=3,
            market=MarketState(
                price_log=0.25,
                price_velocity=0.0,
                fictitious_log=-0.1,
                fictitious_velocity=0.0,
                surplus_ema=1.0,
                value_ema=4.0,
                tick=3,
            ),
        )
        summary = _build_tick_summary(state, organizations=[])
        assert summary["price_log"] == pytest.approx(0.25)
        assert summary["fictitious_log"] == pytest.approx(-0.1)
        assert summary["market_corrections"] == 0  # ledger present with the axis

    def test_correction_ledger_flows_into_summary(self) -> None:
        from web.game.engine_bridge import _build_tick_summary

        from babylon.models.market import MarketState
        from babylon.models.world_state import WorldState

        state = WorldState(
            tick=12,
            market=MarketState(
                price_log=0.1,
                price_velocity=0.0,
                fictitious_log=0.2,
                fictitious_velocity=0.0,
                surplus_ema=1.0,
                value_ema=4.0,
                tick=12,
                corrections=2,
                last_correction_tick=11,
            ),
        )
        summary = _build_tick_summary(state, organizations=[])
        assert summary["market_corrections"] == 2

    def test_absent_axis_is_honest_null(self) -> None:
        from web.game.engine_bridge import _build_tick_summary

        from babylon.models.world_state import WorldState

        summary = _build_tick_summary(WorldState(tick=1), organizations=[])
        assert summary["price_log"] is None
        assert summary["fictitious_log"] is None
        assert summary["market_corrections"] is None


@pytest.mark.unit
class TestBuildTickSummarySeriesAggregates:
    """Task 19 (spec-116 4d.5): county-deduped tick_* aggregates ride tick_summary.

    The series is HONEST-SPARSE by design: tick_* attrs stamp at year
    boundaries only (weekly campaign => yearly points) and are carried
    forward between boundaries — NULL before the first boundary, a step
    function after, never fabricated smoothing (Constitution III.11).
    """

    _SERIES_KEYS = (
        "crisis_pop_share",
        "bifurcation_score_mean",
        "wage_compression_mean",
        "capital_stock_total",
        "unemployment_rate_mean",
    )

    @staticmethod
    def _graph_with_two_counties() -> BabylonGraph:
        graph = BabylonGraph()
        # T1/T2 share one county and carry IDENTICAL county-level stamps —
        # they must count ONCE (the _county_flow_snapshot N-fold-inflation
        # hazard), never once per territory.
        graph.add_node(
            "T1",
            node_type="territory",
            county_fips="26163",
            population=1_000_000,
            tick_crisis_phase="deep",
            tick_bifurcation_score=-0.5,
            tick_wage_compression=0.2,
            tick_capital_stock=1e9,
            tick_unemployment_rate=0.10,
        )
        graph.add_node(
            "T2",
            node_type="territory",
            county_fips="26163",
            population=500_000,
            tick_crisis_phase="deep",
            tick_bifurcation_score=-0.5,
            tick_wage_compression=0.2,
            tick_capital_stock=1e9,
            tick_unemployment_rate=0.10,
        )
        graph.add_node(
            "T3",
            node_type="territory",
            county_fips="26125",
            population=500_000,
            tick_crisis_phase="normal",
            tick_bifurcation_score=0.3,
            tick_wage_compression=0.0,
            tick_capital_stock=2e9,
            tick_unemployment_rate=0.05,
        )
        return graph

    def test_aggregates_are_county_deduped_and_population_weighted(self) -> None:
        from babylon.models.world_state import WorldState
        from game.engine_bridge import _build_tick_summary

        summary = _build_tick_summary(
            WorldState(tick=52), organizations=[], graph=self._graph_with_two_counties()
        )

        # Wayne pop 1.5M (deep) vs 26125 pop 0.5M (normal): 1.5/2.0.
        assert summary["crisis_pop_share"] == pytest.approx(0.75)
        # Weighted over COUNTIES: (-0.5 * 1.5e6 + 0.3 * 0.5e6) / 2e6.
        assert summary["bifurcation_score_mean"] == pytest.approx(-0.3)
        assert summary["wage_compression_mean"] == pytest.approx(0.15)
        # Extensive sum, ONE term per county: 1e9 + 2e9 — never 1e9*2 + 2e9.
        assert summary["capital_stock_total"] == pytest.approx(3e9)
        assert summary["unemployment_rate_mean"] == pytest.approx(0.0875)

    def test_no_graph_or_no_boundary_yet_is_honest_null(self) -> None:
        from babylon.models.world_state import WorldState
        from game.engine_bridge import _build_tick_summary

        no_graph = _build_tick_summary(WorldState(tick=1), organizations=[])
        bare_graph = BabylonGraph()
        bare_graph.add_node("T1", node_type="territory", county_fips="26163", population=10)
        pre_boundary = _build_tick_summary(WorldState(tick=1), organizations=[], graph=bare_graph)

        for key in self._SERIES_KEYS:
            assert no_graph[key] is None, f"{key} must be NULL without a graph"
            assert pre_boundary[key] is None, f"{key} must be NULL before the first boundary"


# ---------------------------------------------------------------------- #
# Spec-116 FR-4.1: the Voice heartbeat — CausalChainObserver wiring
# ---------------------------------------------------------------------- #


@pytest.mark.unit
class TestCausalHeartbeatWiring:
    """resolve_tick runs the per-session CausalChainObserver and persists its
    frames as deterministic NarrationRecord beats (spec-116 FR-4.1).
    Observer-layer only: no state/graph mutation, outside the tick hash."""

    _SID = uuid.UUID("dddddddd-bbbb-cccc-dddd-eeeeeeeeeeee")

    @patch("game.engine_bridge.step")
    def test_resolve_tick_caches_observer_per_session(self, mock_step: MagicMock) -> None:
        from game.engine_bridge import _session_causal_observers

        _session_causal_observers.clear()
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = []
        mock_step.return_value = _make_mock_new_state()

        bridge = EngineBridge(mock_persistence)
        bridge.resolve_tick(self._SID)
        first = _session_causal_observers.get(self._SID)
        assert first is not None, "resolve_tick must create the per-session observer"

        bridge.resolve_tick(self._SID)
        assert _session_causal_observers.get(self._SID) is first, (
            "the SAME observer instance must survive across resolve_tick calls "
            "(the 5-tick history buffer lives on it)"
        )

    def test_persist_causal_beats_safe_never_raises_without_db(self) -> None:
        """Best-effort sibling contract (_persist_*_safe family): a DB failure
        — here pytest-django blocking access (no django_db mark) — is
        swallowed and logged, never fails tick resolution."""
        from game.engine_bridge import _persist_causal_beats_safe

        frame = {
            "pattern": "TICK_PULSE",
            "tick": 3,
            "deltas": {
                "pool": {"before": 100.0, "after": 90.0},
                "wage": {"before": 0.2, "after": 0.2},
                "p_rev": {"before": 0.3, "after": 0.3},
            },
        }
        _persist_causal_beats_safe(self._SID, 3, (frame,))  # must not raise


@pytest.mark.unit
@pytest.mark.django_db
class TestCausalHeartbeatPersistence:
    """The pulse beat lands in narration_record on every resolved tick."""

    _SID = uuid.UUID("eeeeeeee-bbbb-cccc-dddd-eeeeeeeeeeee")

    @patch("game.engine_bridge.step")
    def test_resolve_tick_persists_pulse_beat(self, mock_step: MagicMock) -> None:
        from game.causal_voice import CAUSAL_MODEL_ID, CAUSAL_PROMPT_VERSION
        from game.engine_bridge import _session_causal_observers
        from game.models import GameSession, NarrationRecord

        _session_causal_observers.clear()
        GameSession.objects.create(
            id=self._SID, scenario="default", current_tick=0, status="active"
        )
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_pending_turns.return_value = []
        mock_step.return_value = _make_mock_new_state(tick=1)

        bridge = EngineBridge(mock_persistence)
        bridge.resolve_tick(self._SID)

        record = NarrationRecord.objects.get(
            session_id=self._SID, tick=1, beat_id="causal-pulse-t1"
        )
        assert record.scope == "tick"
        assert record.register == "wire"
        assert record.model_id == CAUSAL_MODEL_ID
        assert record.prompt_version == CAUSAL_PROMPT_VERSION
        assert record.degraded is False
        assert record.headline == "The week's ledger, tick 1."


@pytest.mark.unit
class TestExpectedDeltas:
    """Spec-116 FR-116-4.4: per-target expected_deltas on verb-target rows,
    sourced from the resolvers' own math (preview == resolution). The axis a
    verb has no per-target formula for is an honest None, never 0.0."""

    def test_educate_rows_carry_resolver_parity_consciousness_delta(self) -> None:
        from babylon.models.enums import ActionType
        from game.engine_bridge import _preview_consciousness_delta

        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_educate_targets(uuid.uuid4(), "org-player")

        target = result["targets"][0]
        expected = round(
            _preview_consciousness_delta(
                dict(graph.nodes["org-player"]),
                "sc-genesee-proles",
                ActionType.EDUCATE,
                graph,
            ),
            4,
        )
        assert target["expected_deltas"]["consciousness_delta"] == expected
        assert target["expected_deltas"]["heat_delta"] is None

    def test_aid_population_rows_carry_deltas_and_org_rows_do_not(self) -> None:
        from babylon.models.enums import ActionType
        from game.engine_bridge import _preview_consciousness_delta

        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_aid_targets(uuid.uuid4(), "org-player")

        pop = result["population_targets"][0]
        expected = round(
            _preview_consciousness_delta(
                dict(graph.nodes["org-player"]),
                pop["community_id"],
                ActionType.PROVIDE_SERVICE,
                graph,
            ),
            4,
        )
        assert pop["expected_deltas"]["consciousness_delta"] == expected
        assert pop["expected_deltas"]["heat_delta"] is None
        for org_row in result["org_targets"]:
            assert "expected_deltas" not in org_row

    def test_attack_rows_carry_defines_driven_heat_delta(self) -> None:
        from babylon.config.defines import GameDefines

        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.add_node(
            "org-rivals",
            "organization",
            name="Citizens Council",
            org_type="business",
            budget=340.0,
            territory_ids=["T1"],
        )
        graph.add_node(
            "inst-court",
            "institution",
            name="County Court",
            # Real shape: production carries factional weights under
            # internal_balance (Institution.model_dump()'s nested
            # InternalBalanceOfForces) -- no production graph ever emits a
            # flat "factional_composition" key (Track 1 audit, task #45).
            internal_balance=InternalBalanceOfForces(
                liberal_technocratic=0.6,
                revanchist_fascist=0.3,
                institutionalist_bonapartist=0.1,
            ).model_dump(),
            territory_ids=["T1"],
        )

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_attack_targets(uuid.uuid4(), "org-player")

        heat_gain = round(GameDefines().ooda.attack_self_heat_gain, 4)
        org_rows = result["targets"]["organizations"]
        inst_rows = result["targets"]["institutions"]
        assert len(org_rows) >= 1 and len(inst_rows) >= 1
        for row in [*org_rows, *inst_rows]:
            assert row["expected_deltas"]["heat_delta"] == heat_gain
            assert row["expected_deltas"]["consciousness_delta"] is None
        court_row = next(r for r in inst_rows if r["target_id"] == "inst-court")
        assert court_row["factional_control"] == {
            "liberal_technocratic": 0.6,
            "revanchist_fascist": 0.3,
            "institutionalist_bonapartist": 0.1,
        }

    def test_educate_row_includes_doctrine_theory_bonus_for_class_analysis_org(self) -> None:
        """Task-18-review fix: EDUCATE's resolver (resolve_educate ->
        resolve_action(..., doctrine=services.defines.doctrine)) applies the
        Step-7.5 doctrine theory bonus (ADR073) when the acting org carries
        CLASS_ANALYSIS doctrine tags. The bridge's per-target preview must
        reproduce that exactly (preview == resolution) — this asserts
        against an INDEPENDENT call to compute_consciousness_delta built to
        mirror resolve_educate's own signature (doctrine passed), not
        against _preview_consciousness_delta itself, so it would have FAILED
        before the fix (the old preview omitted doctrine and understated the
        delta)."""
        from babylon.config.defines import GameDefines
        from babylon.models.enums import ActionType
        from babylon.ooda.action_effects import compute_consciousness_delta

        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.update_node("org-player", doctrine_tags={"class_analysis": 5.0})

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_educate_targets(uuid.uuid4(), "org-player")

        target = result["targets"][0]
        defines = GameDefines()
        org_attrs = dict(graph.nodes["org-player"])

        # Mirrors resolve_educate's own resolve_action(..., doctrine=...) call exactly.
        with_doctrine = compute_consciousness_delta(
            org_attrs,
            "sc-genesee-proles",
            ActionType.EDUCATE,
            graph,
            defines.ooda,
            defines.organization,
            defines.doctrine,
        )
        expected = round(float(with_doctrine.collective_identity_delta), 4)  # type: ignore[union-attr]

        # Sanity: the bonus is actually engaged (not a coincidental equality) —
        # the no-doctrine baseline must be strictly smaller in magnitude.
        without_doctrine = compute_consciousness_delta(
            org_attrs,
            "sc-genesee-proles",
            ActionType.EDUCATE,
            graph,
            defines.ooda,
            defines.organization,
        )
        baseline = round(float(without_doctrine.collective_identity_delta), 4)  # type: ignore[union-attr]
        assert abs(expected) > abs(baseline)

        assert target["expected_deltas"]["consciousness_delta"] == expected

    def test_aid_row_omits_theory_bonus_even_for_class_analysis_org(self) -> None:
        """Guard against OVER-stating AID: resolve_aid calls
        compute_consciousness_delta directly WITHOUT doctrine (it defaults to
        None), so even an acting org with CLASS_ANALYSIS doctrine tags must
        NOT receive the Step-7.5 bonus on its AID preview. Asserts against an
        independent call mirroring resolve_aid's own (no-doctrine) signature."""
        from babylon.config.defines import GameDefines
        from babylon.models.enums import ActionType
        from babylon.ooda.action_effects import compute_consciousness_delta

        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.update_node("org-player", doctrine_tags={"class_analysis": 5.0})

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_aid_targets(uuid.uuid4(), "org-player")

        pop = result["population_targets"][0]
        defines = GameDefines()
        org_attrs = dict(graph.nodes["org-player"])

        # Mirrors resolve_aid's own compute_consciousness_delta call exactly
        # (no doctrine argument at all).
        no_bonus = compute_consciousness_delta(
            org_attrs,
            pop["community_id"],
            ActionType.PROVIDE_SERVICE,
            graph,
            defines.ooda,
            defines.organization,
        )
        expected = round(float(no_bonus.collective_identity_delta), 4)  # type: ignore[union-attr]

        assert pop["expected_deltas"]["consciousness_delta"] == expected

    def test_preview_action_campaign_also_includes_doctrine_theory_bonus(self) -> None:
        """Scope-extension discovered during the Task-18 review fix:
        resolve_campaign (CAMPAIGN/PROPAGANDIZE) calls
        resolve_action(..., doctrine=services.defines.doctrine) exactly like
        resolve_educate, so the shared preview_action() endpoint (the third
        _preview_consciousness_delta call site, gated on
        ``verb in {"educate", "campaign", "aid"}``) must apply the same
        Step-7.5 doctrine bonus for CAMPAIGN too — not just EDUCATE — or its
        estimate would understate resolution identically to the reported
        EDUCATE bug."""
        from babylon.config.defines import GameDefines
        from babylon.models.enums import ActionType
        from babylon.ooda.action_effects import compute_consciousness_delta

        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        graph = _make_balkanization_graph()
        graph.update_node("org-player", doctrine_tags={"class_analysis": 5.0})

        with _patched_hydrate_state(bridge, graph):
            result = bridge.preview_action(
                uuid.uuid4(), "org-player", "campaign", "sc-genesee-proles"
            )

        defines = GameDefines()
        org_attrs = dict(graph.nodes["org-player"])

        # Mirrors resolve_campaign's own resolve_action(..., doctrine=...) call.
        with_doctrine = compute_consciousness_delta(
            org_attrs,
            "sc-genesee-proles",
            ActionType.PROPAGANDIZE,
            graph,
            defines.ooda,
            defines.organization,
            defines.doctrine,
        )
        # preview_action rounds its estimate to 4 places before returning.
        expected = round(float(with_doctrine.collective_identity_delta), 4)  # type: ignore[union-attr]

        without_doctrine = compute_consciousness_delta(
            org_attrs,
            "sc-genesee-proles",
            ActionType.PROPAGANDIZE,
            graph,
            defines.ooda,
            defines.organization,
        )
        baseline = round(float(without_doctrine.collective_identity_delta), 4)  # type: ignore[union-attr]
        assert abs(expected) > abs(baseline)

        assert result["estimated_consciousness_delta"] == expected


@pytest.mark.unit
class TestEconomyDashboardChipContract:
    """spec-116 4d.6: the payload key set is PINNED so a phantom chip
    (TS-declared, never-emitted) can never return. Corrected audit figures:
    all fields are emitted today; the tick-26 dead chips were pre-boundary
    honesty (profit_rate/occ) on an un-migrated DB, not phantoms."""

    def test_dashboard_emits_exactly_the_declared_key_set(self) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_economy_dashboard(uuid.uuid4())

        assert set(result.keys()) == {
            "tick",
            "has_data",
            "value_produced",
            "rent_extracted",
            "exploitation_rate",
            "profit_rate",
            "occ",
            "imperial_rent_pool",
            "current_super_wage_rate",
            "wage_flow_total",
            "tribute_flow_total",
            "wealth_by_class_role",
            "county_flow",
            "imperial_rent_gap",
            "imperial_rent_gap_by_region",
            "veil",
        }, (
            "EconomyDashboardPayload drifted — update types/game.ts, the "
            "chips, and this pin in the SAME commit (no phantoms, no orphans)"
        )


@pytest.mark.unit
class TestEconomyDashboardVeil:
    """T2-8/T2-9 (spec-117 §5d, D7): ``veil`` is computed from the player
    org's REAL ``acquired_doctrine_ids`` (not a mock resolver — I-7 lesson
    from ``test_doctrine_tree_endpoint.py``), and the two value-axis fields
    it carries are ``None`` below Tier 1, never a fabricated number a client
    could read regardless of tier (the same "enforced at serialization"
    boundary the fog uses)."""

    @staticmethod
    def _state_with_acquired(acquired: tuple[str, ...]) -> Any:
        state = _build_initial_state_for_scenario("default")
        org = state.organizations["ORG001"].model_copy(update={"acquired_doctrine_ids": acquired})
        return state.model_copy(update={"organizations": {"ORG001": org}})

    def _dashboard_with_acquired(self, acquired: tuple[str, ...]) -> dict[str, Any]:
        state = self._state_with_acquired(acquired)
        bridge = EngineBridge(_make_mock_persistence())
        with patch.object(bridge, "hydrate_state", return_value=(state, state.to_graph())):
            return bridge.get_economy_dashboard(uuid.uuid4())

    def test_no_player_org_is_tier_zero(self) -> None:
        state = _build_initial_state_for_scenario("default").model_copy(
            update={"organizations": {}, "player_org_id": None}
        )
        bridge = EngineBridge(_make_mock_persistence())
        with patch.object(bridge, "hydrate_state", return_value=(state, state.to_graph())):
            result = bridge.get_economy_dashboard(uuid.uuid4())

        assert result["veil"]["tier"] == 0
        assert result["veil"]["next_unlock_node_id"] == "class_consciousness"
        assert result["veil"]["next_unlock_label"] == "Class Consciousness"
        assert result["veil"]["value_produced"] is None
        assert result["veil"]["exploitation_rate"] is None

    def test_empty_acquired_is_tier_zero(self) -> None:
        result = self._dashboard_with_acquired(())

        assert result["veil"]["tier"] == 0
        assert result["veil"]["value_produced"] is None
        assert result["veil"]["exploitation_rate"] is None

    def test_tier1_node_acquired_unlocks_the_value_axis(self) -> None:
        result = self._dashboard_with_acquired(("class_consciousness",))

        assert result["veil"]["tier"] == 1
        assert result["veil"]["next_unlock_node_id"] == "trade_unionism"
        assert result["veil"]["next_unlock_label"] == "Trade Unionism"
        # Real numbers, not a copy fabricated independently of the actual
        # aggregate — must equal the legacy (always-live) top-level fields.
        assert result["veil"]["value_produced"] == result["value_produced"]
        assert result["veil"]["exploitation_rate"] == result["exploitation_rate"]

    def test_both_nodes_acquired_is_tier_two_with_no_next_unlock(self) -> None:
        result = self._dashboard_with_acquired(("class_consciousness", "trade_unionism"))

        assert result["veil"]["tier"] == 2
        assert result["veil"]["next_unlock_node_id"] is None
        assert result["veil"]["next_unlock_label"] is None
        assert result["veil"]["value_produced"] == result["value_produced"]
        assert result["veil"]["exploitation_rate"] == result["exploitation_rate"]

    def test_legacy_top_level_fields_are_veiled_too(self) -> None:
        """G4: the audit found the legacy top-level ``value_produced``/
        ``exploitation_rate`` fields (EconomyDashboard/BottomDrawer's
        pre-existing surface) leaking the real numbers ungated below Tier 1
        — only the new ``veil.*`` copies were gated (Wave 2B). Closed: the
        top-level fields are now gated by the exact same tier, so no client
        inspection of the wire response can pierce the veil regardless of
        which field name it reads."""
        result = self._dashboard_with_acquired(())

        assert result["value_produced"] is None
        assert result["exploitation_rate"] is None
        assert result["rent_extracted"] is None
        assert result["profit_rate"] is None
        assert result["occ"] is None
        assert result["imperial_rent_pool"] is None
        assert result["imperial_rent_gap"] is None
        assert result["imperial_rent_gap_by_region"] == []

    def test_legacy_top_level_fields_unlock_at_tier_one(self) -> None:
        """The flip side of the gate: at Tier 1, the legacy top-level
        fields carry the SAME real numbers ``veil.*`` does — gating never
        forks the two into disagreeing values."""
        result = self._dashboard_with_acquired(("class_consciousness",))

        assert result["value_produced"] == result["veil"]["value_produced"]
        assert result["exploitation_rate"] == result["veil"]["exploitation_rate"]
        assert isinstance(result["value_produced"], float)
        assert isinstance(result["exploitation_rate"], float)


@pytest.mark.unit
class TestSpineWhitelistSeverityAndTitles:
    """spec-116 FR-116-4.7 sweep: severity tiers + humanized titles for the
    14 newly wired types (FR-116-2 reserves critical for genuine
    rupture/endgame proximity; secession IS fragmented-collapse proximity)."""

    @pytest.mark.parametrize(
        ("event_type", "expected"),
        [
            ("market_correction", "warning"),
            ("entity_death", "warning"),
            ("population_attrition", "informational"),
            ("crisis_phase_transition", "warning"),
            ("bifurcation_threshold", "warning"),
            ("edge_mode_transition", "informational"),
            ("co_optive_breakdown", "warning"),
            ("latent_contradiction_release", "informational"),
            ("aspect_reversal", "informational"),
            ("level_transition", "warning"),
            ("secession_declared", "critical"),
            ("calibration_warning.axiom_violation", "informational"),
            ("calibration_warning.qcew_carry_forward", "informational"),
            ("calibration_warning.phi_hour_outlier", "informational"),
        ],
    )
    def test_severity(self, event_type: str, expected: str) -> None:
        from game.engine_bridge import _classify_event

        assert _classify_event(event_type) == expected

    @pytest.mark.parametrize(
        ("event_type", "expected"),
        [
            # Overrides — dotted/hyphenated values the naive title() mangles,
            # plus the one player-facing rename.
            ("co_optive_breakdown", "Co-optive Breakdown"),
            ("calibration_warning.axiom_violation", "Calibration: Axiom Violation"),
            ("calibration_warning.qcew_carry_forward", "Calibration: QCEW Carry-Forward"),
            ("calibration_warning.phi_hour_outlier", "Calibration: Phi-Hour Outlier"),
            ("entity_death", "Class Extinction"),
            # Default humanization still applies to everything else.
            ("market_correction", "Market Correction"),
            ("secession_declared", "Secession Declared"),
            ("pogrom", "Pogrom"),
        ],
    )
    def test_humanized_titles(self, event_type: str, expected: str) -> None:
        from game.engine_bridge import _humanize_event_type

        assert _humanize_event_type(event_type) == expected


@pytest.mark.requires_reference_db
class TestBridgeEconomicsOverridesWiresCirculationAndFinancialServices:
    """spec-116 Task 20b: wire the FRED-backed circulation + financial services
    into ``_bridge_economics_overrides``, mirroring the
    ``throughput_calculator`` wiring pattern (``test_throughput_wiring.py``).

    Without ``turnover_profile_source``/``interest_calculator`` wired,
    ``domain/economics/tick/system/__init__.py``'s ``_compute_circulation_layer``
    (:1167) and ``_compute_financial_layer`` (:1365) no-op unconditionally, so
    the Group C (7 fields) and Group D (9 fields) territory attrs stay at their
    write-site fallback constants forever. Both factories
    (``create_circulation_services``/``create_financial_services``) read the
    same reference-DB ``session_factory`` already in scope for melt/gamma/
    leontief/throughput above — no new runtime dependency.
    """

    def test_overrides_include_a_real_turnover_profile_source(self) -> None:
        from babylon.domain.economics.circulation.turnover import DefaultTurnoverProfileSource
        from game.engine_bridge import _bridge_economics_overrides

        overrides, leontief_session = _bridge_economics_overrides(())
        try:
            assert "turnover_profile_source" in overrides
            assert isinstance(overrides["turnover_profile_source"], DefaultTurnoverProfileSource)
        finally:
            if leontief_session is not None:
                leontief_session.close()

    def test_overrides_include_a_real_interest_calculator(self) -> None:
        from babylon.domain.economics.credit.interest import DefaultInterestCalculator
        from game.engine_bridge import _bridge_economics_overrides

        overrides, leontief_session = _bridge_economics_overrides(())
        try:
            assert "interest_calculator" in overrides
            assert isinstance(overrides["interest_calculator"], DefaultInterestCalculator)
        finally:
            if leontief_session is not None:
                leontief_session.close()

    def test_overrides_include_inventory_and_depreciation_data_sources(self) -> None:
        """Group C's other two circulation adapters ride the same wiring call."""
        from game.engine_bridge import _bridge_economics_overrides

        overrides, leontief_session = _bridge_economics_overrides(())
        try:
            assert overrides.get("inventory_data_source") is not None
            assert overrides.get("depreciation_data_source") is not None
        finally:
            if leontief_session is not None:
                leontief_session.close()

    def test_overrides_thread_defines_into_housing_calculator(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Honesty sweep (U2.4): ``_bridge_economics_overrides`` resolves its
        own ``defines = GameDefines.load_default()`` (already threaded into
        ``create_leontief_rent_services`` above) but previously dropped it
        from the ``create_financial_services(fred_series_cache=fred_cache)``
        call — ``housing_calculator``'s interest rate silently reverted to a
        SECOND, independent ``GameDefines.load_default()`` call inside the
        factory instead of the one this function (and thus this session)
        actually resolved.

        ``GameDefines.load_default`` is monkeypatched to return a DIFFERENT
        value on its second call — a plain single fixed return would pass
        whether or not the fix is applied (``create_financial_services``'s
        own internal fallback is also ``GameDefines.load_default()``, so a
        constant stub can't distinguish "reused the resolved defines" from
        "fell back to a second independent load"). Only the fix (threading
        the already-resolved ``defines`` through directly, avoiding a
        second call) keeps the housing rate at the first call's value.
        """
        from babylon.config.defines import CapitalVolumeIIIDefines, GameDefines
        from game.engine_bridge import _bridge_economics_overrides

        custom_defines = GameDefines(
            capital_vol3=CapitalVolumeIIIDefines(housing_capitalization_rate_default=0.12)
        )
        call_count = {"n": 0}

        def _fake_load_default(cls: type[GameDefines]) -> GameDefines:
            call_count["n"] += 1
            return custom_defines if call_count["n"] == 1 else GameDefines()

        monkeypatch.setattr(GameDefines, "load_default", classmethod(_fake_load_default))

        overrides, leontief_session = _bridge_economics_overrides(())
        try:
            housing_calc = overrides.get("housing_calculator")
            assert housing_calc is not None
            assert housing_calc._interest_rate == 0.12, (
                "housing_calculator._interest_rate reverted to a SECOND, "
                "independent GameDefines.load_default() call instead of "
                "reusing the defines this function already resolved"
            )
        finally:
            if leontief_session is not None:
                leontief_session.close()


@pytest.mark.requires_reference_db
class TestBridgeEconomicsOverridesWiresVol1ReserveArmyServices:
    """spec-116 Task 21b: wire the FRED-backed Vol I production layer
    (Feature 021 — reserve army, productivity, dispossession) into
    ``_bridge_economics_overrides``, mirroring the headless runner's
    ``create_vol1_services``/``load_vol1_series_from_db`` wiring
    (``engine/simulation/_legacy.py:305-316``).

    Without ``reserve_army_data_source`` wired, ``domain/economics/tick/
    system/__init__.py``'s ``_compute_vol1_layer`` (:1100) returns
    ``county_states`` unchanged unconditionally, so the wage-pressure
    sigmoid never compresses ``median_wage`` tick-over-tick in a web
    session — only the QCEW bootstrap value it starts from is real.
    ``create_vol1_services`` reads the same reference-DB ``session_factory``
    already in scope for melt/gamma/leontief/throughput/circulation/
    financial above — no new runtime dependency.
    """

    def test_overrides_include_a_reserve_army_data_source(self) -> None:
        from game.engine_bridge import _bridge_economics_overrides

        overrides, leontief_session = _bridge_economics_overrides(())
        try:
            source = overrides.get("reserve_army_data_source")
            assert source is not None
            assert hasattr(source, "get_unemployment_decomposition")
            assert callable(source.get_unemployment_decomposition)
        finally:
            if leontief_session is not None:
                leontief_session.close()

    def test_overrides_include_productivity_and_dispossession_data_sources(self) -> None:
        """The other two Vol I adapters ride the same wiring call (mirrors
        the headless runner's ``.update(vol1_overrides)`` faithfully — see
        the FLAG discussion in the Task 21b brief: ``productivity_data_source``
        has zero tick readers anywhere in ``src/`` today, and
        ``dispossession_data_source``'s one reader
        (``_simulate_transitions``, :1757) is itself gated on an unwired
        ``transition_engine`` (:1736), so both ride along inert — wiring the
        whole bundle is faithful to the headless mirror without widening the
        web session's live blast radius beyond reserve-army wage pressure.
        """
        from game.engine_bridge import _bridge_economics_overrides

        overrides, leontief_session = _bridge_economics_overrides(())
        try:
            assert overrides.get("productivity_data_source") is not None
            assert overrides.get("dispossession_data_source") is not None
        finally:
            if leontief_session is not None:
                leontief_session.close()


class TestGroupCDDocstringsHonest:
    """Honesty sweep (U2, Row K): the 'both gating services are unwired'
    claim was false for 8 of 9 Group C/D rows."""

    def test_carry_tick_dynamics_flows_comment_corrected(self) -> None:
        import inspect

        from game.engine_bridge import _carry_tick_dynamics_flows

        source = inspect.getsource(_carry_tick_dynamics_flows)
        assert "both gating services are unwired" not in source
        assert "CORRECTED 2026-07-18" in source

    def test_serialize_territory_docstring_corrected(self) -> None:
        import inspect

        doc = _serialize_territory.__doc__ or ""
        assert "both gating services are unwired" not in doc
        assert "CORRECTED 2026-07-18" in doc
        source = inspect.getsource(_serialize_territory)
        assert "until turnover_profile_source /" not in source


# Catalog docstring tests: NONE IN THIS TASK.
# U5.3's TestCatalogDocstringAccuracy is authoritative — it pins the
# docstring against build_default_registry().keys, so it cannot go stale
# again at 6 OR at 10. A hardcoded "six bound contradictions" assertion
# here would red the moment U5.2 grows the registry to ten.


class TestMobilizeTargetsIncludeSeededBusinesses:
    """ADR086: the QCEW-seeded ``Business`` NPCs surface as real MOBILIZE
    targets in a ``us_nationwide`` session -- ``get_mobilize_targets`` walks the
    player org's territories and returns the business/civil_society orgs sharing
    them, so the businesses seeded into the player's HQ hexes are targetable."""

    def test_us_nationwide_businesses_are_mobilize_targets(self) -> None:
        from babylon.engine.scenarios import create_us_scenario
        from babylon.engine.scenarios.business_seeds import build_seeded_businesses

        state, _config, _defines = create_us_scenario()
        graph = state.to_graph()
        bridge = EngineBridge(_make_mock_persistence())

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_mobilize_targets(uuid.uuid4(), state.player_org_id)

        target_ids = {t["id"] for t in result["targets"]}
        seeded_ids = set(build_seeded_businesses("US", []))
        # Every seeded business shares the player's HQ territories, so all are
        # reachable as MOBILIZE targets (not merely a non-empty intersection).
        assert seeded_ids, "no businesses seeded"
        assert seeded_ids <= target_ids, (
            f"seeded businesses missing from MOBILIZE targets: {seeded_ids - target_ids}"
        )

    def test_targeted_businesses_carry_real_names_and_type(self) -> None:
        from babylon.engine.scenarios import create_us_scenario
        from babylon.engine.scenarios.business_seeds import build_seeded_businesses

        state, _config, _defines = create_us_scenario()
        graph = state.to_graph()
        bridge = EngineBridge(_make_mock_persistence())

        with _patched_hydrate_state(bridge, graph):
            result = bridge.get_mobilize_targets(uuid.uuid4(), state.player_org_id)

        by_id = {t["id"]: t for t in result["targets"]}
        for biz_id, biz in build_seeded_businesses("US", []).items():
            assert by_id[biz_id]["name"] == biz.name
            assert by_id[biz_id]["type"] == "BUSINESS"
