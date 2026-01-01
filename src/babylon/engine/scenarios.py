"""Factory functions for creating simulation scenarios.

These functions create pre-configured WorldState and SimulationConfig
pairs for testing and exploration.

Sprint 6: Phase 2 integration testing support.
Multiverse Protocol: Scenario injection for counterfactual simulation.
"""

from __future__ import annotations

from babylon.config.defines import EconomyDefines, GameDefines, SurvivalDefines
from babylon.models.config import SimulationConfig
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import EdgeType, SectorType, SocialRole
from babylon.models.scenario import ScenarioConfig
from babylon.models.world_state import WorldState


def create_two_node_scenario(
    worker_wealth: float = 0.5,
    owner_wealth: float = 0.5,
    extraction_efficiency: float = 0.8,
    repression_level: float = 0.5,
    worker_organization: float = 0.1,
    worker_ideology: float = 0.0,
) -> tuple[WorldState, SimulationConfig, GameDefines]:
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
        Tuple of (WorldState, SimulationConfig, GameDefines) ready for step() function.

    Example:
        >>> state, config, defines = create_two_node_scenario()
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

    # PPP Model: Add WAGES edge from owner to worker
    # In MLM-TW theory, super-wages flow from the core bourgeoisie to workers.
    # This enables the PPP calculation to provide purchasing power bonus.
    wages = Relationship(
        source_id="C002",  # Owner pays
        target_id="C001",  # Worker receives
        edge_type=EdgeType.WAGES,
        description="Super-wages from imperial rent",
        value_flow=0.0,  # Calculated by step()
        tension=0.0,
    )

    # Material Reality Refactor: Create territory for production
    # Workers need land (biocapacity) to produce value
    territory = Territory(
        id="T001",
        name="Periphery Land",
        sector_type=SectorType.INDUSTRIAL,
        biocapacity=100.0,  # Fully charged at genesis
        max_biocapacity=100.0,
    )

    # TENANCY edge: Worker occupies territory (enables production)
    tenancy = Relationship(
        source_id="C001",
        target_id="T001",
        edge_type=EdgeType.TENANCY,
        description="Worker land tenancy",
        value_flow=0.0,
        tension=0.0,
    )

    # Create world state
    state = WorldState(
        tick=0,
        entities={"C001": worker, "C002": owner},
        territories={"T001": territory},
        relationships=[exploitation, solidarity, wages, tenancy],
        event_log=[],
    )

    # Create configuration (IT-level settings only)
    config = SimulationConfig()

    # Create GameDefines with scenario-specific game balance parameters
    # (Paradox Refactor: game math now lives in GameDefines, not SimulationConfig)
    economy_defines = EconomyDefines(
        extraction_efficiency=extraction_efficiency,
    )
    survival_defines = SurvivalDefines(
        default_repression=repression_level,
        default_subsistence=0.3,
        steepness_k=10.0,
    )
    defines = GameDefines(
        economy=economy_defines,
        survival=survival_defines,
        initial=GameDefines().initial.model_copy(
            update={
                "worker_wealth": worker_wealth,
                "owner_wealth": owner_wealth,
            }
        ),
    )

    return state, config, defines


def create_high_tension_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Create a scenario with high initial tension.

    Worker is poor, owner is rich, tension is already elevated.
    Useful for testing phase transitions and rupture conditions.

    Returns:
        Tuple of (WorldState, SimulationConfig, GameDefines) near rupture point.
    """
    state, config, defines = create_two_node_scenario(
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

    return state, config, defines


def create_labor_aristocracy_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Create a scenario with a labor aristocracy (Wc > Vc).

    Worker receives more than they produce, enabled by imperial rent
    from elsewhere. Tests consciousness decay mechanics.

    Returns:
        Tuple of (WorldState, SimulationConfig, GameDefines) with labor aristocracy.
    """
    return create_two_node_scenario(
        worker_wealth=0.8,  # Well-off worker
        owner_wealth=0.2,  # Owner extracting from elsewhere
        extraction_efficiency=0.3,  # Low local extraction
        repression_level=0.3,  # Low repression needed
        worker_organization=0.05,  # Very low organization
        worker_ideology=0.5,  # Leaning reactionary
    )


def create_imperial_circuit_scenario(
    periphery_wealth: float = 0.6,  # Calibrated: P(S|A) > P(S|R) prevents immediate revolt
    core_wealth: float = 0.9,
    comprador_cut: float = 0.90,  # Calibrated to prevent Comprador Liquidation
    imperial_rent_pool: float = 100.0,
    extraction_efficiency: float = 0.8,
    repression_level: float = 0.5,
    solidarity_strength: float = 0.0,
) -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Create the 4-node Imperial Circuit scenario.

    This scenario fixes the "Robin Hood" bug in create_two_node_scenario() where
    super-wages incorrectly flow to periphery workers. In MLM-TW theory, super-wages
    should only go to the Labor Aristocracy (core workers), NOT periphery workers.

    Topology:

    .. mermaid::

       graph LR
           Pw["P_w (Periphery Workers)"] -->|EXPLOITATION| Pc["P_c (Comprador)"]
           Pc -->|TRIBUTE| Cb["C_b (Core Bourgeoisie)"]
           Cb -->|WAGES| Cw["C_w (Labor Aristocracy)"]
           Cb -->|CLIENT_STATE| Pc
           Pw -.->|"SOLIDARITY (0.0)"| Cw

    Value Flow:

    1. EXPLOITATION: P_w -> P_c (imperial rent extraction from workers)
    2. TRIBUTE: P_c -> C_b (comprador sends tribute, keeps comprador_cut)
    3. WAGES: C_b -> C_w (super-wages to labor aristocracy, NOT periphery!)
    4. CLIENT_STATE: C_b -> P_c (subsidy to stabilize client state)
    5. SOLIDARITY: P_w -> C_w (potential internationalism, starts at 0)

    Args:
        periphery_wealth: Initial wealth for periphery worker P001 (default 0.1)
        core_wealth: Initial wealth for core bourgeoisie C001 (default 0.9)
        comprador_cut: Fraction comprador keeps from extracted value (default 0.90)
        imperial_rent_pool: Initial imperial rent pool (default 100.0)
        extraction_efficiency: Alpha in imperial rent formula (default 0.8)
        repression_level: Base repression level (default 0.5)
        solidarity_strength: Initial solidarity between P_w and C_w (default 0.0).
            When > 0, wage crisis routes to class consciousness (revolutionary).
            When = 0, wage crisis routes to national identity (fascist).

    Returns:
        Tuple of (WorldState, SimulationConfig, GameDefines) ready for step() function.

    Example:
        >>> state, config, defines = create_imperial_circuit_scenario()
        >>> # Verify wages go to labor aristocracy, not periphery
        >>> wages_edges = [r for r in state.relationships if r.edge_type == EdgeType.WAGES]
        >>> assert state.entities[wages_edges[0].target_id].role == SocialRole.LABOR_ARISTOCRACY
    """
    # C001: Periphery Worker (P_w) - source of extracted value
    periphery_worker = SocialClass(
        id="C001",
        name="Periphery Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        description="Exploited worker in the global periphery",
        wealth=periphery_wealth,
        ideology=-0.3,  # type: ignore[arg-type]  # Validator converts
        organization=0.1,
        repression_faced=repression_level,
        subsistence_threshold=0.3,  # High vulnerability
        p_acquiescence=0.0,
        p_revolution=0.0,
    )

    # C002: Comprador (P_c) - intermediary class, keeps a cut
    comprador = SocialClass(
        id="C002",
        name="Comprador",
        role=SocialRole.COMPRADOR_BOURGEOISIE,
        description="Intermediary extracting value for imperial core",
        wealth=periphery_wealth * 2,
        ideology=0.3,  # type: ignore[arg-type]  # Validator converts
        organization=0.5,
        repression_faced=repression_level * 0.6,  # Somewhat protected
        subsistence_threshold=0.2,
        p_acquiescence=0.0,
        p_revolution=0.0,
    )

    # C003: Core Bourgeoisie (C_b) - receives tribute, pays wages
    core_bourgeoisie = SocialClass(
        id="C003",
        name="Core Bourgeoisie",
        role=SocialRole.CORE_BOURGEOISIE,
        description="Capital owner in the imperial core",
        wealth=core_wealth,
        ideology=0.8,  # type: ignore[arg-type]  # Reactionary
        organization=0.8,
        repression_faced=0.1,  # Protected by the state
        subsistence_threshold=0.1,
        p_acquiescence=0.0,
        p_revolution=0.0,
    )

    # C004: Labor Aristocracy (C_w) - receives super-wages (THE FIX)
    labor_aristocracy = SocialClass(
        id="C004",
        name="Labor Aristocracy",
        role=SocialRole.LABOR_ARISTOCRACY,
        description="Core workers benefiting from imperial rent",
        wealth=core_wealth * 0.2,
        ideology=0.2,  # type: ignore[arg-type]  # Conservative but not reactionary
        organization=0.4,
        repression_faced=0.2,  # Low repression due to privilege
        subsistence_threshold=0.1,  # Low vulnerability due to super-wages
        p_acquiescence=0.0,
        p_revolution=0.0,
        population=1000,  # Population for decomposition tracking
    )

    # C005: Carceral Enforcer - DORMANT until CLASS_DECOMPOSITION
    # Receives 30% of Labor Aristocracy during decomposition (guards, cops)
    carceral_enforcer = SocialClass(
        id="C005",
        name="Carceral Enforcer",
        role=SocialRole.CARCERAL_ENFORCER,
        description="Guards and police managing surplus population",
        wealth=0.0,
        ideology=0.6,  # type: ignore[arg-type]  # Reactionary
        organization=0.7,  # Well-organized state apparatus
        repression_faced=0.0,  # They ARE the repression
        subsistence_threshold=0.1,
        p_acquiescence=0.0,
        p_revolution=0.0,
        population=0,  # DORMANT - populated during decomposition
        active=False,  # DORMANT - activated during decomposition
    )

    # C006: Internal Proletariat - DORMANT until CLASS_DECOMPOSITION
    # Receives 70% of Labor Aristocracy during decomposition (precariat, prisoners)
    internal_proletariat = SocialClass(
        id="C006",
        name="Internal Proletariat",
        role=SocialRole.INTERNAL_PROLETARIAT,
        description="Surplus population managed by carceral state",
        wealth=0.0,
        ideology=-0.2,  # type: ignore[arg-type]  # Potentially revolutionary
        organization=0.1,  # Atomized, disorganized
        repression_faced=0.9,  # Maximum repression
        subsistence_threshold=0.5,  # High vulnerability
        p_acquiescence=0.0,
        p_revolution=0.0,
        population=0,  # DORMANT - populated during decomposition
        active=False,  # DORMANT - activated during decomposition
    )

    # Edge 1: EXPLOITATION - P_w (C001) -> P_c (C002)
    exploitation = Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        description="Value flows from periphery to comprador",
        value_flow=0.0,
        tension=0.0,
    )

    # Edge 2: TRIBUTE - P_c (C002) -> C_b (C003)
    tribute = Relationship(
        source_id="C002",
        target_id="C003",
        edge_type=EdgeType.TRIBUTE,
        description="Imperial rent transfer (minus comprador cut)",
        value_flow=0.0,
        tension=0.0,
    )

    # Edge 3: WAGES - C_b (C003) -> C_w (C004) - THE FIX: targets labor aristocracy, NOT periphery
    wages = Relationship(
        source_id="C003",
        target_id="C004",
        edge_type=EdgeType.WAGES,
        description="Super-wages buying loyalty",
        value_flow=0.0,
        tension=0.0,
    )

    # Edge 4: CLIENT_STATE - C_b (C003) -> P_c (C002)
    client_state = Relationship(
        source_id="C003",
        target_id="C002",
        edge_type=EdgeType.CLIENT_STATE,
        description="Subsidy for client state stabilization",
        value_flow=0.0,
        tension=0.0,
        subsidy_cap=10.0,
    )

    # Edge 5: SOLIDARITY - P_w (C001) -> C_w (C004)
    solidarity = Relationship(
        source_id="C001",
        target_id="C004",
        edge_type=EdgeType.SOLIDARITY,
        description="Potential internationalism",
        value_flow=0.0,
        tension=0.0,
        solidarity_strength=solidarity_strength,  # Configurable (default 0.0)
    )

    # Material Reality Refactor: Create territories for production
    # Workers need land (biocapacity) to produce value
    # Two territories: periphery for C001, core for C004
    periphery_land = Territory(
        id="T001",
        name="Periphery Land",
        sector_type=SectorType.INDUSTRIAL,
        biocapacity=100.0,  # Fully charged at genesis
        max_biocapacity=100.0,
    )
    core_land = Territory(
        id="T002",
        name="Core Land",
        sector_type=SectorType.RESIDENTIAL,
        biocapacity=100.0,  # Fully charged at genesis
        max_biocapacity=100.0,
    )

    # TENANCY edges: Workers occupy territories (enables production)
    # C001 (Periphery Worker) -> T001 (Periphery Land)
    periphery_tenancy = Relationship(
        source_id="C001",
        target_id="T001",
        edge_type=EdgeType.TENANCY,
        description="Periphery worker land tenancy",
        value_flow=0.0,
        tension=0.0,
    )
    # C004 (Labor Aristocracy) -> T002 (Core Land)
    core_tenancy = Relationship(
        source_id="C004",
        target_id="T002",
        edge_type=EdgeType.TENANCY,
        description="Labor aristocracy land tenancy",
        value_flow=0.0,
        tension=0.0,
    )

    # Create world state with 6 entities (4 active + 2 dormant), 2 territories, and 7 edges
    state = WorldState(
        tick=0,
        entities={
            "C001": periphery_worker,
            "C002": comprador,
            "C003": core_bourgeoisie,
            "C004": labor_aristocracy,
            "C005": carceral_enforcer,  # DORMANT - activated during CLASS_DECOMPOSITION
            "C006": internal_proletariat,  # DORMANT - activated during CLASS_DECOMPOSITION
        },
        territories={
            "T001": periphery_land,
            "T002": core_land,
        },
        relationships=[
            exploitation,
            tribute,
            wages,
            client_state,
            solidarity,
            periphery_tenancy,
            core_tenancy,
        ],
        event_log=[],
    )

    # Create configuration (IT-level settings only)
    config = SimulationConfig()

    # Create GameDefines with scenario-specific game balance parameters
    # (Paradox Refactor: game math now lives in GameDefines, not SimulationConfig)
    economy_defines = EconomyDefines(
        extraction_efficiency=extraction_efficiency,
        comprador_cut=comprador_cut,
        superwage_multiplier=1.5,  # High PPP for labor aristocracy
        initial_rent_pool=imperial_rent_pool,
    )
    survival_defines = SurvivalDefines(
        default_repression=repression_level,
        default_subsistence=0.3,
        steepness_k=10.0,
    )
    defines = GameDefines(
        economy=economy_defines,
        survival=survival_defines,
    )

    return state, config, defines


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
    defines: GameDefines,
    scenario: ScenarioConfig,
) -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Apply scenario modifiers to WorldState, SimulationConfig, and GameDefines.

    This function transforms a base (state, config, defines) triple into a
    counterfactual scenario by applying the three modifiers:

    1. superwage_multiplier: Passed to GameDefines.economy.superwage_multiplier.
       - PPP Model: Affects worker effective wealth via PPP calculation.
       - Paradox Refactor: Game math lives in GameDefines, not SimulationConfig.
       - economic.py reads from services.defines.economy.superwage_multiplier.

    2. solidarity_index: Sets solidarity_strength on all SOLIDARITY edges.
       - Does not affect EXPLOITATION or other edge types.

    3. repression_capacity: Updates repression_faced on all SocialClass entities
       AND repression_level in SimulationConfig.

    Args:
        state: Base WorldState to modify (not mutated)
        config: Base SimulationConfig to modify (not mutated)
        defines: Base GameDefines to modify (not mutated)
        scenario: ScenarioConfig with modifier values

    Returns:
        Tuple of (new_state, new_config, new_defines) with scenario modifiers applied.

    Example:
        >>> state, config, defines = create_two_node_scenario()
        >>> scenario = ScenarioConfig(name="test", superwage_multiplier=1.5)
        >>> new_state, new_config, new_defines = apply_scenario(state, config, defines, scenario)
        >>> new_defines.economy.superwage_multiplier  # Will be 1.5 (for PPP calculation)
    """
    # 1. Apply superwage_multiplier to GameDefines.economy (Mikado Refactor)
    # Paradox Refactor: Game math lives in GameDefines, NOT SimulationConfig.
    # economic.py reads from services.defines.economy.superwage_multiplier.
    new_economy = defines.economy.model_copy(
        update={"superwage_multiplier": scenario.superwage_multiplier}
    )
    new_defines = defines.model_copy(update={"economy": new_economy})

    # 2. Apply repression_capacity to repression_level
    new_repression_level = scenario.repression_capacity

    # Create new config with modified values
    # Note: superwage_multiplier is NO LONGER set here (moved to GameDefines)
    new_config = config.model_copy(
        update={
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

    return new_state, new_config, new_defines
