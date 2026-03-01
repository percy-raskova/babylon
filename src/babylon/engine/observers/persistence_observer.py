"""Persistence observer for automatic state persistence after tick (Feature 037).

Implements ``SimulationObserver`` protocol. Called after each tick to persist
state to the configured ``RuntimePersistence`` backend. Uses ``isinstance()``
check for ``PostgresRuntimeExtensions`` to persist subsystem state.

Usage::

    from babylon.engine.observers.persistence_observer import PersistenceObserver

    observer = PersistenceObserver(
        persistence=postgres_runtime,
        session_id=session_id,
        tracer=trace_recorder,
    )
    simulation.attach_observer(observer)
"""

from __future__ import annotations

import logging
import time
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


class PersistenceObserver:
    """Observer that persists simulation state after each tick.

    Implements ``SimulationObserver`` protocol. No changes to
    ``Simulation`` facade or ``SimulationEngine`` required.

    Attributes:
        _persistence: Backend implementing RuntimePersistence.
        _session_id: Session UUID for data scoping.
        _tracer: Optional trace collector.
    """

    def __init__(
        self,
        persistence: RuntimePersistence,
        session_id: UUID,
        tracer: TraceCollector | None = None,
    ) -> None:
        """Initialize the persistence observer.

        Args:
            persistence: Backend implementing RuntimePersistence.
            session_id: Session UUID for data scoping.
            tracer: Optional trace collector for execution tracing.
        """
        self._persistence = persistence
        self._session_id = session_id
        self._tracer = tracer

    @property
    def name(self) -> str:
        """Observer identifier."""
        return f"PersistenceObserver[{self._session_id}]"

    def on_simulation_start(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Called when simulation begins. Persists initial state and config.

        Args:
            initial_state: The WorldState at tick 0.
            config: The SimulationConfig for this run.
        """
        import json

        self._persistence.set_metadata(
            "config",
            json.dumps(config.model_dump(mode="json")),
        )
        self._persistence.set_metadata("status", "running")

        # Persist initial state
        self._persist_state(initial_state)

        logger.debug("PersistenceObserver started: session=%s", self._session_id)

    def on_tick(
        self,
        previous_state: WorldState,  # noqa: ARG002
        new_state: WorldState,
    ) -> None:
        """Called after each tick. Persists new state.

        Args:
            previous_state: WorldState before the tick (unused).
            new_state: WorldState after the tick.
        """
        start = time.perf_counter()
        self._persist_state(new_state)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "PersistenceObserver persisted tick %d in %.1f ms",
            new_state.tick,
            elapsed_ms,
        )

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Called when simulation ends. Finalizes metadata.

        Args:
            final_state: The final WorldState.
        """
        self._persistence.set_metadata("end_tick", str(final_state.tick))
        self._persistence.set_metadata("status", "completed")

        # Flush any remaining traces
        if self._tracer is not None:
            self._tracer.flush(self._session_id, final_state.tick)

        logger.debug(
            "PersistenceObserver ended: session=%s, final_tick=%d",
            self._session_id,
            final_state.tick,
        )

    def _persist_state(self, state: WorldState) -> None:
        """Persist full state snapshot.

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


__all__ = ["PersistenceObserver"]
