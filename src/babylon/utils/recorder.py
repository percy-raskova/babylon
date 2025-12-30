"""Black box recorder for simulation forensics.

Provides persistent tick-by-tick recording of simulation state
for debugging, replay, and troubleshooting long-horizon data.

The SessionRecorder implements the SimulationObserver protocol,
automatically capturing TickMetrics, Events, and Narratives to
JSONL files in distinct session directories.

See Also:
    :mod:`babylon.engine.observer` for the SimulationObserver protocol.
    :mod:`babylon.engine.observers.metrics` for MetricsCollector.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon.ai.director import NarrativeDirector
    from babylon.engine.observers.metrics import MetricsCollector
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


class SessionRecorder:
    """Black box recorder for simulation forensics.

    Implements SimulationObserver protocol to persist tick-by-tick
    simulation state to JSONL files for debugging and replay.

    Each session creates a unique timestamped directory containing:
    - metrics.jsonl: TickMetrics snapshots (one per line)
    - events.jsonl: SimulationEvents (one per line)
    - narrative.jsonl: Narrative entries with tick numbers
    - summary.json: Session metadata on completion

    Args:
        metrics_collector: MetricsCollector observer to extract TickMetrics.
        narrative_director: Optional NarrativeDirector for narrative log.
        base_dir: Base directory for sessions (default: logs/sessions).

    Example:
        >>> from babylon.utils.recorder import SessionRecorder
        >>> recorder = SessionRecorder(metrics_collector=collector)
        >>> # Recorder is registered as observer with Simulation
        >>> # Files written automatically during simulation
        >>> zip_path = recorder.export_package()  # Create debug archive
    """

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        narrative_director: NarrativeDirector | None = None,
        base_dir: Path | None = None,
    ) -> None:
        """Initialize SessionRecorder with observer references."""
        self._metrics = metrics_collector
        self._narrative = narrative_director
        self._base_dir = base_dir or Path("logs/sessions")
        self._session_dir: Path | None = None
        self._last_narrative_idx = 0

        # File handles (opened on simulation start)
        self._metrics_file: IO[str] | None = None
        self._events_file: IO[str] | None = None
        self._narrative_file: IO[str] | None = None

    @property
    def name(self) -> str:
        """Observer identifier for logging and debugging."""
        return "SessionRecorder"

    def on_simulation_start(
        self,
        _initial_state: WorldState,
        _config: SimulationConfig,
    ) -> None:
        """Create session directory and open file handles.

        Args:
            _initial_state: WorldState at tick 0 (unused, required by protocol).
            _config: SimulationConfig for this run (unused, required by protocol).
        """
        # Create timestamped session directory
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self._session_dir = self._base_dir / timestamp
        self._session_dir.mkdir(parents=True, exist_ok=True)

        # Open file handles (append mode for crash safety)
        # Note: We intentionally keep handles open across methods for performance.
        # Files are closed in on_simulation_end().
        self._metrics_file = open(self._session_dir / "metrics.jsonl", "a")  # noqa: SIM115
        self._events_file = open(self._session_dir / "events.jsonl", "a")  # noqa: SIM115
        self._narrative_file = open(self._session_dir / "narrative.jsonl", "a")  # noqa: SIM115

        # Reset narrative tracking
        self._last_narrative_idx = 0

    def on_tick(
        self,
        _previous_state: WorldState,
        new_state: WorldState,
    ) -> None:
        """Record tick data to JSONL files.

        Args:
            _previous_state: WorldState before tick (unused, required by protocol).
            new_state: WorldState after tick (contains events).
        """
        if self._metrics_file is None:
            return

        # 1. Write TickMetrics from MetricsCollector
        if self._metrics.history:
            latest = self._metrics.history[-1]
            self._metrics_file.write(
                json.dumps(latest.model_dump(), default=_json_serializer) + "\n"
            )

        # 2. Write events from new_state
        if self._events_file is not None:
            for event in new_state.events:
                self._events_file.write(
                    json.dumps(event.model_dump(), default=_json_serializer) + "\n"
                )

        # 3. Write new narratives (if available)
        if self._narrative is not None and self._narrative_file is not None:
            narrative_log = self._narrative.narrative_log
            for idx in range(self._last_narrative_idx, len(narrative_log)):
                entry = {"tick": new_state.tick, "text": narrative_log[idx]}
                self._narrative_file.write(json.dumps(entry) + "\n")
            self._last_narrative_idx = len(narrative_log)

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Close file handles and write summary.

        Args:
            final_state: Final WorldState when simulation ends.
        """
        # Close file handles
        for f in (self._metrics_file, self._events_file, self._narrative_file):
            if f is not None:
                f.close()

        # Write summary.json
        if self._session_dir is not None:
            summary = {
                "final_tick": final_state.tick,
                "session_dir": str(self._session_dir),
                "ended_at": datetime.now().isoformat(),
            }
            (self._session_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    def export_package(self) -> Path:
        """Create ZIP archive of session files.

        Flushes all buffers and creates a compressed archive containing
        all session JSONL files for sharing and debugging.

        Returns:
            Path to the created ZIP file.

        Raises:
            RuntimeError: If no session has been started.
        """
        if self._session_dir is None:
            raise RuntimeError("No session to export")

        # Flush buffers before zipping (only if still open)
        for f in (self._metrics_file, self._events_file, self._narrative_file):
            if f is not None and not f.closed:
                f.flush()

        # Create zip with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        zip_path = self._session_dir / f"babylon-debug-{timestamp}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add all JSONL files
            for file in self._session_dir.glob("*.jsonl"):
                zf.write(file, file.name)

            # Add summary if exists
            summary = self._session_dir / "summary.json"
            if summary.exists():
                zf.write(summary, summary.name)

        return zip_path


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for Pydantic and datetime objects.

    Args:
        obj: Object to serialize.

    Returns:
        JSON-serializable representation.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return str(obj)
