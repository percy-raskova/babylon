"""Unit tests for SessionRecorder observer.

Tests the SessionRecorder's ability to persist simulation state to SQLite
for replay, debugging, and temporal queries (ADR030).
"""

from __future__ import annotations

import pytest
from tests.factories import DomainFactory

from babylon.data.simulation import SimulationDB
from babylon.engine.observers.session_recorder import SessionRecorder
from babylon.models.config import SimulationConfig


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


class TestSessionRecorderCreation:
    """Tests for SessionRecorder instantiation."""

    def test_creates_with_database(self) -> None:
        """Should create recorder with database reference."""
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            assert recorder._db is db
            assert recorder._started is False

    def test_name_includes_run_id(self) -> None:
        """name property should include the database run_id."""
        with SimulationDB(run_id="test_run_123", in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            assert "test_run_123" in recorder.name


class TestSessionRecorderProtocol:
    """Tests for SimulationObserver protocol compliance."""

    def test_has_required_methods(self) -> None:
        """Should implement all SimulationObserver protocol methods."""
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
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
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            state = _create_world_state()
            config = _create_config()

            assert recorder._started is False
            recorder.on_simulation_start(state, config)
            assert recorder._started is True

    def test_stores_config_metadata(self) -> None:
        """Should store simulation config as metadata."""
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            state = _create_world_state()
            config = _create_config()

            recorder.on_simulation_start(state, config)

            metadata = db.get_metadata("config")
            assert metadata is not None
            assert "extraction_efficiency" in metadata  # Config should be serialized

    def test_stores_start_tick_metadata(self) -> None:
        """Should store starting tick as metadata."""
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            state = _create_world_state()
            config = _create_config()

            recorder.on_simulation_start(state, config)

            start_tick = db.get_metadata("start_tick")
            assert start_tick == str(state.tick)

    def test_records_initial_state(self) -> None:
        """Should record initial tick_summary."""
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            state = _create_world_state()
            config = _create_config()

            recorder.on_simulation_start(state, config)

            # Check tick_summary was recorded
            result = db.con.execute(
                "SELECT tick FROM tick_summary WHERE tick = ?", (state.tick,)
            ).fetchone()
            assert result is not None


class TestOnTick:
    """Tests for on_tick callback."""

    def test_records_tick_summary(self) -> None:
        """Should record tick_summary for each tick."""
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            initial = _create_world_state()
            config = _create_config()
            next_state = initial.model_copy(update={"tick": initial.tick + 1})

            recorder.on_simulation_start(initial, config)
            recorder.on_tick(initial, next_state)

            # Check both ticks recorded
            result = db.con.execute("SELECT COUNT(*) FROM tick_summary").fetchone()
            assert result is not None
            assert result[0] == 2

    def test_warns_if_not_started(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log warning if called before start."""
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            state = _create_world_state()

            # Call on_tick without on_simulation_start
            recorder.on_tick(state, state)

            assert "before on_simulation_start" in caplog.text


class TestOnSimulationEnd:
    """Tests for on_simulation_end callback."""

    def test_stores_end_tick_metadata(self) -> None:
        """Should store ending tick as metadata."""
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            initial = _create_world_state()
            config = _create_config()
            final_state = initial.model_copy(update={"tick": 100})

            recorder.on_simulation_start(initial, config)
            recorder.on_simulation_end(final_state)

            end_tick = db.get_metadata("end_tick")
            assert end_tick == "100"

    def test_sets_completed_status(self) -> None:
        """Should set status to completed."""
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            initial = _create_world_state()
            config = _create_config()

            recorder.on_simulation_start(initial, config)
            assert db.get_metadata("status") == "running"

            recorder.on_simulation_end(initial)
            assert db.get_metadata("status") == "completed"


class TestEntityRecording:
    """Tests for entity state recording."""

    def test_records_entity_states(self) -> None:
        """Should record entity states to agent_state table."""
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            state = _create_world_state()
            config = _create_config()

            recorder.on_simulation_start(state, config)

            # Check entities recorded
            result = db.con.execute("SELECT COUNT(*) FROM agent_state").fetchone()
            assert result is not None
            # Should have at least the entities from minimal world state
            assert result[0] >= len(state.entities)


class TestRelationshipRecording:
    """Tests for relationship state recording."""

    def test_records_relationships(self) -> None:
        """Should record relationships to network_edge table."""
        with SimulationDB(in_memory=True, attach_reference=False) as db:
            recorder = SessionRecorder(db)
            state = _create_world_state()
            config = _create_config()

            recorder.on_simulation_start(state, config)

            # Check relationships recorded
            result = db.con.execute("SELECT COUNT(*) FROM network_edge").fetchone()
            assert result is not None
            assert result[0] >= len(state.relationships)
