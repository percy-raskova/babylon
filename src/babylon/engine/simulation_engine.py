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

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.engine.systems.protocol import System
from babylon.engine.systems.solidarity import SolidaritySystem
from babylon.engine.systems.survival import SurvivalSystem
from babylon.engine.systems.territory import TerritorySystem
from babylon.models.config import SimulationConfig
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
        context: dict[str, Any],
    ) -> None:
        """Execute all systems in order for one tick.

        Args:
            graph: NetworkX graph (mutated in place by systems)
            services: ServiceContainer with config, formulas, event_bus, database
            context: Mutable context dict passed to all systems
        """
        for system in self._systems:
            system.step(graph, services, context)


# Initialize the machine with Historical Materialist order
# SolidaritySystem runs AFTER ImperialRentSystem, BEFORE ConsciousnessSystem
# This ensures consciousness transmission from solidarity edges
# modifies ideology BEFORE the general consciousness drift calculation
# TerritorySystem runs LAST - spatial dynamics are superstructure effects
_DEFAULT_SYSTEMS: list[System] = [
    ImperialRentSystem(),
    SolidaritySystem(),  # Sprint 3.4.2: Proletarian Internationalism
    ConsciousnessSystem(),
    SurvivalSystem(),
    ContradictionSystem(),
    TerritorySystem(),  # Sprint 3.5.4: Layer 0 - Territorial Substrate
]

_DEFAULT_ENGINE = SimulationEngine(_DEFAULT_SYSTEMS)


def step(state: WorldState, config: SimulationConfig) -> WorldState:
    """Advance simulation by one tick using the modular engine.

    This is the heart of Phase 2. It transforms a WorldState through
    one tick of simulated time by applying the MLM-TW formulas.

    Args:
        state: Current world state (immutable)
        config: Simulation configuration with formula coefficients

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
    services = ServiceContainer.create(config)

    # The Context acts as the shared bus for the tick
    context: dict[str, Any] = {
        "tick": state.tick,
    }

    # Run all systems through the engine
    _DEFAULT_ENGINE.run_tick(G, services, context)

    # Convert EventBus history to string log for backward compatibility
    for event in services.event_bus.get_history():
        events.append(f"Tick {event.tick + 1}: {event.type.upper()}")

    # Reconstruct state from modified graph
    return WorldState.from_graph(G, tick=state.tick + 1, event_log=events)
