"""Simulation engine for the Babylon game loop.

The step() function is the core of Phase 2. It takes a WorldState and
SimulationConfig and returns a new WorldState representing one tick of
simulation time.

The step function is:
- **Pure**: No side effects, no mutation of inputs
- **Deterministic**: Same inputs always produce same outputs
- **Transparent**: Order of operations encodes historical materialism

Turn Order (encodes historical materialism):
1. Economic Base - Value extraction (imperial rent)
2. Consciousness - Ideology drift based on material conditions
3. Survival Calculus - P(S|A) and P(S|R) updates
4. Contradiction Tension - Accumulated from wealth gaps
5. Event Logging - Record significant state changes

Phase 2.1: Refactored to modular System architecture.
Phase 4a: Refactored to use ServiceContainer for dependency injection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.event_bus import Event
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.engine.systems.protocol import ContextType, System
from babylon.engine.systems.solidarity import SolidaritySystem
from babylon.engine.systems.struggle import StruggleSystem
from babylon.engine.systems.survival import SurvivalSystem
from babylon.engine.systems.territory import TerritorySystem
from babylon.models.config import SimulationConfig
from babylon.models.enums import EventType
from babylon.models.events import (
    CrisisEvent,
    ExtractionEvent,
    MassAwakeningEvent,
    PhaseTransitionEvent,
    RuptureEvent,
    SimulationEvent,
    SolidaritySpikeEvent,
    SparkEvent,
    SubsidyEvent,
    TransmissionEvent,
    UprisingEvent,
)
from babylon.models.world_state import WorldState

if TYPE_CHECKING:
    import networkx as nx


class SimulationEngine:
    """Modular engine that advances the simulation by iterating through Systems.

    The engine holds a list of systems and executes them in sequence.
    Order encodes historical materialism:
    1. Economic Base (imperial rent)
    2. Consciousness (ideology drift)
    3. Survival Calculus (probability updates)
    4. Contradiction (tension dynamics)
    """

    def __init__(self, systems: list[System]) -> None:
        """Initialize the engine with a list of systems.

        Args:
            systems: Ordered list of systems to execute each tick.
                     Order matters! Economic systems must run before ideology.
        """
        self._systems = systems

    @property
    def systems(self) -> list[System]:
        """Read-only access to registered systems."""
        return list(self._systems)

    def run_tick(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Execute all systems in order for one tick.

        Args:
            graph: NetworkX graph (mutated in place by systems)
            services: ServiceContainer with config, formulas, event_bus, database
            context: TickContext or dict passed to all systems
        """
        for system in self._systems:
            system.step(graph, services, context)


# Initialize the machine with Historical Materialist order
# SolidaritySystem runs AFTER ImperialRentSystem, BEFORE ConsciousnessSystem
# This ensures consciousness transmission from solidarity edges
# modifies ideology BEFORE the general consciousness drift calculation
# StruggleSystem runs AFTER SurvivalSystem (needs P values), BEFORE ContradictionSystem
# The solidarity built in Tick N enables SolidaritySystem transmission in Tick N+1
# TerritorySystem runs LAST - spatial dynamics are superstructure effects
_DEFAULT_SYSTEMS: list[System] = [
    ImperialRentSystem(),
    SolidaritySystem(),  # Sprint 3.4.2: Proletarian Internationalism
    ConsciousnessSystem(),
    SurvivalSystem(),
    StruggleSystem(),  # Agency Layer: George Floyd Dynamic
    ContradictionSystem(),
    TerritorySystem(),  # Sprint 3.5.4: Layer 0 - Territorial Substrate
]

_DEFAULT_ENGINE = SimulationEngine(_DEFAULT_SYSTEMS)


def _convert_bus_event_to_pydantic(event: Event) -> SimulationEvent | None:
    """Convert EventBus Event to typed Pydantic SimulationEvent.

    Args:
        event: The EventBus Event dataclass with type, tick, payload.

    Returns:
        A typed SimulationEvent subclass, or None if unsupported event type.

    Note:
        This function handles graceful degradation - unsupported event types
        return None rather than raising an error. The caller should filter
        out None values.

    Sprint 3.1+: Supports all 10 EventTypes except SOLIDARITY_AWAKENING.
    """
    # Normalize event type (may be string or EventType enum)
    event_type = event.type
    if isinstance(event_type, str):
        try:
            event_type = EventType(event_type)
        except ValueError:
            return None

    tick = event.tick
    timestamp = event.timestamp
    payload = event.payload

    # Economic Events
    if event_type == EventType.SURPLUS_EXTRACTION:
        return ExtractionEvent(
            tick=tick,
            timestamp=timestamp,
            source_id=payload.get("source_id", ""),
            target_id=payload.get("target_id", ""),
            amount=payload.get("amount", 0.0),
            mechanism=payload.get("mechanism", "imperial_rent"),
        )

    if event_type == EventType.IMPERIAL_SUBSIDY:
        return SubsidyEvent(
            tick=tick,
            timestamp=timestamp,
            source_id=payload.get("source_id", ""),
            target_id=payload.get("target_id", ""),
            amount=payload.get("amount", 0.0),
            repression_boost=payload.get("repression_boost", 0.0),
        )

    if event_type == EventType.ECONOMIC_CRISIS:
        return CrisisEvent(
            tick=tick,
            timestamp=timestamp,
            pool_ratio=payload.get("pool_ratio", 0.0),
            aggregate_tension=payload.get("aggregate_tension", 0.0),
            decision=payload.get("decision", "UNKNOWN"),
            wage_delta=payload.get("wage_delta", 0.0),
        )

    # Consciousness Events
    if event_type == EventType.CONSCIOUSNESS_TRANSMISSION:
        return TransmissionEvent(
            tick=tick,
            timestamp=timestamp,
            source_id=payload.get("source_id", ""),
            target_id=payload.get("target_id", ""),
            delta=payload.get("delta", 0.0),
            solidarity_strength=payload.get("solidarity_strength", 0.0),
        )

    if event_type == EventType.MASS_AWAKENING:
        return MassAwakeningEvent(
            tick=tick,
            timestamp=timestamp,
            target_id=payload.get("target_id", ""),
            old_consciousness=payload.get("old_consciousness", 0.0),
            new_consciousness=payload.get("new_consciousness", 0.0),
            triggering_source=payload.get("triggering_source", ""),
        )

    # Struggle Events (Agency Layer - George Floyd Dynamic)
    if event_type == EventType.EXCESSIVE_FORCE:
        return SparkEvent(
            tick=tick,
            timestamp=timestamp,
            node_id=payload.get("node_id", ""),
            repression=payload.get("repression", 0.0),
            spark_probability=payload.get("spark_probability", 0.0),
        )

    if event_type == EventType.UPRISING:
        return UprisingEvent(
            tick=tick,
            timestamp=timestamp,
            node_id=payload.get("node_id", ""),
            trigger=payload.get("trigger", "unknown"),
            agitation=payload.get("agitation", 0.0),
            repression=payload.get("repression", 0.0),
        )

    if event_type == EventType.SOLIDARITY_SPIKE:
        return SolidaritySpikeEvent(
            tick=tick,
            timestamp=timestamp,
            node_id=payload.get("node_id", ""),
            solidarity_gained=payload.get("solidarity_gained", 0.0),
            edges_affected=payload.get("edges_affected", 0),
            triggered_by=payload.get("triggered_by", "unknown"),
        )

    # Contradiction Events
    if event_type == EventType.RUPTURE:
        return RuptureEvent(
            tick=tick,
            timestamp=timestamp,
            edge=payload.get("edge", ""),
        )

    # Topology Events (Sprint 3.3)
    if event_type == EventType.PHASE_TRANSITION:
        return PhaseTransitionEvent(
            tick=tick,
            timestamp=timestamp,
            previous_state=payload.get("previous_state", ""),
            new_state=payload.get("new_state", ""),
            percolation_ratio=payload.get("percolation_ratio", 0.0),
            num_components=payload.get("num_components", 0),
            largest_component_size=payload.get("largest_component_size", 0),
            cadre_density=payload.get("cadre_density", 0.0),
            is_resilient=payload.get("is_resilient"),
        )

    # Unsupported event type (e.g., SOLIDARITY_AWAKENING) - graceful degradation
    return None


def step(
    state: WorldState,
    config: SimulationConfig,
    persistent_context: dict[str, Any] | None = None,
    defines: GameDefines | None = None,
) -> WorldState:
    """Advance simulation by one tick using the modular engine.

    This is the heart of Phase 2. It transforms a WorldState through
    one tick of simulated time by applying the MLM-TW formulas.

    Args:
        state: Current world state (immutable)
        config: Simulation configuration with formula coefficients
        persistent_context: Optional context dict that persists across ticks.
            Used by systems that need to track state between ticks (e.g.,
            ConsciousnessSystem's previous_wages for bifurcation mechanic).
        defines: Optional custom GameDefines. If None, loads from default
            defines.yaml location. Use this for scenario-specific calibration.

    Returns:
        New WorldState at tick + 1

    Order encodes historical materialism:
        1. Economic base (value extraction)
        2. Consciousness (responds to material conditions)
        3. Survival calculus (probability updates)
        4. Contradictions (tension from all above)
        5. Event capture (log significant changes)
    """
    # Short-circuit for empty state
    if not state.entities:
        return state.model_copy(update={"tick": state.tick + 1})

    # Convert to mutable graph for system application
    G = state.to_graph()
    events: list[str] = list(state.event_log)

    # Create ServiceContainer for this tick
    # Use provided defines, or load from default YAML
    effective_defines = defines if defines is not None else GameDefines.load_default()
    services = ServiceContainer.create(config, effective_defines)

    # Create typed TickContext for this tick
    # persistent_data is initialized from caller's persistent_context if provided
    context = TickContext(
        tick=state.tick,
        persistent_data=dict(persistent_context) if persistent_context else {},
    )

    # Run all systems through the engine
    _DEFAULT_ENGINE.run_tick(G, services, context)

    # Sync any changes from context.persistent_data back to caller's dict
    if persistent_context is not None:
        for key, value in context.persistent_data.items():
            persistent_context[key] = value

    # Convert EventBus history to both string log and typed events
    structured_events: list[SimulationEvent] = []
    for event in services.event_bus.get_history():
        # String log for backward compatibility
        events.append(f"Tick {event.tick + 1}: {event.type.upper()}")
        # Typed Pydantic event (Sprint 3.1)
        pydantic_event = _convert_bus_event_to_pydantic(event)
        if pydantic_event is not None:
            structured_events.append(pydantic_event)

    # Include observer events from previous tick (Sprint 3.3)
    # Observer events are emitted AFTER WorldState is frozen, so they
    # appear in the NEXT tick's events via persistent_context
    if persistent_context is not None:
        observer_events = persistent_context.get("_observer_events", [])
        if observer_events:
            # Type assertion: observer_events is list[SimulationEvent]
            for obs_event in observer_events:
                if isinstance(obs_event, SimulationEvent):
                    structured_events.append(obs_event)
            # Clear the observer events after injection
            del persistent_context["_observer_events"]

    # Reconstruct state from modified graph
    return WorldState.from_graph(
        G,
        tick=state.tick + 1,
        event_log=events,
        events=structured_events,
    )
