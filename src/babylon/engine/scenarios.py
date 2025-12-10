"""Factory functions for creating simulation scenarios.

These functions create pre-configured WorldState and SimulationConfig
pairs for testing and exploration.

Sprint 6: Phase 2 integration testing support.
Multiverse Protocol: Scenario injection for counterfactual simulation.
"""

from __future__ import annotations

from babylon.models.config import SimulationConfig
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import EdgeType, SocialRole
from babylon.models.scenario import ScenarioConfig
from babylon.models.world_state import WorldState


def create_two_node_scenario(
    worker_wealth: float = 0.5,
    owner_wealth: float = 0.5,
    extraction_efficiency: float = 0.8,
    repression_level: float = 0.5,
    worker_organization: float = 0.1,
    worker_ideology: float = 0.0,
) -> tuple[WorldState, SimulationConfig]:
    """Create the minimal viable dialectic: one worker, one owner, one exploitation edge.

    This is the two-node scenario from the Phase 1 blueprint, now ready for
    Phase 2 simulation. It models the fundamental class relationship:
    - Worker produces value (source of exploitation edge)
    - Owner extracts imperial rent (target of exploitation edge)
    - Tension accumulates on the edge

    Args:
        worker_wealth: Initial wealth for periphery worker (default 0.5)
        owner_wealth: Initial wealth for core owner (default 0.5)
        extraction_efficiency: Alpha in imperial rent formula (default 0.8)
        repression_level: State violence capacity (default 0.5)
        worker_organization: Worker class cohesion (default 0.1)
        worker_ideology: Worker ideology, -1=revolutionary to +1=reactionary (default 0.0)

    Returns:
        Tuple of (WorldState, SimulationConfig) ready for step() function.

    Example:
        >>> state, config = create_two_node_scenario()
        >>> for _ in range(100):
        ...     state = step(state, config)
        >>> print(f"Worker wealth after 100 ticks: {state.entities['C001'].wealth}")
    """
    # Create worker (periphery proletariat)
    worker = SocialClass(
        id="C001",
        name="Periphery Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        description="Exploited worker in the global periphery",
        wealth=worker_wealth,
        ideology=worker_ideology,  # type: ignore[arg-type]  # Validator converts float to IdeologicalProfile
        organization=worker_organization,
        repression_faced=repression_level,
        subsistence_threshold=0.3,
        p_acquiescence=0.0,  # Will be calculated by step()
        p_revolution=0.0,  # Will be calculated by step()
    )

    # Create owner (core bourgeoisie)
    owner = SocialClass(
        id="C002",
        name="Core Owner",
        role=SocialRole.CORE_BOURGEOISIE,
        description="Capital owner in the imperial core",
        wealth=owner_wealth,
        ideology=0.5,  # type: ignore[arg-type]  # Leaning reactionary; Validator converts
        organization=0.8,  # Capitalists are well-organized
        repression_faced=0.1,  # Protected by the state
        subsistence_threshold=0.1,  # Low survival needs
        p_acquiescence=0.0,
        p_revolution=0.0,
    )

    # Create exploitation relationship
    exploitation = Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        description="Imperial rent extraction",
        value_flow=0.0,  # Will be calculated by step()
        tension=0.0,  # Will accumulate over time
    )

    # Bug Fix: Add SOLIDARITY edge so solidarity_index affects P(S|R)
    # This represents potential class solidarity infrastructure between workers.
    # The solidarity_strength will be set by apply_scenario() based on solidarity_index.
    # Self-solidarity edge: worker supports worker (internal class cohesion)
    solidarity = Relationship(
        source_id="C002",  # External support flows TO worker
        target_id="C001",  # Worker receives solidarity
        edge_type=EdgeType.SOLIDARITY,
        description="Class solidarity infrastructure",
        value_flow=0.0,
        tension=0.0,
        solidarity_strength=0.0,  # Will be set by apply_scenario()
    )

    # Create world state
    state = WorldState(
        tick=0,
        entities={"C001": worker, "C002": owner},
        relationships=[exploitation, solidarity],
        event_log=[],
    )

    # Create configuration
    config = SimulationConfig(
        extraction_efficiency=extraction_efficiency,
        repression_level=repression_level,
        subsistence_threshold=0.3,
        survival_steepness=10.0,
        consciousness_sensitivity=0.5,
        initial_worker_wealth=worker_wealth,
        initial_owner_wealth=owner_wealth,
    )

    return state, config


def create_high_tension_scenario() -> tuple[WorldState, SimulationConfig]:
    """Create a scenario with high initial tension.

    Worker is poor, owner is rich, tension is already elevated.
    Useful for testing phase transitions and rupture conditions.

    Returns:
        Tuple of (WorldState, SimulationConfig) near rupture point.
    """
    state, config = create_two_node_scenario(
        worker_wealth=0.1,  # Near poverty
        owner_wealth=0.9,  # Very wealthy
        extraction_efficiency=0.9,  # High exploitation
        repression_level=0.8,  # High repression
        worker_organization=0.3,  # Some organization
        worker_ideology=-0.5,  # Leaning revolutionary
    )

    # Add some initial tension to the edge
    if state.relationships:
        rel = state.relationships[0]
        # Create new relationship with higher tension
        tensioned_rel = Relationship(
            source_id=rel.source_id,
            target_id=rel.target_id,
            edge_type=rel.edge_type,
            value_flow=rel.value_flow,
            tension=0.7,  # High starting tension
            description=rel.description,
        )
        state = state.model_copy(update={"relationships": [tensioned_rel]})

    return state, config


def create_labor_aristocracy_scenario() -> tuple[WorldState, SimulationConfig]:
    """Create a scenario with a labor aristocracy (Wc > Vc).

    Worker receives more than they produce, enabled by imperial rent
    from elsewhere. Tests consciousness decay mechanics.

    Returns:
        Tuple of (WorldState, SimulationConfig) with labor aristocracy.
    """
    return create_two_node_scenario(
        worker_wealth=0.8,  # Well-off worker
        owner_wealth=0.2,  # Owner extracting from elsewhere
        extraction_efficiency=0.3,  # Low local extraction
        repression_level=0.3,  # Low repression needed
        worker_organization=0.05,  # Very low organization
        worker_ideology=0.5,  # Leaning reactionary
    )


# =============================================================================
# MULTIVERSE PROTOCOL: Scenario Injection
# =============================================================================


def get_multiverse_scenarios() -> list[ScenarioConfig]:
    """Generate 2^3 = 8 permutations of High/Low scenario values.

    This implements the Multiverse Protocol: running deterministic simulations
    across parameter space to prove mathematical divergence.

    Parameter ranges:
        - superwage_multiplier: 0.3 (Low) or 1.5 (High)
        - solidarity_index: 0.2 (Low) or 0.8 (High)
        - repression_capacity: 0.2 (Low) or 0.8 (High)

    Expected outcomes:
        - High SW + Low Solidarity + High Repression -> Low P(S|R) (Stable for Capital)
        - Low SW + High Solidarity + Low Repression -> High P(S|R) (Revolution likely)

    Returns:
        List of 8 ScenarioConfig objects covering all permutations.

    Example:
        >>> scenarios = get_multiverse_scenarios()
        >>> for s in scenarios:
        ...     print(f"{s.name}: sw={s.superwage_multiplier}, sol={s.solidarity_index}")
    """
    scenarios: list[ScenarioConfig] = []

    superwage_values = [0.3, 1.5]  # Low, High
    solidarity_values = [0.2, 0.8]  # Low, High
    repression_values = [0.2, 0.8]  # Low, High

    for superwage in superwage_values:
        for solidarity in solidarity_values:
            for repression in repression_values:
                # Generate descriptive name
                sw_label = "HighSW" if superwage > 1.0 else "LowSW"
                sol_label = "HighSol" if solidarity > 0.5 else "LowSol"
                rep_label = "HighRep" if repression > 0.5 else "LowRep"
                name = f"{sw_label}_{sol_label}_{rep_label}"

                scenarios.append(
                    ScenarioConfig(
                        name=name,
                        superwage_multiplier=superwage,
                        solidarity_index=solidarity,
                        repression_capacity=repression,
                    )
                )

    return scenarios


def apply_scenario(
    state: WorldState,
    config: SimulationConfig,
    scenario: ScenarioConfig,
) -> tuple[WorldState, SimulationConfig]:
    """Apply scenario modifiers to WorldState and SimulationConfig.

    This function transforms a base (state, config) pair into a counterfactual
    scenario by applying the three modifiers:

    1. superwage_multiplier: Multiplies extraction_efficiency in SimulationConfig.
       - Clamped to [0, 1] since extraction_efficiency is a Coefficient.

    2. solidarity_index: Sets solidarity_strength on all SOLIDARITY edges.
       - Does not affect EXPLOITATION or other edge types.

    3. repression_capacity: Updates repression_faced on all SocialClass entities
       AND repression_level in SimulationConfig.

    Args:
        state: Base WorldState to modify (not mutated)
        config: Base SimulationConfig to modify (not mutated)
        scenario: ScenarioConfig with modifier values

    Returns:
        Tuple of (new_state, new_config) with scenario modifiers applied.

    Example:
        >>> state, config = create_two_node_scenario()
        >>> scenario = ScenarioConfig(name="test", superwage_multiplier=1.5)
        >>> new_state, new_config = apply_scenario(state, config, scenario)
        >>> new_config.extraction_efficiency  # Will be 1.0 (clamped from 0.8 * 1.5)
    """
    # 1. Apply superwage_multiplier to extraction_efficiency
    # Clamp to [0, 1] since extraction_efficiency is a Coefficient
    new_extraction = min(1.0, config.extraction_efficiency * scenario.superwage_multiplier)

    # 2. Apply repression_capacity to repression_level
    new_repression_level = scenario.repression_capacity

    # Create new config with modified values
    new_config = config.model_copy(
        update={
            "extraction_efficiency": new_extraction,
            "repression_level": new_repression_level,
        }
    )

    # 3. Apply solidarity_index to SOLIDARITY edges
    # and repression_capacity to all SocialClass entities
    new_relationships: list[Relationship] = []
    for rel in state.relationships:
        if rel.edge_type == EdgeType.SOLIDARITY:
            # Update solidarity_strength on SOLIDARITY edges
            new_rel = Relationship(
                source_id=rel.source_id,
                target_id=rel.target_id,
                edge_type=rel.edge_type,
                value_flow=rel.value_flow,
                tension=rel.tension,
                description=rel.description,
                subsidy_cap=rel.subsidy_cap,
                solidarity_strength=scenario.solidarity_index,
            )
            new_relationships.append(new_rel)
        else:
            # Keep other edges unchanged
            new_relationships.append(rel)

    # 4. Apply repression_capacity to all SocialClass entities
    new_entities: dict[str, SocialClass] = {}
    for entity_id, entity in state.entities.items():
        new_entity = SocialClass(
            id=entity.id,
            name=entity.name,
            role=entity.role,
            description=entity.description,
            wealth=entity.wealth,
            ideology=entity.ideology,
            p_acquiescence=entity.p_acquiescence,
            p_revolution=entity.p_revolution,
            subsistence_threshold=entity.subsistence_threshold,
            organization=entity.organization,
            repression_faced=scenario.repression_capacity,  # Modified
        )
        new_entities[entity_id] = new_entity

    # Create new state with modified entities and relationships
    new_state = state.model_copy(
        update={
            "entities": new_entities,
            "relationships": new_relationships,
        }
    )

    return new_state, new_config
