"""Enumeration types for the Babylon simulation.

These StrEnums define the categorical types used throughout the simulation.
All values are lowercase snake_case for JSON serialization compatibility.

Enums defined:
- SocialRole: Class position in the world system (MLM-TW categories)
- EdgeType: Nature of relationships between entities
- IntensityLevel: Contradiction/tension intensity scale
- ResolutionType: How contradictions can resolve
- EventType: Types of simulation events for the narrative layer
- OperationalProfile: Territory visibility stance (Sprint 3.5.1)
- SectorType: Strategic sector categories (Sprint 3.5.1)
- TerritoryType: Settler-colonial hierarchy classification (Sprint 3.7)
"""

from enum import StrEnum


class SocialRole(StrEnum):
    """Class position in the world system.

    Based on Marxist-Leninist-Maoist Third Worldist (MLM-TW) theory,
    classes are defined by their relationship to production AND their
    position in the imperial hierarchy.

    Values:
        CORE_BOURGEOISIE: Owns means of production in imperial core
        PERIPHERY_PROLETARIAT: Sells labor in exploited periphery
        LABOR_ARISTOCRACY: Core workers benefiting from imperial rent
        PETTY_BOURGEOISIE: Small owners, professionals, shopkeepers
        LUMPENPROLETARIAT: Outside formal economy, precarious existence
        COMPRADOR_BOURGEOISIE: Intermediary class in periphery, collaborates with imperial core
    """

    CORE_BOURGEOISIE = "core_bourgeoisie"
    PERIPHERY_PROLETARIAT = "periphery_proletariat"
    LABOR_ARISTOCRACY = "labor_aristocracy"
    PETTY_BOURGEOISIE = "petty_bourgeoisie"
    LUMPENPROLETARIAT = "lumpenproletariat"
    COMPRADOR_BOURGEOISIE = "comprador_bourgeoisie"


class EdgeType(StrEnum):
    """Nature of relationships between entities.

    These are the fundamental relationship types that form edges
    in the simulation's NetworkX graph.

    Values:
        EXPLOITATION: Value extraction (imperial rent flows along these edges)
        SOLIDARITY: Mutual support and class consciousness
        REPRESSION: State violence directed at a class
        COMPETITION: Market rivalry between entities
        TRIBUTE: Value flow from periphery comprador to core (comprador keeps cut)
        WAGES: Core bourgeoisie paying core workers (super-wages from imperial rent)
        CLIENT_STATE: Imperial subsidy to maintain client state stability
        TENANCY: Occupant -> Territory relationship (Sprint 3.5.1)
        ADJACENCY: Territory -> Territory spatial connectivity (Sprint 3.5.1)
    """

    EXPLOITATION = "exploitation"
    SOLIDARITY = "solidarity"
    REPRESSION = "repression"
    COMPETITION = "competition"
    TRIBUTE = "tribute"
    WAGES = "wages"
    CLIENT_STATE = "client_state"
    TENANCY = "tenancy"
    ADJACENCY = "adjacency"


class IntensityLevel(StrEnum):
    """Intensity scale for contradictions and tensions.

    Contradictions exist on a spectrum from dormant (latent potential)
    to critical (imminent rupture). This enum provides discrete levels
    for game mechanics while the underlying simulation may use
    continuous float values.

    Values:
        DORMANT: Contradiction exists but not yet manifest
        LOW: Minor tensions, easily managed
        MEDIUM: Noticeable conflict, requires attention
        HIGH: Serious crisis, intervention needed
        CRITICAL: Rupture imminent, phase transition likely
    """

    DORMANT = "dormant"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionType(StrEnum):
    """How contradictions can resolve.

    Based on dialectical materialism, contradictions resolve through
    one of three mechanisms. The resolution type determines what
    happens to the system after a contradiction reaches critical intensity.

    Values:
        SYNTHESIS: Dialectical resolution - opposites unite at higher level
        RUPTURE: Revolutionary break - system undergoes fundamental change
        SUPPRESSION: Forced dormancy - contradiction remains but is contained
    """

    SYNTHESIS = "synthesis"
    RUPTURE = "rupture"
    SUPPRESSION = "suppression"


class EventType(StrEnum):
    """Types of simulation events for the narrative layer.

    These event types are published to the EventBus when significant
    state changes occur, enabling the AI Observer to generate narrative.

    Values:
        SURPLUS_EXTRACTION: Imperial rent extracted from worker to owner
        IMPERIAL_SUBSIDY: Wealth converted to suppression to stabilize client state
        SOLIDARITY_AWAKENING: Periphery worker enters active struggle (consciousness >= threshold)
        CONSCIOUSNESS_TRANSMISSION: Consciousness flows via SOLIDARITY edge from periphery to core
        MASS_AWAKENING: Target consciousness crosses mass awakening threshold
        ECONOMIC_CRISIS: Imperial rent pool depleted below critical threshold (Sprint 3.4.4)
        EXCESSIVE_FORCE: State violence "spark" - police brutality event (Agency Layer)
        UPRISING: Mass insurrection triggered by spark + accumulated agitation (Agency Layer)
        SOLIDARITY_SPIKE: Solidarity infrastructure built through shared struggle (Agency Layer)
    """

    SURPLUS_EXTRACTION = "surplus_extraction"
    IMPERIAL_SUBSIDY = "imperial_subsidy"
    SOLIDARITY_AWAKENING = "solidarity_awakening"
    CONSCIOUSNESS_TRANSMISSION = "consciousness_transmission"
    MASS_AWAKENING = "mass_awakening"
    ECONOMIC_CRISIS = "economic_crisis"  # Sprint 3.4.4 - Dynamic Balance
    EXCESSIVE_FORCE = "excessive_force"  # Agency Layer - The Spark (Police Brutality)
    UPRISING = "uprising"  # Agency Layer - The Explosion (Riot/Insurrection)
    SOLIDARITY_SPIKE = "solidarity_spike"  # Agency Layer - The Bridge Building


class OperationalProfile(StrEnum):
    """Operational profile for territory visibility.

    Sprint 3.5.1: Layer 0 - The Territorial Substrate.
    The stance system trades visibility for recruitment:
    - LOW_PROFILE: Safe from eviction, low recruitment (opaque)
    - HIGH_PROFILE: High recruitment, high heat (transparent)

    "Legibility over Stealth" - The State knows where you are.
    The game is about staying below the repression threshold.

    Values:
        LOW_PROFILE: "We are just a reading group/community center."
        HIGH_PROFILE: "We are a Revolutionary Cell."
    """

    LOW_PROFILE = "low_profile"
    HIGH_PROFILE = "high_profile"


class SectorType(StrEnum):
    """Strategic sector categories for territories.

    Sprint 3.5.1: Layer 0 - The Territorial Substrate.
    Sector types determine the economic and social character of territories
    and affect the dynamics of recruitment, eviction, and spillover.

    Values:
        INDUSTRIAL: Factories, warehouses, production centers
        RESIDENTIAL: Housing, neighborhoods, population centers
        COMMERCIAL: Shops, markets, service industries
        UNIVERSITY: Educational institutions, intellectuals
        DOCKS: Ports, logistics hubs, trade nodes
        GOVERNMENT: State buildings, bureaucracy, military
    """

    INDUSTRIAL = "industrial"
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    UNIVERSITY = "university"
    DOCKS = "docks"
    GOVERNMENT = "government"


class TerritoryType(StrEnum):
    """Territory classification in the settler-colonial hierarchy.

    Sprint 3.7: The Carceral Geography - Necropolitical Triad.

    The settler-colonial state manages population through territorial
    classification. Displaced populations flow from productive zones
    to containment/elimination zones following the logic of capital.

    Values:
        CORE: High value, low heat. Labor aristocracy destination.
            The suburbs, gated communities, gentrified zones.
        PERIPHERY: Low value, high heat. Source of cheap labor.
            The ghetto, favela, global south production zones.
        RESERVATION: Containment. High subsistence, no labor value.
            The reservation system - warehousing surplus population.
        PENAL_COLONY: Extraction. Forced labor, suppresses Organization.
            The prison-industrial complex - carceral extraction.
        CONCENTRATION_CAMP: Elimination. High population decay, generates Terror.
            The final solution - necropolitical endpoint.
    """

    CORE = "core"
    PERIPHERY = "periphery"
    RESERVATION = "reservation"
    PENAL_COLONY = "penal_colony"
    CONCENTRATION_CAMP = "concentration_camp"
