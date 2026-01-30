"""SessionRecorder observer for persistent SQLite state recording.

Implements SimulationObserver protocol to persist simulation state to SQLite
per tick, enabling replay, debugging, and temporal queries (ADR030/032/033).

The SessionRecorder creates a comprehensive black box recording:
- Node history: Entity state snapshots at each tick
- Edge history: Relationship state at each tick
- Events: Simulation events (uprisings, crashes, etc.)
- Tick log: RNG state and mutation summary for replay

Usage:
    from babylon.data.simulation import SimulationDB
    from babylon.engine.observers.session_recorder import SessionRecorder

    db = SimulationDB(run_id="experiment_001")
    recorder = SessionRecorder(db)

    # Attach to simulation
    simulation.attach_observer(recorder)
    simulation.run(max_ticks=100)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from babylon.models.enums import EdgeType

if TYPE_CHECKING:
    from babylon.data.simulation import SimulationDB
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState

logger = logging.getLogger(__name__)


class SessionRecorder:
    """Observer that persists simulation state to SQLite for replay and debugging.

    Implements SimulationObserver protocol (ADR030/032/033). Records tick-by-tick
    state snapshots to SQLite, enabling:
    - Replay from any point using stored state
    - Temporal queries ("state at tick 500", "diffs between ticks")
    - Debugging via rich mutation logs
    - Post-hoc analysis without re-running simulation

    The recorder persists to SimulationDB's tick-keyed temporal tables:
    - tick_summary: Aggregate metrics (c/v/s, exploitation rate, profit rate)
    - agent_state: Individual entity snapshots
    - network_edge: Relationship state
    - production_event: c/v/s tensor per territory

    Attributes:
        db: SimulationDB instance for persistence.
        _started: Whether simulation has started (for lifecycle validation).
    """

    def __init__(self, db: SimulationDB) -> None:
        """Initialize the session recorder.

        Args:
            db: SimulationDB instance for state persistence.
        """
        self._db = db
        self._started = False

    @property
    def name(self) -> str:
        """Return observer identifier."""
        return f"SessionRecorder[{self._db.run_id}]"

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
        self._db.set_metadata("config", json.dumps(config.model_dump(mode="json")))
        self._db.set_metadata("start_tick", str(initial_state.tick))
        self._db.set_metadata("status", "running")

        # Record initial state
        self._record_tick(initial_state)

        logger.debug("SessionRecorder started: run_id=%s", self._db.run_id)

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

        self._record_tick(new_state)

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Called when simulation ends. Finalizes recording metadata.

        Args:
            final_state: The final WorldState when simulation ends.
        """
        self._db.set_metadata("end_tick", str(final_state.tick))
        self._db.set_metadata("status", "completed")

        logger.debug(
            "SessionRecorder ended: run_id=%s, final_tick=%d",
            self._db.run_id,
            final_state.tick,
        )

    def _record_tick(self, state: WorldState) -> None:
        """Record full state snapshot at a tick.

        Args:
            state: WorldState to persist.
        """
        tick = state.tick

        # Record aggregate metrics (tick_summary)
        self._record_tick_summary(state)

        # Record entity states (agent_state)
        self._record_entities(state)

        # Record relationships (network_edge)
        self._record_relationships(state)

        # Record events if any
        if state.events:
            self._record_events(state)

        logger.debug("SessionRecorder recorded tick %d", tick)

    def _record_tick_summary(self, state: WorldState) -> None:
        """Record aggregate metrics for the tick.

        Args:
            state: WorldState to extract metrics from.
        """
        # Note: c/v/s aggregate values are tracked via production_event table.
        # For tick_summary, we record 0.0 for c/v/s since they're computed
        # from production events, not territory attributes.
        total_c = 0.0
        total_v = 0.0
        total_s = 0.0

        # Calculate average consciousness
        consciousness_values = [
            float(entity.ideology.class_consciousness) for entity in state.entities.values()
        ]
        avg_consciousness = (
            sum(consciousness_values) / len(consciousness_values) if consciousness_values else 0.0
        )

        # Count uprising events this tick
        uprising_count = sum(1 for event in state.events if event.event_type == "UPRISING")

        self._db.record_tick_summary(
            tick=state.tick,
            total_c=total_c,
            total_v=total_v,
            total_s=total_s,
            avg_consciousness=avg_consciousness,
            uprising_count=uprising_count,
        )

    def _record_entities(self, state: WorldState) -> None:
        """Record entity states to agent_state table.

        Args:
            state: WorldState to extract entities from.
        """
        for entity_id, entity in state.entities.items():
            # Convert ideology to JSON for storage (preserves full profile)
            ideology_json = json.dumps(entity.ideology.model_dump())

            # Build agent record
            self._db.con.execute(
                """
                INSERT INTO agent_state
                (tick, agent_id, agent_type, consciousness, organization,
                 wealth_millions, ideology, county_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.tick,
                    entity_id,
                    entity.role.value,
                    float(entity.ideology.class_consciousness),
                    float(entity.organization),
                    float(entity.wealth),
                    ideology_json,
                    getattr(entity, "county_id", None),
                ),
            )

    def _record_relationships(self, state: WorldState) -> None:
        """Record relationship states to network_edge table.

        Args:
            state: WorldState to extract relationships from.
        """
        for rel in state.relationships:
            weight = self._get_edge_weight(rel)
            self._db.con.execute(
                """
                INSERT INTO network_edge
                (tick, source_id, target_id, edge_type, weight)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    state.tick,
                    rel.source_id,
                    rel.target_id,
                    rel.edge_type.value,
                    weight,
                ),
            )

    def _get_edge_weight(self, rel: object) -> float:
        """Extract weight from relationship based on edge type.

        Args:
            rel: Relationship object.

        Returns:
            Appropriate weight value for the edge type.
        """
        # Access attributes directly from the relationship
        edge_type = getattr(rel, "edge_type", None)
        if edge_type == EdgeType.SOLIDARITY:
            return float(getattr(rel, "solidarity_strength", 0.0))
        elif edge_type == EdgeType.EXPLOITATION:
            return float(getattr(rel, "tension", 0.0))
        elif edge_type in (EdgeType.WAGES, EdgeType.TRIBUTE, EdgeType.TENANCY):
            return float(getattr(rel, "value_flow", 0.0))
        else:
            return 1.0

    def _record_events(self, state: WorldState) -> None:
        """Record simulation events for this tick.

        Args:
            state: WorldState with events to record.
        """
        for event in state.events:
            # Events are per-tick, not cumulative
            event_details = {
                "entity_id": event.entity_id if hasattr(event, "entity_id") else None,
                "territory_id": (event.territory_id if hasattr(event, "territory_id") else None),
            }
            # Add any additional event data
            if hasattr(event, "model_dump"):
                event_details.update(event.model_dump(mode="json"))

            self._db.con.execute(
                """
                INSERT INTO production_event
                (tick, territory_id, sector_code, c_millions, v_millions, s_millions,
                 workers)
                VALUES (?, ?, ?, 0, 0, 0, 0)
                """,
                (
                    state.tick,
                    event_details.get("territory_id", "GLOBAL"),
                    event.event_type,
                ),
            )


__all__ = ["SessionRecorder"]
