"""Unit tests for SessionRecorder observer (Feature 037 migration).

Tests the SessionRecorder's ability to persist simulation state via
the RuntimePersistence protocol for replay, debugging, and temporal
queries (ADR030 + Feature 037).
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock
from uuid import UUID

from tests.factories import DomainFactory

from babylon.engine.observers.session_recorder import SessionRecorder
from babylon.models.config import SimulationConfig
from babylon.persistence.protocols import RuntimePersistence, TraceCollector, TraceLevel

_TEST_SESSION_ID = UUID("12345678-1234-5678-1234-567812345678")


def _create_world_state() -> object:
    """Create a minimal world state for testing."""
    factory = DomainFactory()
    worker = factory.create_worker()
    owner = factory.create_owner()
    relationship = factory.create_relationship(source_id=worker.id, target_id=owner.id)
    return factory.create_world_state(
        entities={worker.id: worker, owner.id: owner},
        relationships=[relationship],
    )


def _create_config() -> SimulationConfig:
    """Create a minimal simulation config for testing."""
    return SimulationConfig()


def _create_mock_persistence() -> MagicMock:
    """Create a mock RuntimePersistence backend."""
    mock = MagicMock(spec=RuntimePersistence)
    return mock


class TestSessionRecorderCreation:
    """Tests for SessionRecorder instantiation."""

    def test_creates_with_persistence(self) -> None:
        """Should create recorder with persistence reference."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        assert recorder._persistence is mock_persistence
        assert recorder._started is False

    def test_name_includes_session_id(self) -> None:
        """name property should include the session_id."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        assert str(_TEST_SESSION_ID) in recorder.name


class TestSessionRecorderProtocol:
    """Tests for SimulationObserver protocol compliance."""

    def test_has_required_methods(self) -> None:
        """Should implement all SimulationObserver protocol methods."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        # Check protocol methods exist
        assert hasattr(recorder, "name")
        assert hasattr(recorder, "on_simulation_start")
        assert hasattr(recorder, "on_tick")
        assert hasattr(recorder, "on_simulation_end")
        # Check they're callable
        assert callable(recorder.on_simulation_start)
        assert callable(recorder.on_tick)
        assert callable(recorder.on_simulation_end)


class TestOnSimulationStart:
    """Tests for on_simulation_start callback."""

    def test_sets_started_flag(self) -> None:
        """Should set _started flag when simulation begins."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        state = _create_world_state()
        config = _create_config()

        assert recorder._started is False
        recorder.on_simulation_start(state, config)
        assert recorder._started is True

    def test_stores_config_metadata(self) -> None:
        """Should store simulation config as metadata via persistence."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        state = _create_world_state()
        config = _create_config()

        recorder.on_simulation_start(state, config)

        # Verify set_metadata was called with "config"
        config_calls = [
            c for c in mock_persistence.set_metadata.call_args_list if c[0][0] == "config"
        ]
        assert len(config_calls) == 1
        config_json = config_calls[0][0][1]
        assert "extraction_efficiency" in config_json

    def test_stores_start_tick_metadata(self) -> None:
        """Should store starting tick as metadata."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        state = _create_world_state()
        config = _create_config()

        recorder.on_simulation_start(state, config)

        start_tick_calls = [
            c for c in mock_persistence.set_metadata.call_args_list if c[0][0] == "start_tick"
        ]
        assert len(start_tick_calls) == 1
        assert start_tick_calls[0][0][1] == str(state.tick)

    def test_records_initial_state(self) -> None:
        """Should call persist_tick for initial state."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        state = _create_world_state()
        config = _create_config()

        recorder.on_simulation_start(state, config)

        # persist_tick should have been called for the initial state
        assert mock_persistence.persist_tick.called
        call_kwargs = mock_persistence.persist_tick.call_args
        assert call_kwargs.kwargs.get("session_id") == _TEST_SESSION_ID


class TestOnTick:
    """Tests for on_tick callback."""

    def test_records_tick(self) -> None:
        """Should call persist_tick for each tick."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        initial = _create_world_state()
        config = _create_config()
        next_state = initial.model_copy(update={"tick": initial.tick + 1})

        recorder.on_simulation_start(initial, config)
        recorder.on_tick(initial, next_state)

        # persist_tick should have been called twice (initial + tick)
        assert mock_persistence.persist_tick.call_count == 2

    def test_warns_if_not_started(self) -> None:
        """Should not persist tick if called before start."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        state = _create_world_state()

        # Call on_tick without on_simulation_start
        recorder.on_tick(state, state)

        # persist_tick should NOT have been called
        assert not mock_persistence.persist_tick.called


class TestOnSimulationEnd:
    """Tests for on_simulation_end callback."""

    def test_stores_end_tick_metadata(self) -> None:
        """Should store ending tick as metadata."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        initial = _create_world_state()
        config = _create_config()
        final_state = initial.model_copy(update={"tick": 100})

        recorder.on_simulation_start(initial, config)
        recorder.on_simulation_end(final_state)

        end_tick_calls = [
            c for c in mock_persistence.set_metadata.call_args_list if c[0][0] == "end_tick"
        ]
        assert len(end_tick_calls) == 1
        assert end_tick_calls[0][0][1] == "100"

    def test_sets_completed_status(self) -> None:
        """Should set status to completed."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        initial = _create_world_state()
        config = _create_config()

        recorder.on_simulation_start(initial, config)

        # Check "running" was set
        running_calls = [
            c for c in mock_persistence.set_metadata.call_args_list if c[0] == ("status", "running")
        ]
        assert len(running_calls) == 1

        recorder.on_simulation_end(initial)

        # Check "completed" was set
        completed_calls = [
            c
            for c in mock_persistence.set_metadata.call_args_list
            if c[0] == ("status", "completed")
        ]
        assert len(completed_calls) == 1

    def test_flushes_tracer_on_end(self) -> None:
        """Should flush tracer when simulation ends."""
        mock_persistence = _create_mock_persistence()
        mock_tracer = MagicMock(spec=TraceCollector)
        type(mock_tracer).level = PropertyMock(return_value=TraceLevel.DEBUG)
        type(mock_tracer).buffer_size = PropertyMock(return_value=0)

        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
            tracer=mock_tracer,
        )
        initial = _create_world_state()
        config = _create_config()

        recorder.on_simulation_start(initial, config)
        recorder.on_simulation_end(initial)

        assert mock_tracer.flush.called


class TestPersistTickDelegation:
    """Tests for persist_tick delegation to RuntimePersistence."""

    def test_passes_session_id(self) -> None:
        """persist_tick should receive session_id."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        state = _create_world_state()
        config = _create_config()

        recorder.on_simulation_start(state, config)

        call_kwargs = mock_persistence.persist_tick.call_args
        assert call_kwargs.kwargs.get("session_id") == _TEST_SESSION_ID

    def test_passes_graph_from_to_graph(self) -> None:
        """persist_tick should receive the graph from state.to_graph()."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        state = _create_world_state()
        config = _create_config()

        recorder.on_simulation_start(state, config)

        call_args = mock_persistence.persist_tick.call_args
        # tick keyword arg
        assert call_args.kwargs.get("tick") == state.tick
        # graph keyword arg should be a NetworkX DiGraph
        import networkx as nx

        assert isinstance(call_args.kwargs.get("graph"), nx.DiGraph)

    def test_serializes_events(self) -> None:
        """persist_tick should receive serialized events."""
        mock_persistence = _create_mock_persistence()
        recorder = SessionRecorder(
            persistence=mock_persistence,
            session_id=_TEST_SESSION_ID,
        )
        state = _create_world_state()
        config = _create_config()

        recorder.on_simulation_start(state, config)

        call_args = mock_persistence.persist_tick.call_args
        events = call_args.kwargs.get("events")
        assert isinstance(events, list)
