"""Enumeration types for the Babylon simulation.

These StrEnums define the categorical types used throughout the simulation.
All values are lowercase snake_case for JSON serialization compatibility.

Enums defined:
- SocialRole: Class position in the world system (MLM-TW categories)
- EdgeType: Nature of relationships between entities
- IntensityLevel: Contradiction/tension intensity scale
- ResolutionType: How contradictions can resolve
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
    """

    CORE_BOURGEOISIE = "core_bourgeoisie"
    PERIPHERY_PROLETARIAT = "periphery_proletariat"
    LABOR_ARISTOCRACY = "labor_aristocracy"
    PETTY_BOURGEOISIE = "petty_bourgeoisie"
    LUMPENPROLETARIAT = "lumpenproletariat"


class EdgeType(StrEnum):
    """Nature of relationships between entities.

    These are the fundamental relationship types that form edges
    in the simulation's NetworkX graph.

    Values:
        EXPLOITATION: Value extraction (imperial rent flows along these edges)
        SOLIDARITY: Mutual support and class consciousness
        REPRESSION: State violence directed at a class
        COMPETITION: Market rivalry between entities
    """

    EXPLOITATION = "exploitation"
    SOLIDARITY = "solidarity"
    REPRESSION = "repression"
    COMPETITION = "competition"


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
    """

    SURPLUS_EXTRACTION = "surplus_extraction"
