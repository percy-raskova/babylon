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

Sprint 5: Phase 2 game loop implementation.
"""

from __future__ import annotations

import networkx as nx

from babylon.models.config import SimulationConfig
from babylon.models.enums import EdgeType
from babylon.models.world_state import WorldState
from babylon.systems.formulas import (
    calculate_acquiescence_probability,
    calculate_consciousness_drift,
    calculate_imperial_rent,
    calculate_revolution_probability,
)


def step(state: WorldState, config: SimulationConfig) -> WorldState:
    """Advance simulation by one tick. Pure function.

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

    # Convert to mutable graph for formula application
    G = state.to_graph()
    events: list[str] = list(state.event_log)  # Preserve existing events

    # Phase 1: Economic Base - Imperial Rent Extraction
    _apply_imperial_rent(G, config, events, state.tick)

    # Phase 2: Consciousness Drift
    _update_consciousness_drift(G, config)

    # Phase 3: Survival Calculus
    _update_survival_probabilities(G, config)

    # Phase 4: Contradiction Tension
    _update_contradiction_tension(G, config, events, state.tick)

    # Phase 5: Reconstruct state from modified graph
    return WorldState.from_graph(G, tick=state.tick + 1, event_log=events)


def _apply_imperial_rent(
    G: nx.DiGraph[str],
    config: SimulationConfig,
    _events: list[str],
    _tick: int,
) -> None:
    """Apply imperial rent extraction to all exploitation edges.

    For each EXPLOITATION edge:
    1. Calculate rent based on worker wealth and consciousness
    2. Transfer wealth from worker (source) to owner (target)
    3. Record value_flow on the edge

    Args:
        G: NetworkX graph (mutated in place)
        config: Simulation configuration
        events: Event log (mutated in place)
        tick: Current tick number
    """
    for source_id, target_id, data in G.edges(data=True):
        edge_type = data.get("edge_type")
        if isinstance(edge_type, str):
            edge_type = EdgeType(edge_type)

        if edge_type != EdgeType.EXPLOITATION:
            continue

        # Get source (worker) data
        worker_data = G.nodes[source_id]
        worker_wealth = worker_data.get("wealth", 0.0)
        worker_ideology = worker_data.get("ideology", 0.0)

        # Map ideology [-1, 1] to consciousness [0, 1]
        # -1 (revolutionary) -> 1.0 consciousness (resistance)
        # +1 (reactionary) -> 0.0 consciousness (submission)
        consciousness = (1.0 - worker_ideology) / 2.0

        # Calculate imperial rent
        rent = calculate_imperial_rent(
            alpha=config.extraction_efficiency,
            periphery_wages=worker_wealth,
            periphery_consciousness=consciousness,
        )

        # Ensure we don't extract more than worker has
        rent = min(rent, worker_wealth)

        # Transfer wealth
        G.nodes[source_id]["wealth"] = max(0.0, worker_wealth - rent)
        G.nodes[target_id]["wealth"] = G.nodes[target_id].get("wealth", 0.0) + rent

        # Record value flow on edge
        G.edges[source_id, target_id]["value_flow"] = rent


def _update_consciousness_drift(
    G: nx.DiGraph[str],
    config: SimulationConfig,
) -> None:
    """Apply consciousness drift to all entities based on material conditions.

    For each entity:
    1. Calculate value_produced from sum of value_flow on outgoing EXPLOITATION edges
    2. Skip if value_produced <= 0 (no exploitation = no material basis for drift)
    3. Map ideology to consciousness, apply drift formula, map back
    4. Clamp result to [-1, 1]

    The consciousness drift formula:
        dPsi/dt = k(1 - W/V) - lambda * Psi

    Where:
    - W = worker wealth (wages)
    - V = value produced (sum of outgoing value_flow)
    - k = consciousness_sensitivity
    - lambda = consciousness_decay_lambda
    - Psi = consciousness [0, 1]

    Mapping between ideology and consciousness:
    - consciousness = (1 - ideology) / 2
    - ideology = 1 - 2*consciousness

    Args:
        G: NetworkX graph (mutated in place)
        config: Simulation configuration
    """
    for node_id in G.nodes():
        # Calculate value_produced: sum of value_flow on outgoing EXPLOITATION edges
        value_produced = 0.0
        for _, _, data in G.out_edges(node_id, data=True):
            edge_type = data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)
            if edge_type == EdgeType.EXPLOITATION:
                value_produced += data.get("value_flow", 0.0)

        # Skip entities with no outgoing exploitation (no material basis for drift)
        if value_produced <= 0:
            continue

        # Get current state
        node_data = G.nodes[node_id]
        current_ideology = node_data.get("ideology", 0.0)

        # Map ideology [-1, 1] to consciousness [0, 1]
        # -1 (revolutionary) -> 1.0 consciousness
        # +1 (reactionary) -> 0.0 consciousness
        current_consciousness = (1.0 - current_ideology) / 2.0

        # For consciousness drift, we interpret:
        # - value_produced: The value being extracted from this worker (value_flow sum)
        # - core_wages: What the worker "receives" in exchange for their labor
        #
        # In our extraction model, the worker produces value (= value_flow) that
        # flows to the owner. In return, they receive... nothing (pure extraction).
        # This is the definition of super-exploitation: W/V = 0.
        #
        # Formula: dPsi/dt = k(1 - W/V) - lambda*Psi
        # With W=0: drift = k(1 - 0) - lambda*Psi = k - lambda*Psi (always positive
        # when k > lambda*Psi, causing consciousness to increase toward revolution)
        core_wages = 0.0

        # Calculate consciousness drift
        drift = calculate_consciousness_drift(
            core_wages=core_wages,
            value_produced=value_produced,
            current_consciousness=current_consciousness,
            sensitivity_k=config.consciousness_sensitivity,
            decay_lambda=config.consciousness_decay_lambda,
        )

        # Apply drift to consciousness
        new_consciousness = current_consciousness + drift

        # Clamp consciousness to [0, 1]
        new_consciousness = max(0.0, min(1.0, new_consciousness))

        # Map consciousness back to ideology
        # consciousness 1.0 -> ideology -1.0
        # consciousness 0.0 -> ideology +1.0
        new_ideology = 1.0 - 2.0 * new_consciousness

        # Clamp ideology to [-1, 1] for safety
        new_ideology = max(-1.0, min(1.0, new_ideology))

        G.nodes[node_id]["ideology"] = new_ideology


def _update_survival_probabilities(
    G: nx.DiGraph[str],
    config: SimulationConfig,
) -> None:
    """Update P(S|A) and P(S|R) for all entities.

    Args:
        G: NetworkX graph (mutated in place)
        config: Simulation configuration
    """
    for node_id, data in G.nodes(data=True):
        wealth = data.get("wealth", 0.0)
        organization = data.get("organization", 0.1)
        repression_faced = data.get("repression_faced", 0.5)
        subsistence = data.get("subsistence_threshold", config.subsistence_threshold)

        # P(S|A) - survival through acquiescence
        p_acq = calculate_acquiescence_probability(
            wealth=wealth,
            subsistence_threshold=subsistence,
            steepness_k=config.survival_steepness,
        )

        # P(S|R) - survival through revolution
        p_rev = calculate_revolution_probability(
            cohesion=organization,
            repression=repression_faced,
        )

        G.nodes[node_id]["p_acquiescence"] = p_acq
        G.nodes[node_id]["p_revolution"] = p_rev


def _update_contradiction_tension(
    G: nx.DiGraph[str],
    config: SimulationConfig,
    events: list[str],
    tick: int,
) -> None:
    """Update tension on edges based on wealth gaps.

    Tension accumulates based on the wealth differential between
    connected entities. Larger gaps create more tension.

    Args:
        G: NetworkX graph (mutated in place)
        config: Simulation configuration
        events: Event log (mutated in place)
        tick: Current tick number
    """
    for source_id, target_id, data in G.edges(data=True):
        source_wealth = G.nodes[source_id].get("wealth", 0.0)
        target_wealth = G.nodes[target_id].get("wealth", 0.0)

        # Tension increases with wealth gap
        wealth_gap = abs(target_wealth - source_wealth)
        tension_delta = wealth_gap * config.tension_accumulation_rate

        current_tension = data.get("tension", 0.0)
        new_tension = min(1.0, current_tension + tension_delta)

        G.edges[source_id, target_id]["tension"] = new_tension

        # Log rupture events
        if new_tension >= 1.0 and current_tension < 1.0:
            events.append(f"Tick {tick + 1}: RUPTURE on edge {source_id}->{target_id}")
