"""SessionRecorder observer for persistent simulation state recording.

Implements SimulationObserver protocol to persist simulation state
per tick via the ``RuntimePersistence`` protocol, enabling replay,
debugging, and temporal queries (ADR030/032/033 + Feature 037).

The SessionRecorder creates a comprehensive black box recording:
- Node history: Entity state snapshots at each tick
- Edge history: Relationship state at each tick
- Events: Simulation events (uprisings, crashes, etc.)
- Tick log: RNG state and mutation summary for replay

.. note::
    As of Feature 037, ``SessionRecorder`` delegates **all** persistence
    to the ``RuntimePersistence`` protocol. This means it works natively
    with ``PostgresRuntime`` (production) and can still be used with
    ``RuntimeDatabase`` (SQLite) for lightweight dev/test scenarios.

    SQLite is treated as **read-only** for initialization; all new writes
    target PostgreSQL via ``RuntimePersistence.persist_tick``.

Usage::

    from babylon.persistence.postgres_runtime import PostgresRuntime
    from babylon.engine.observers.session_recorder import SessionRecorder

    with PostgresRuntime(pool) as pg:
        recorder = SessionRecorder(persistence=pg, session_id=session_id)
        simulation.attach_observer(recorder)
        simulation.run(max_ticks=100)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from babylon.persistence.protocols import (
    PostgresRuntimeExtensions,
    RuntimePersistence,
    TraceCollector,
)

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState

logger = logging.getLogger(__name__)


class SessionRecorder:
    """Observer that persists simulation state via RuntimePersistence protocol.

    Implements SimulationObserver protocol (ADR030/032/033). Records tick-by-tick
    state snapshots to the configured ``RuntimePersistence`` backend, enabling:

    - Replay from any point using stored state
    - Temporal queries ("state at tick 500", "diffs between ticks")
    - Debugging via rich mutation logs
    - Post-hoc analysis without re-running simulation

    When the backend implements ``PostgresRuntimeExtensions``, extended
    subsystem state (graph metadata, community state, etc.) is also persisted.

    Attributes:
        _persistence: Backend implementing RuntimePersistence.
        _session_id: Session UUID for data scoping.
        _tracer: Optional trace collector for execution tracing.
        _started: Whether simulation has started (for lifecycle validation).
    """

    def __init__(
        self,
        persistence: RuntimePersistence,
        session_id: UUID,
        tracer: TraceCollector | None = None,
    ) -> None:
        """Initialize the session recorder.

        Args:
            persistence: Backend implementing RuntimePersistence protocol.
            session_id: Session UUID for data scoping.
            tracer: Optional trace collector for execution tracing.
        """
        self._persistence = persistence
        self._session_id = session_id
        self._tracer = tracer
        self._started = False

    @property
    def name(self) -> str:
        """Return observer identifier."""
        return f"SessionRecorder[{self._session_id}]"

    def on_simulation_start(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Called when simulation begins. Initializes recording metadata.

        Args:
            initial_state: The WorldState at tick 0.
            config: The SimulationConfig for this run.
        """
        self._started = True

        # Store simulation metadata
        self._persistence.set_metadata(
            "config",
            json.dumps(config.model_dump(mode="json")),
        )
        self._persistence.set_metadata("start_tick", str(initial_state.tick))
        self._persistence.set_metadata("status", "running")

        # Record initial state
        self._persist_state(initial_state)

        logger.debug("SessionRecorder started: session=%s", self._session_id)

    def on_tick(
        self,
        previous_state: WorldState,  # noqa: ARG002 - Required by SimulationObserver protocol
        new_state: WorldState,
    ) -> None:
        """Called after each tick completes. Records new state to database.

        Args:
            previous_state: WorldState before the tick (unused, for delta analysis).
            new_state: WorldState after the tick.
        """
        if not self._started:
            logger.warning("SessionRecorder.on_tick called before on_simulation_start")
            return

        self._persist_state(new_state)

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Called when simulation ends. Finalizes recording metadata.

        Args:
            final_state: The final WorldState when simulation ends.
        """
        self._persistence.set_metadata("end_tick", str(final_state.tick))
        self._persistence.set_metadata("status", "completed")

        # Flush any remaining traces
        if self._tracer is not None:
            self._tracer.flush(self._session_id, final_state.tick)

        logger.debug(
            "SessionRecorder ended: session=%s, final_tick=%d",
            self._session_id,
            final_state.tick,
        )

    def _persist_state(self, state: WorldState) -> None:
        """Persist full state snapshot at a tick.

        Args:
            state: WorldState to persist.
        """
        graph = state.to_graph()
        events = self._serialize_events(state)

        self._persistence.persist_tick(
            tick=state.tick,
            graph=graph,
            events=events,
            session_id=self._session_id,
        )

        # Persist extended subsystem state if backend supports it
        if isinstance(self._persistence, PostgresRuntimeExtensions):
            self._persist_extended_state(state, graph)

        # Flush tracer after persist
        if self._tracer is not None:
            self._tracer.flush(self._session_id, state.tick)

        logger.debug("SessionRecorder recorded tick %d", state.tick)

    def _persist_extended_state(
        self,
        state: WorldState,
        graph: Any,
    ) -> None:
        """Persist subsystem state for PostgresRuntimeExtensions backends.

        Args:
            state: WorldState with subsystem data.
            graph: The NetworkX graph from state.to_graph().
        """
        persistence = self._persistence
        tick = state.tick

        # Graph metadata (economy, state_finances, tick_dynamics)
        graph_data = graph.graph if hasattr(graph, "graph") else {}
        economy = graph_data.get("economy", {})
        state_finances = graph_data.get("state_finances", {})
        tick_dynamics = graph_data.get("tick_dynamics")

        if isinstance(persistence, PostgresRuntimeExtensions):
            persistence.persist_graph_metadata(
                tick=tick,
                economy=economy,
                state_finances=state_finances,
                tick_dynamics=tick_dynamics,
                session_id=self._session_id,
            )

    @staticmethod
    def _serialize_events(state: WorldState) -> list[dict[str, Any]]:
        """Convert WorldState events to serializable dicts.

        Args:
            state: WorldState with events.

        Returns:
            List of event dicts.
        """
        events: list[dict[str, Any]] = []
        for event in state.events:
            if hasattr(event, "model_dump"):
                events.append(event.model_dump(mode="json"))
            else:
                events.append({"type": str(event)})
        return events


__all__ = ["SessionRecorder"]
