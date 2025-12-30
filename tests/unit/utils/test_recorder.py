"""Tests for SessionRecorder - Black Box recording for DPG Dashboard.

TDD Tests - Written BEFORE implementation (RED phase).
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from babylon.engine.observer import SimulationObserver
from babylon.models.enums import EventType
from babylon.models.events import ExtractionEvent
from babylon.models.metrics import EntityMetrics, TickMetrics
from babylon.models.types import Currency, Probability

if TYPE_CHECKING:
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_session_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for session recording."""
    return tmp_path / "sessions"


@pytest.fixture
def mock_metrics_collector() -> Mock:
    """Create a mock MetricsCollector with sample TickMetrics."""
    collector = Mock()
    collector.history = [
        TickMetrics(
            tick=1,
            p_w=EntityMetrics(
                wealth=Currency(100.0),
                consciousness=Probability(0.3),
                national_identity=Probability(0.5),
                agitation=Probability(0.2),
                p_acquiescence=Probability(0.7),
                p_revolution=Probability(0.3),
                organization=Probability(0.1),
            ),
            imperial_rent_pool=Currency(500.0),
            global_tension=Probability(0.4),
        ),
    ]
    return collector


@pytest.fixture
def mock_narrative_director() -> Mock:
    """Create a mock NarrativeDirector with sample narratives."""
    director = Mock()
    director.narrative_log = [
        "The workers grow restless as imperial rent extraction continues.",
        "Consciousness spreads through solidarity networks.",
    ]
    return director


@pytest.fixture
def mock_world_state() -> Mock:
    """Create a mock WorldState with sample events."""
    state = Mock()
    state.tick = 1
    state.events = [
        ExtractionEvent(
            event_type=EventType.SURPLUS_EXTRACTION,
            tick=1,
            timestamp=datetime.now(),
            source_id="C001",
            target_id="C003",
            amount=Currency(50.0),
            mechanism="imperial_rent",
        ),
    ]
    return state


@pytest.fixture
def mock_config() -> Mock:
    """Create a mock SimulationConfig."""
    config = Mock()
    config.max_ticks = 100
    return config


# =============================================================================
# Test: Observer Protocol Compliance
# =============================================================================


@pytest.mark.unit
class TestObserverProtocol:
    """Verify SessionRecorder implements SimulationObserver protocol."""

    def test_recorder_implements_observer_protocol(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
    ) -> None:
        """SessionRecorder should satisfy SimulationObserver protocol."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        # Check protocol compliance
        assert isinstance(recorder, SimulationObserver)
        assert hasattr(recorder, "name")
        assert hasattr(recorder, "on_simulation_start")
        assert hasattr(recorder, "on_tick")
        assert hasattr(recorder, "on_simulation_end")

    def test_recorder_name_property(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
    ) -> None:
        """SessionRecorder.name should return identifier string."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        assert recorder.name == "SessionRecorder"


# =============================================================================
# Test: Session Directory Creation
# =============================================================================


@pytest.mark.unit
class TestSessionDirectoryCreation:
    """Verify session directory creation on simulation start."""

    def test_recorder_creates_session_directory(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """on_simulation_start should create timestamped session directory."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        recorder.on_simulation_start(mock_world_state, mock_config)

        # Verify directory was created
        assert temp_session_dir.exists()
        session_dirs = list(temp_session_dir.iterdir())
        assert len(session_dirs) == 1

        # Verify timestamp format (YYYYMMDD-HHMMSS)
        session_dir = session_dirs[0]
        assert session_dir.is_dir()
        # Should match pattern like "20251230-163045"
        assert len(session_dir.name) == 15
        assert session_dir.name[8] == "-"

    def test_recorder_creates_jsonl_files(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """on_simulation_start should create empty JSONL files."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        recorder.on_simulation_start(mock_world_state, mock_config)

        session_dir = list(temp_session_dir.iterdir())[0]
        assert (session_dir / "metrics.jsonl").exists()
        assert (session_dir / "events.jsonl").exists()
        assert (session_dir / "narrative.jsonl").exists()


# =============================================================================
# Test: Metrics Logging
# =============================================================================


@pytest.mark.unit
class TestMetricsLogging:
    """Verify TickMetrics are logged to metrics.jsonl."""

    def test_recorder_logs_metrics_to_jsonl(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """on_tick should write TickMetrics as JSON line."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        # Simulate lifecycle
        recorder.on_simulation_start(mock_world_state, mock_config)
        recorder.on_tick(mock_world_state, mock_world_state)
        recorder.on_simulation_end(mock_world_state)

        # Read and verify metrics.jsonl
        session_dir = list(temp_session_dir.iterdir())[0]
        metrics_file = session_dir / "metrics.jsonl"
        lines = metrics_file.read_text().strip().split("\n")

        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["tick"] == 1
        assert data["imperial_rent_pool"] == 500.0

    def test_recorder_logs_multiple_ticks(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """Multiple ticks should append multiple JSON lines."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        recorder.on_simulation_start(mock_world_state, mock_config)

        # Simulate 3 ticks with updated metrics
        for tick in range(1, 4):
            mock_metrics_collector.history.append(
                TickMetrics(
                    tick=tick,
                    imperial_rent_pool=Currency(500.0 + tick * 10),
                    global_tension=Probability(0.4),
                )
            )
            mock_world_state.tick = tick
            recorder.on_tick(mock_world_state, mock_world_state)

        recorder.on_simulation_end(mock_world_state)

        # Verify 3 lines written (initial + 3 appended = 4 total history items)
        session_dir = list(temp_session_dir.iterdir())[0]
        metrics_file = session_dir / "metrics.jsonl"
        lines = metrics_file.read_text().strip().split("\n")

        assert len(lines) == 3


# =============================================================================
# Test: Events Logging
# =============================================================================


@pytest.mark.unit
class TestEventsLogging:
    """Verify SimulationEvents are logged to events.jsonl."""

    def test_recorder_logs_events_to_jsonl(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """on_tick should write events as JSON lines."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        recorder.on_simulation_start(mock_world_state, mock_config)
        recorder.on_tick(mock_world_state, mock_world_state)
        recorder.on_simulation_end(mock_world_state)

        # Read and verify events.jsonl
        session_dir = list(temp_session_dir.iterdir())[0]
        events_file = session_dir / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")

        assert len(lines) == 1
        data = json.loads(lines[0])
        # Event type is lowercase in JSON (enum value serialization)
        assert data["event_type"] == "surplus_extraction"
        assert data["source_id"] == "C001"
        assert data["target_id"] == "C003"

    def test_recorder_handles_empty_events(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """on_tick should handle ticks with no events gracefully."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        # Clear events
        mock_world_state.events = []

        recorder.on_simulation_start(mock_world_state, mock_config)
        recorder.on_tick(mock_world_state, mock_world_state)
        recorder.on_simulation_end(mock_world_state)

        # events.jsonl should be empty
        session_dir = list(temp_session_dir.iterdir())[0]
        events_file = session_dir / "events.jsonl"
        content = events_file.read_text().strip()

        assert content == ""


# =============================================================================
# Test: Narrative Logging
# =============================================================================


@pytest.mark.unit
class TestNarrativeLogging:
    """Verify narratives are logged to narrative.jsonl."""

    def test_recorder_logs_narratives_to_jsonl(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_narrative_director: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """on_tick should write narratives as JSON lines with tick."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            narrative_director=mock_narrative_director,
            base_dir=temp_session_dir,
        )

        recorder.on_simulation_start(mock_world_state, mock_config)
        recorder.on_tick(mock_world_state, mock_world_state)
        recorder.on_simulation_end(mock_world_state)

        # Read and verify narrative.jsonl
        session_dir = list(temp_session_dir.iterdir())[0]
        narrative_file = session_dir / "narrative.jsonl"
        lines = narrative_file.read_text().strip().split("\n")

        assert len(lines) == 2
        data0 = json.loads(lines[0])
        assert data0["tick"] == 1
        assert "workers grow restless" in data0["text"]

    def test_recorder_handles_no_narrative_director(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """SessionRecorder should work without NarrativeDirector."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            narrative_director=None,
            base_dir=temp_session_dir,
        )

        recorder.on_simulation_start(mock_world_state, mock_config)
        recorder.on_tick(mock_world_state, mock_world_state)
        recorder.on_simulation_end(mock_world_state)

        # narrative.jsonl should exist but be empty
        session_dir = list(temp_session_dir.iterdir())[0]
        narrative_file = session_dir / "narrative.jsonl"
        content = narrative_file.read_text().strip()

        assert content == ""

    def test_recorder_avoids_duplicate_narratives(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_narrative_director: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """on_tick should not write the same narrative twice."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            narrative_director=mock_narrative_director,
            base_dir=temp_session_dir,
        )

        recorder.on_simulation_start(mock_world_state, mock_config)

        # First tick writes both narratives
        recorder.on_tick(mock_world_state, mock_world_state)

        # Second tick - no new narratives
        mock_world_state.tick = 2
        recorder.on_tick(mock_world_state, mock_world_state)

        recorder.on_simulation_end(mock_world_state)

        # Should still only have 2 lines (not 4)
        session_dir = list(temp_session_dir.iterdir())[0]
        narrative_file = session_dir / "narrative.jsonl"
        lines = narrative_file.read_text().strip().split("\n")

        assert len(lines) == 2


# =============================================================================
# Test: Simulation End
# =============================================================================


@pytest.mark.unit
class TestSimulationEnd:
    """Verify cleanup and summary on simulation end."""

    def test_recorder_writes_summary_json(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """on_simulation_end should write summary.json."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        mock_world_state.tick = 42

        recorder.on_simulation_start(mock_world_state, mock_config)
        recorder.on_simulation_end(mock_world_state)

        session_dir = list(temp_session_dir.iterdir())[0]
        summary_file = session_dir / "summary.json"

        assert summary_file.exists()
        data = json.loads(summary_file.read_text())
        assert data["final_tick"] == 42
        assert "ended_at" in data


# =============================================================================
# Test: Export Package
# =============================================================================


@pytest.mark.unit
class TestExportPackage:
    """Verify ZIP export functionality."""

    def test_export_package_creates_zip(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """export_package should create a ZIP file."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        recorder.on_simulation_start(mock_world_state, mock_config)
        recorder.on_tick(mock_world_state, mock_world_state)

        zip_path = recorder.export_package()

        assert zip_path.exists()
        assert zip_path.suffix == ".zip"
        assert "babylon-debug" in zip_path.name

    def test_export_package_contains_all_files(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_narrative_director: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """ZIP should contain all session files."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            narrative_director=mock_narrative_director,
            base_dir=temp_session_dir,
        )

        recorder.on_simulation_start(mock_world_state, mock_config)
        recorder.on_tick(mock_world_state, mock_world_state)
        recorder.on_simulation_end(mock_world_state)

        zip_path = recorder.export_package()

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "metrics.jsonl" in names
            assert "events.jsonl" in names
            assert "narrative.jsonl" in names
            assert "summary.json" in names

    def test_export_package_raises_without_session(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
    ) -> None:
        """export_package should raise if no session started."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        with pytest.raises(RuntimeError, match="No session to export"):
            recorder.export_package()

    def test_export_package_returns_path(
        self,
        temp_session_dir: Path,
        mock_metrics_collector: Mock,
        mock_world_state: Mock,
        mock_config: Mock,
    ) -> None:
        """export_package should return Path to ZIP file."""
        from babylon.utils.recorder import SessionRecorder

        recorder = SessionRecorder(
            metrics_collector=mock_metrics_collector,
            base_dir=temp_session_dir,
        )

        recorder.on_simulation_start(mock_world_state, mock_config)

        result = recorder.export_package()

        assert isinstance(result, Path)
        assert result.is_file()
