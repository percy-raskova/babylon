"""Factory functions for creating simulation scenarios.

These functions create pre-configured WorldState and SimulationConfig
pairs for testing and exploration.

Sprint 6: Phase 2 integration testing support.
"""

from __future__ import annotations

from babylon.models.config import SimulationConfig
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import EdgeType, SocialRole
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
        ideology=worker_ideology,
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
        ideology=0.5,  # Leaning reactionary
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

    # Create world state
    state = WorldState(
        tick=0,
        entities={"C001": worker, "C002": owner},
        relationships=[exploitation],
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
