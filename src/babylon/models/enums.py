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
- EdgeMode: Qualitative contradiction mode on edges (Feature 002)
- ContradictionCharacter: Antagonistic vs non-antagonistic flag (Feature 002)
- DispossessionType: Categories of ongoing primitive accumulation (Feature 021)
- ExploitationMode: Surplus value extraction mode classification (Feature 021)
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
        INTERNAL_PROLETARIAT: Core workers outside LA (precariat, unemployed, incarcerated)
        CARCERAL_ENFORCER: Guards, cops, prison staff (repressive apparatus)

    Terminal Crisis Dynamics (ai-docs/terminal-crisis-dynamics.md):
        When peripheral extraction fails and super-wages deplete, the Labor
        Aristocracy decomposes into CARCERAL_ENFORCER (30%) and INTERNAL_PROLETARIAT
        (70%). This models the carceral turn from productive to coercive labor.
    """

    CORE_BOURGEOISIE = "core_bourgeoisie"
    PERIPHERY_PROLETARIAT = "periphery_proletariat"
    LABOR_ARISTOCRACY = "labor_aristocracy"
    PETTY_BOURGEOISIE = "petty_bourgeoisie"
    LUMPENPROLETARIAT = "lumpenproletariat"
    COMPRADOR_BOURGEOISIE = "comprador_bourgeoisie"
    # Terminal Crisis Dynamics - Carceral Turn
    INTERNAL_PROLETARIAT = "internal_proletariat"
    CARCERAL_ENFORCER = "carceral_enforcer"


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
        ECOLOGICAL_OVERSHOOT: Consumption exceeds biocapacity (Slice 1.4 - Metabolic Rift)
        EXCESSIVE_FORCE: State violence "spark" - police brutality event (Agency Layer)
        UPRISING: Mass insurrection triggered by spark + accumulated agitation (Agency Layer)
        SOLIDARITY_SPIKE: Solidarity infrastructure built through shared struggle (Agency Layer)
        POWER_VACUUM: Comprador insolvency triggers George Jackson Bifurcation
        REVOLUTIONARY_OFFENSIVE: Organized labor seizes opportunity during power vacuum
        FASCIST_REVANCHISM: Core workers react with nationalism during power vacuum
        RUPTURE: Contradiction tension reached critical threshold, triggering phase transition
        PHASE_TRANSITION: Topology percolation threshold crossed (Sprint 3.3)
        ENTITY_DEATH: Entity starved (wealth < consumption_needs) - Material Reality Refactor
        POPULATION_DEATH: Probabilistic mortality from inequality (Mass Line Refactor)
        POPULATION_ATTRITION: Grinding Attrition deaths from coverage deficit (Mass Line Phase 3)

    Terminal Crisis Dynamics (ai-docs/terminal-crisis-dynamics.md):
        PERIPHERAL_REVOLT: Periphery severs EXPLOITATION edges when P(S|R) > P(S|A)
        SUPERWAGE_CRISIS: Core bourgeoisie can't afford super-wages (pool exhausted)
        CLASS_DECOMPOSITION: Labor aristocracy splits into enforcers + internal proletariat
        CONTROL_RATIO_CRISIS: Prisoners exceed guard capacity (ratio inverted)
        TERMINAL_DECISION: System bifurcates to revolution or genocide
    """

    SURPLUS_EXTRACTION = "surplus_extraction"
    IMPERIAL_SUBSIDY = "imperial_subsidy"
    SOLIDARITY_AWAKENING = "solidarity_awakening"
    CONSCIOUSNESS_TRANSMISSION = "consciousness_transmission"
    MASS_AWAKENING = "mass_awakening"
    ECONOMIC_CRISIS = "economic_crisis"  # Sprint 3.4.4 - Dynamic Balance
    ECOLOGICAL_OVERSHOOT = "ecological_overshoot"  # Slice 1.4 - Metabolic Rift
    EXCESSIVE_FORCE = "excessive_force"  # Agency Layer - The Spark (Police Brutality)
    UPRISING = "uprising"  # Agency Layer - The Explosion (Riot/Insurrection)
    SOLIDARITY_SPIKE = "solidarity_spike"  # Agency Layer - The Bridge Building
    POWER_VACUUM = "power_vacuum"  # George Jackson Bifurcation - Comprador insolvency
    REVOLUTIONARY_OFFENSIVE = (
        "revolutionary_offensive"  # Jackson: Organized labor seizes opportunity
    )
    FASCIST_REVANCHISM = "fascist_revanchism"  # Jackson: Core reacts with nationalism
    RUPTURE = "rupture"  # Contradiction rupture - tension reached critical threshold
    PHASE_TRANSITION = "phase_transition"  # Topology: percolation threshold crossed
    ENDGAME_REACHED = "endgame_reached"  # Game ended (victory/defeat condition met)
    ENTITY_DEATH = "entity_death"  # Material Reality: Entity starved (wealth < consumption)
    POPULATION_DEATH = "population_death"  # Mass Line: Probabilistic mortality from inequality
    POPULATION_ATTRITION = "population_attrition"  # Mass Line Phase 3: Coverage deficit deaths
    # Terminal Crisis Dynamics - Endgame Arc
    PERIPHERAL_REVOLT = "peripheral_revolt"  # Periphery severs EXPLOITATION edges
    SUPERWAGE_CRISIS = "superwage_crisis"  # C_b can't afford super-wages
    CLASS_DECOMPOSITION = "class_decomposition"  # LA splits into enforcers + proletariat
    CONTROL_RATIO_CRISIS = "control_ratio_crisis"  # Prisoners > guards × capacity
    TERMINAL_DECISION = "terminal_decision"  # Revolution or genocide bifurcation
    # Crisis and Devaluation Mechanics (Feature 018)
    CRISIS_PHASE_TRANSITION = "crisis_phase_transition"  # Phase lifecycle change
    DISPOSSESSION_CASCADE = "dispossession_cascade"  # LA share decline milestone
    BIFURCATION_THRESHOLD = "bifurcation_threshold"  # |score| crosses threshold
    # Dialectical Field Topology (Feature 002)
    EDGE_MODE_TRANSITION = "edge_mode_transition"  # Edge qualitative mode change
    PRINCIPAL_CONTRADICTION_SHIFT = "principal_contradiction_shift"  # Principal field changed
    CO_OPTIVE_BREAKDOWN = "co_optive_breakdown"  # Co-optation failure with bifurcation
    LATENT_CONTRADICTION_RELEASE = "latent_contradiction_release"  # Suppressed df/dt spike
    ASPECT_REVERSAL = "aspect_reversal"  # Dominant party switches on directed edge
    # Capital Volume I Production Dynamics (Feature 021)
    RESERVE_ARMY_PRESSURE = "reserve_army_pressure"  # Reserve army wage pressure applied
    DISPOSSESSION_EVENT = "dispossession_event"  # Aggregate dispossession recorded
    VALUE_TRANSFER = "value_transfer"  # Inter-territory value transfer from dispossession
    EXPLOITATION_MODE_SHIFT = "exploitation_mode_shift"  # Exploitation mode reclassified


class DispossessionType(StrEnum):
    """Categories of ongoing primitive accumulation.

    Eight types of extra-economic wealth seizure that transfer value from
    working-class households to capital. These represent Marx's "primitive
    accumulation" as an ongoing process, not a historical phase.

    Feature 021: Capital Volume I Production Dynamics (FR-004).
    """

    FORECLOSURE = "foreclosure"
    EVICTION = "eviction"
    TAX_SALE = "tax_sale"
    EMINENT_DOMAIN = "eminent_domain"
    WAGE_THEFT = "wage_theft"
    INCARCERATION_SEIZURE = "incarceration_seizure"
    PENSION_DEFAULT = "pension_default"
    GENTRIFICATION_DISPLACEMENT = "gentrification_displacement"


class ExploitationMode(StrEnum):
    """Dominant mode of surplus value extraction for a territory-sector.

    Classifies how surplus value is extracted: by lengthening the working
    day (absolute), by increasing productivity during a fixed day (relative),
    or a blend of both.

    Feature 021: Capital Volume I Production Dynamics (FR-007).
    """

    ABSOLUTE_DOMINANT = "absolute_dominant"
    RELATIVE_DOMINANT = "relative_dominant"
    MIXED = "mixed"


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


class DisplacementPriorityMode(StrEnum):
    """Mode for displacement routing priority.

    Sprint 3.7.1: Dynamic Displacement Priority Modes.

    The settler-colonial state routes displaced populations to sink nodes
    (RESERVATION, PENAL_COLONY, CONCENTRATION_CAMP) differently based on
    current political-economic conditions.

    Values:
        EXTRACTION: Labor is valuable. Prison-industrial complex logic.
            Priority: PENAL_COLONY > RESERVATION > CONCENTRATION_CAMP
            "We need their labor." (Default mode)

        CONTAINMENT: Crisis or transition period. Warehousing logic.
            Priority: RESERVATION > PENAL_COLONY > CONCENTRATION_CAMP
            "We need them out of the way but not dead yet."

        ELIMINATION: Late fascism. Necropolitical logic.
            Priority: CONCENTRATION_CAMP > PENAL_COLONY > RESERVATION
            "We don't need them at all."

        AUTO: Compute mode dynamically from economic/political conditions.
            (Not implemented in Sprint 3.7.1 - reserved for future use)
    """

    EXTRACTION = "extraction"
    CONTAINMENT = "containment"
    ELIMINATION = "elimination"
    AUTO = "auto"


class GameOutcome(StrEnum):
    """Possible game ending outcomes (Slice 1.6: Endgame Detection).

    The simulation can end in three ways, plus the ongoing state:

    Values:
        IN_PROGRESS: Game is still ongoing (no endgame condition met yet).

        REVOLUTIONARY_VICTORY: The masses have won. Requires:
            - percolation_ratio >= 0.7 (70%+ in giant component)
            - average class_consciousness > 0.8 (ideological clarity)

        ECOLOGICAL_COLLAPSE: The planet has collapsed. Requires:
            - overshoot_ratio > 2.0 for 5 consecutive ticks
            (Capital's metabolic rift has become fatal)

        FASCIST_CONSOLIDATION: Fascism has won. Requires:
            - national_identity > class_consciousness for 3+ nodes
            (False consciousness prevents class-based organization)

    Priority when multiple conditions are met:
        REVOLUTIONARY_VICTORY > ECOLOGICAL_COLLAPSE > FASCIST_CONSOLIDATION
    """

    IN_PROGRESS = "in_progress"
    REVOLUTIONARY_VICTORY = "revolutionary_victory"
    ECOLOGICAL_COLLAPSE = "ecological_collapse"
    FASCIST_CONSOLIDATION = "fascist_consolidation"


class EdgeMode(StrEnum):
    """Qualitative mode of an edge in the contradiction field topology.

    Dialectical Field Topology (Feature 002): EdgeMode is distinct from
    EdgeType. EdgeType describes the mechanical nature of a relationship
    (exploitation, solidarity, etc.). EdgeMode describes the qualitative
    character of the contradiction on that edge — how the contradiction
    manifests dialectically.

    Reference: R-002 (EdgeMode vs EdgeType distinction)
    Reference: FR-010 (transition topology — 17 permissible transitions)
    Reference: FR-017 (CO-OPTIVE edge classification table)

    Values:
        EXTRACTIVE: Unidirectional value flow from exploited to exploiter
        TRANSACTIONAL: Bidirectional symmetric market exchange
        SOLIDARISTIC: Bidirectional mutual aid, shared reproduction
        ANTAGONISTIC: Oppositional, open conflict over contested value
        CO_OPTIVE: Bidirectional asymmetric — concessions for quiescence
    """

    EXTRACTIVE = "extractive"
    TRANSACTIONAL = "transactional"
    SOLIDARISTIC = "solidaristic"
    ANTAGONISTIC = "antagonistic"
    CO_OPTIVE = "co_optive"


class ContradictionCharacter(StrEnum):
    """Character flag for contradictions on edges.

    Dialectical Field Topology (Feature 002), FR-018: Every edge carrying
    an edge_mode also carries a contradiction_character flag indicating
    whether the contradiction is antagonistic (irreconcilable within the
    current mode of production) or non-antagonistic.

    Reference: Constitution I.14 (antagonistic vs non-antagonistic contradictions)

    Values:
        ANTAGONISTIC: Irreconcilable within current mode of production
        NON_ANTAGONISTIC: Resolvable without systemic transformation
    """

    ANTAGONISTIC = "antagonistic"
    NON_ANTAGONISTIC = "non_antagonistic"


# Hypergraph Community Layer (Feature 022)


class CommunityType(StrEnum):
    """Community types for hypergraph membership (Constitution II.7).

    Three structurally distinct categories — NOT a spectrum.

    Category 1 — Contradiction Pairs (both sides real hyperedges):
        SETTLER: Settler nation (hegemonic). Institutions: HOAs, police unions, border militias.
        NEW_AFRIKAN: New Afrikan / Black internal nation (marginalized)
        FIRST_NATIONS: Indigenous / First Nations peoples (marginalized)
        CHICANO: Chicano / Mexican-American nation (marginalized)
        PATRIARCHAL: Patriarchal order (hegemonic). Institutions: gendered wage systems, family structure.
        WOMEN: Women — reproductive labor allocation (marginalized)
        TRANS: Transgender / gender non-conforming (marginalized)

    Category 2 — Institutional Exclusion (only marginalized side):
        DISABLED: Disabled community. Built environment assumes able-bodiedness.
        QUEER: Queer / LGBQ. Institutional heteronormativity.
        UNDOCUMENTED: Undocumented. Legal exclusion from protections.
        INCARCERATED: Incarcerated. Carceral system, civil death.

    Category 3 — Lifecycle Phases (D-P-D' Circuit):
        YOUTH: D phase. Pre-productive, dependent, receives socialization.
        ADULT: P phase. Sells labor-power. Where C-M-C and M-C-M' operate.
        ELDER: D' phase. Post-productive. Legitimation bargain (pensions, Social Security).
    """

    # Category 1: Contradiction Pairs — hegemonic
    SETTLER = "settler"
    PATRIARCHAL = "patriarchal"
    # Category 1: Contradiction Pairs — marginalized
    NEW_AFRIKAN = "new_afrikan"
    FIRST_NATIONS = "first_nations"
    CHICANO = "chicano"
    WOMEN = "women"
    TRANS = "trans"
    # Category 2: Institutional Exclusion — marginalized only
    DISABLED = "disabled"
    QUEER = "queer"
    UNDOCUMENTED = "undocumented"
    INCARCERATED = "incarcerated"
    # Category 3: Lifecycle Phases — D-P-D' Circuit
    YOUTH = "youth"
    ADULT = "adult"
    ELDER = "elder"


class HyperedgeCategory(StrEnum):
    """Structural category for community hyperedges (Feature 029, Constitution II.7).

    Three qualitatively distinct categories with different material bases,
    relationships to oppression, and modeling requirements.

    Values:
        CONTRADICTION_PAIR: Both hegemonic and marginalized sides exist as real
            hyperedges with extraction flows between them.
        INSTITUTIONAL_EXCLUSION: Only marginalized side exists. Oppression flows
            through institutional defaults, not a paired oppressor community.
        LIFECYCLE_PHASE: Temporal positions in D-P-D' intergenerational lifecycle.
            Universal, temporally permeable, defined by relationship to production.
    """

    CONTRADICTION_PAIR = "contradiction_pair"
    INSTITUTIONAL_EXCLUSION = "institutional_exclusion"
    LIFECYCLE_PHASE = "lifecycle_phase"


class ConsciousnessTendency(StrEnum):
    """Dominant ideological tendency within a community (Feature 029).

    Represents the prevailing direction of collective consciousness — the
    default drift without active organizing.

    Values:
        LIBERAL: Seeks inclusion in existing institutions without transforming
            them. Organizational vehicle: liberal CSOs, Democratic Party.
        FASCIST: Collaboration with hegemonic order for individual escape.
            Strategy: shrink the marginalized definition, exclude the most marginal.
        REVOLUTIONARY: Oppositional collective identity, independent power.
            The contradiction is material, not a misunderstanding.
    """

    LIBERAL = "liberal"
    FASCIST = "fascist"
    REVOLUTIONARY = "revolutionary"


class LegalStatus(StrEnum):
    """Legal designation status for community-level state repression.

    Hypergraph Community Layer (Feature 022): Escalation is strictly
    one-way for state action. De-escalation requires political struggle
    (player action). Each level increases the threat multiplier applied
    to community members.

    Values:
        LEGAL: Normal status, minimal state attention (multiplier 0.1)
        SURVEILLED: Active monitoring (multiplier 0.5)
        DESIGNATED_EXTREMIST: Formal extremist designation (multiplier 1.0)
        DESIGNATED_TERRORIST: Formal terrorist designation (multiplier 2.0)
        CRIMINALIZED: Membership itself criminalized (multiplier 3.0)
    """

    LEGAL = "legal"
    SURVEILLED = "surveilled"
    DESIGNATED_EXTREMIST = "designated_extremist"
    DESIGNATED_TERRORIST = "designated_terrorist"
    CRIMINALIZED = "criminalized"


class MembershipRole(StrEnum):
    """Agent integration level within a community.

    Hypergraph Community Layer (Feature 022): Determines membership
    strength weight and visibility profile for threat score computation.

    Values:
        CORE_ORGANIZER: Infrastructure maintainers, visible leaders (weight 1.0)
        ACTIVE: Regular participants, known within community (weight 0.7)
        PARTICIPANT: Occasional engagement (weight 0.4)
        PERIPHERAL: Marginal connection (weight 0.2)
        SYMPATHIZER: External ally, not legible as member (weight 0.1)
    """

    CORE_ORGANIZER = "core_organizer"
    ACTIVE = "active"
    PARTICIPANT = "participant"
    PERIPHERAL = "peripheral"
    SYMPATHIZER = "sympathizer"
