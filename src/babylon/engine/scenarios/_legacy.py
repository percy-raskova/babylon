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
from babylon.models.entity_registry import (
    CARCERAL_ENFORCER_ID,
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    INTERNAL_PROLETARIAT_ID,
    LABOR_ARISTOCRACY_ID,
    PERIPHERY_WORKER_ID,
)
from babylon.models.enums import EdgeType, SectorType, SocialRole, TerritoryType
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
        id=PERIPHERY_WORKER_ID,
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
        id=COMPRADOR_ID,
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
        source_id=PERIPHERY_WORKER_ID,
        target_id=COMPRADOR_ID,
        edge_type=EdgeType.EXPLOITATION,
        description="Imperial rent extraction",
        value_flow=0.0,  # Will be calculated by step()
        tension=0.0,  # Will accumulate over time
    )

    # NOTE (Design B, fix/from-graph-safety): this scenario historically
    # carried a SOLIDARITY relationship on the SAME (owner, worker) pair as
    # the WAGES edge below ("Bug Fix: Add SOLIDARITY edge so solidarity_index
    # affects P(S|R)"). BabylonGraph stores one edge per (source, target)
    # pair; the WAGES payload (added last, identical key set) fully
    # overwrote the SOLIDARITY payload on every to_graph(), so the
    # solidarity edge was silently dead in graph form — solidarity_index
    # never actually reached the dynamics, and the two_node.json baseline
    # encodes wages-only behaviour. The to_graph pre-scan now rejects such
    # collisions loudly, so the dead relationship is removed: with only two
    # entities every candidate pair collides with EXPLOITATION or WAGES.
    # Re-introducing live two-node solidarity (distinct topology, baseline
    # regen) is a spec/Phase-2.R decision, not a data patch.

    # PPP Model: Add WAGES edge from owner to worker
    # In MLM-TW theory, super-wages flow from the core bourgeoisie to workers.
    # This enables the PPP calculation to provide purchasing power bonus.
    wages = Relationship(
        source_id=COMPRADOR_ID,  # Owner pays
        target_id=PERIPHERY_WORKER_ID,  # Worker receives
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
        source_id=PERIPHERY_WORKER_ID,
        target_id="T001",
        edge_type=EdgeType.TENANCY,
        description="Worker land tenancy",
        value_flow=0.0,
        tension=0.0,
    )

    # Create world state
    state = WorldState(
        tick=0,
        entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
        territories={"T001": territory},
        relationships=[exploitation, wages, tenancy],
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
        id=PERIPHERY_WORKER_ID,
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
        id=COMPRADOR_ID,
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
        id=CORE_BOURGEOISIE_ID,
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
        id=LABOR_ARISTOCRACY_ID,
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
        id=CARCERAL_ENFORCER_ID,
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
        id=INTERNAL_PROLETARIAT_ID,
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
        source_id=PERIPHERY_WORKER_ID,
        target_id=COMPRADOR_ID,
        edge_type=EdgeType.EXPLOITATION,
        description="Value flows from periphery to comprador",
        value_flow=0.0,
        tension=0.0,
    )

    # Edge 2: TRIBUTE - P_c (C002) -> C_b (C003)
    tribute = Relationship(
        source_id=COMPRADOR_ID,
        target_id=CORE_BOURGEOISIE_ID,
        edge_type=EdgeType.TRIBUTE,
        description="Imperial rent transfer (minus comprador cut)",
        value_flow=0.0,
        tension=0.0,
    )

    # Edge 3: WAGES - C_b (C003) -> C_w (C004) - THE FIX: targets labor aristocracy, NOT periphery
    wages = Relationship(
        source_id=CORE_BOURGEOISIE_ID,
        target_id=LABOR_ARISTOCRACY_ID,
        edge_type=EdgeType.WAGES,
        description="Super-wages buying loyalty",
        value_flow=0.0,
        tension=0.0,
    )

    # Edge 4: CLIENT_STATE - C_b (C003) -> P_c (C002)
    client_state = Relationship(
        source_id=CORE_BOURGEOISIE_ID,
        target_id=COMPRADOR_ID,
        edge_type=EdgeType.CLIENT_STATE,
        description="Subsidy for client state stabilization",
        value_flow=0.0,
        tension=0.0,
        subsidy_cap=10.0,
    )

    # Edge 5: SOLIDARITY - P_w (C001) -> C_w (C004)
    solidarity = Relationship(
        source_id=PERIPHERY_WORKER_ID,
        target_id=LABOR_ARISTOCRACY_ID,
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
        source_id=PERIPHERY_WORKER_ID,
        target_id="T001",
        edge_type=EdgeType.TENANCY,
        description="Periphery worker land tenancy",
        value_flow=0.0,
        tension=0.0,
    )
    # C004 (Labor Aristocracy) -> T002 (Core Land)
    core_tenancy = Relationship(
        source_id=LABOR_ARISTOCRACY_ID,
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
            PERIPHERY_WORKER_ID: periphery_worker,
            COMPRADOR_ID: comprador,
            CORE_BOURGEOISIE_ID: core_bourgeoisie,
            LABOR_ARISTOCRACY_ID: labor_aristocracy,
            CARCERAL_ENFORCER_ID: carceral_enforcer,  # DORMANT - activated during CLASS_DECOMPOSITION
            INTERNAL_PROLETARIAT_ID: internal_proletariat,  # DORMANT - activated during CLASS_DECOMPOSITION
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
# US CONUS SCENARIO: Full Hexagonal Coverage
# =============================================================================

# Major US metro centroids: (lat, lon, population)
_METRO_CENTROIDS: list[tuple[str, float, float, int]] = [
    ("New York", 40.71, -74.01, 8_300_000),
    ("Los Angeles", 34.05, -118.24, 3_900_000),
    ("Chicago", 41.88, -87.63, 2_700_000),
    ("Houston", 29.76, -95.37, 2_300_000),
    ("Phoenix", 33.45, -112.07, 1_600_000),
    ("Philadelphia", 39.95, -75.17, 1_600_000),
    ("San Antonio", 29.42, -98.49, 1_500_000),
    ("San Diego", 32.72, -117.16, 1_400_000),
    ("Dallas", 32.78, -96.80, 1_300_000),
    ("San Jose", 37.34, -121.89, 1_000_000),
    ("Austin", 30.27, -97.74, 980_000),
    ("Jacksonville", 30.33, -81.66, 950_000),
    ("San Francisco", 37.77, -122.42, 870_000),
    ("Seattle", 47.61, -122.33, 750_000),
    ("Denver", 39.74, -104.99, 720_000),
    ("Washington DC", 38.91, -77.04, 700_000),
    ("Nashville", 36.16, -86.78, 690_000),
    ("Atlanta", 33.75, -84.39, 500_000),
    ("Detroit", 42.33, -83.05, 640_000),
    ("Miami", 25.76, -80.19, 440_000),
]

# Named CONUS regions by lat/lon bucket
_REGIONS: list[tuple[str, float, float, float, float]] = [
    # (name, lat_min, lat_max, lon_min, lon_max)
    ("Pacific Northwest", 42.0, 50.0, -125.0, -116.0),
    ("California", 32.0, 42.0, -125.0, -114.0),
    ("Mountain West", 37.0, 50.0, -116.0, -104.0),
    ("Southwest", 31.0, 37.0, -114.0, -104.0),
    ("Great Plains", 37.0, 50.0, -104.0, -95.0),
    ("Texas Gulf", 25.0, 37.0, -104.0, -93.0),
    ("Upper Midwest", 42.0, 50.0, -95.0, -82.0),
    ("Heartland", 36.0, 42.0, -95.0, -82.0),
    ("Deep South", 29.0, 36.0, -93.0, -82.0),
    ("Southeast", 25.0, 36.0, -82.0, -75.0),
    ("Mid-Atlantic", 36.0, 42.0, -82.0, -73.0),
    ("Northeast", 42.0, 50.0, -82.0, -66.0),
]


def _get_region_name(lat: float, lon: float) -> str:
    """Classify a lat/lon into a named CONUS region.

    Args:
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        Region name string.
    """
    for name, lat_min, lat_max, lon_min, lon_max in _REGIONS:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return name
    return "Frontier"


def _compute_metro_influence(lat: float, lon: float) -> float:
    """Compute population estimate via Gaussian-weighted metro proximity.

    Each metro contributes population inversely proportional to distance
    squared (Gaussian kernel with sigma=2.0 degrees ~ 200km).

    Args:
        lat: Hex centroid latitude.
        lon: Hex centroid longitude.

    Returns:
        Estimated population as a float (unscaled metro influence sum).
    """
    import math

    sigma = 2.0  # degrees (~200km effective radius)
    total = 0.0
    for _name, m_lat, m_lon, m_pop in _METRO_CENTROIDS:
        d2 = (lat - m_lat) ** 2 + (lon - m_lon) ** 2
        weight = math.exp(-d2 / (2.0 * sigma**2))
        total += weight * m_pop
    return total


def _classify_hex(
    lat: float,
    lon: float,
    metro_influence: float,
) -> tuple[SectorType, TerritoryType, float, float]:
    """Derive sector type, territory type, rent level, and biocapacity from geography.

    Args:
        lat: Hex centroid latitude.
        lon: Hex centroid longitude.
        metro_influence: Pre-computed metro influence score.

    Returns:
        Tuple of (sector_type, territory_type, rent_level, biocapacity).
    """
    # Sector type: metro-proximate hexes are commercial/residential
    if metro_influence > 500_000:
        sector = SectorType.COMMERCIAL
    elif metro_influence > 100_000:
        sector = SectorType.RESIDENTIAL
    elif metro_influence > 20_000:
        sector = SectorType.INDUSTRIAL
    else:
        # Rural/agricultural — map to INDUSTRIAL (closest available enum)
        sector = SectorType.INDUSTRIAL

    # Territory type: metro = CORE, rural/border = PERIPHERY
    territory_type = TerritoryType.CORE if metro_influence > 50_000 else TerritoryType.PERIPHERY

    # Rent level: proportional to metro influence (log-scaled, 0.5-10.0)
    import math

    rent = min(10.0, max(0.5, math.log1p(metro_influence / 100_000)))

    # Biocapacity: higher in agricultural heartland (Great Plains, Midwest)
    # Lower in arid Southwest and dense urban areas
    # Base from latitude/longitude position
    is_heartland = 35.0 <= lat <= 48.0 and -104.0 <= lon <= -82.0
    is_arid = lat < 37.0 and lon < -104.0
    if is_heartland:
        biocap = 150.0
    elif is_arid:
        biocap = 40.0
    else:
        biocap = 100.0
    # Dense urban areas have reduced biocapacity
    if metro_influence > 500_000:
        biocap *= 0.3

    return sector, territory_type, rent, biocap


def _create_us_territories() -> dict[str, Territory]:
    """Generate ~1100 H3 resolution-3 Territory objects covering CONUS.

    Returns:
        Dict mapping H3 cell ID to Territory.
    """
    import h3

    # CONUS bounding polygon (rectangular approximation)
    polygon = h3.LatLngPoly([(24.5, -124.7), (49.4, -124.7), (49.4, -66.9), (24.5, -66.9)])
    cells = h3.polygon_to_cells(polygon, 3)

    territories: dict[str, Territory] = {}
    for cell in cells:
        lat, lon = h3.cell_to_latlng(cell)
        metro_inf = _compute_metro_influence(lat, lon)
        sector, t_type, rent, biocap = _classify_hex(lat, lon, metro_inf)
        region = _get_region_name(lat, lon)
        pop = max(100, int(metro_inf / 10))  # Scale down to per-hex population

        territories[cell] = Territory(
            id=cell,
            h3_index=cell,
            name=f"{region} {sector.value.title()}",
            sector_type=sector,
            territory_type=t_type,
            population=pop,
            rent_level=rent,
            biocapacity=biocap,
            max_biocapacity=biocap,
            heat=0.0,
        )
    return territories


def create_us_scenario(
    extraction_efficiency: float = 0.8,
    repression_level: float = 0.5,
    solidarity_strength: float = 0.0,
) -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Create a full CONUS hex scenario with ~1100 H3 territories.

    Generates H3 resolution-3 hexagonal tiles covering the continental US.
    Each hex has geographic-derived economic properties (population, rent,
    biocapacity, sector type) computed from proximity to 20 metro centroids.

    Reuses the standard 6-class imperial circuit entities (4 active + 2 dormant)
    and 5 core relationship edges, adding TENANCY edges connecting classes to
    territory clusters based on class role.

    Args:
        extraction_efficiency: Alpha in imperial rent formula (default 0.8).
        repression_level: Base repression level (default 0.5).
        solidarity_strength: Initial solidarity P_w->C_w (default 0.0).

    Returns:
        Tuple of (WorldState, SimulationConfig, GameDefines).
    """
    # Generate territories
    territories = _create_us_territories()
    territory_ids = list(territories.keys())

    # Reuse the 6 social classes from the imperial circuit scenario
    state, config, defines = create_imperial_circuit_scenario(
        extraction_efficiency=extraction_efficiency,
        repression_level=repression_level,
        solidarity_strength=solidarity_strength,
    )

    # Build TENANCY edges connecting classes to territory subsets
    tenancy_edges = _assign_tenancy_edges(territories, territory_ids)

    # Combine all relationships: original edges (minus old T001/T002 tenancies) + new
    core_relationships = [r for r in state.relationships if r.edge_type != EdgeType.TENANCY]

    return (
        WorldState(
            tick=0,
            entities=state.entities,
            territories=territories,
            relationships=[*core_relationships, *tenancy_edges],
            event_log=[],
        ),
        config,
        defines,
    )


def _assign_tenancy_edges(
    territories: dict[str, Territory],
    territory_ids: list[str],
) -> list[Relationship]:
    """Create TENANCY edges connecting social classes to territory clusters.

    Assignment logic by class role:
    - Core Bourgeoisie: top 5% highest-rent hexes (financial centers)
    - Labor Aristocracy: next 20% highest-rent (suburban residential)
    - Periphery Worker: industrial/low-rent hexes (bottom 50%)
    - Comprador: mid-tier commercial hexes (10-30th percentile by rent)

    Args:
        territories: Full territory dict.
        territory_ids: Ordered list of territory IDs.

    Returns:
        List of TENANCY Relationship edges.
    """
    # Sort by rent to partition into class zones
    sorted_ids = sorted(territory_ids, key=lambda tid: territories[tid].rent_level, reverse=True)
    n = len(sorted_ids)

    # Partition into class zones by rent percentile
    bourgeois_ids = sorted_ids[: max(1, n // 20)]  # top 5%
    aristocracy_ids = sorted_ids[n // 20 : n // 5]  # 5-20%
    comprador_ids = sorted_ids[n // 5 : 3 * n // 10]  # 20-30%
    worker_ids = sorted_ids[n // 2 :]  # bottom 50%

    edges: list[Relationship] = []

    # Each class gets TENANCY edges to its assigned territories
    _class_zones = [
        (CORE_BOURGEOISIE_ID, bourgeois_ids, "Core bourgeoisie financial zone"),
        (LABOR_ARISTOCRACY_ID, aristocracy_ids, "Labor aristocracy suburban zone"),
        (COMPRADOR_ID, comprador_ids, "Comprador commercial zone"),
        (PERIPHERY_WORKER_ID, worker_ids, "Periphery worker industrial zone"),
    ]

    for class_id, zone_ids, description in _class_zones:
        for tid in zone_ids:
            edges.append(
                Relationship(
                    source_id=class_id,
                    target_id=tid,
                    edge_type=EdgeType.TENANCY,
                    description=description,
                    value_flow=0.0,
                    tension=0.0,
                )
            )

    return edges


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
