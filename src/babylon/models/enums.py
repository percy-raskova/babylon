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
- OrgType: Organization category discriminator (Feature 031)
- ClassCharacter: Which class an organization serves (Feature 031)
- TopologyType: Computed internal topology classification (Feature 031)
- LegalStanding: Legal status of an organization (Feature 031)
- JurisdictionLevel: State apparatus jurisdiction scope (Feature 031)
- ServiceType: Civil society service domain (Feature 031)
- TerrainType: Hex terrain classification (Feature 036)
- BiocapacityType: Renewable resource stock categories (Feature 036)
- InfrastructureType: Physical infrastructure categories (Feature 036)
- FlowCategory: Flow categories for infrastructure capacity (Feature 036)
- JunctionType: Point infrastructure at mesh vertices (Feature 036)
- LocalityClass: Distance classification for nonlocal edges (Feature 036)
- InternetResponseMode: State internet control modes (Feature 036)
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
        TRANSACTIONAL: Service-for-support exchange (org-community, Feature 032)
        SOLIDARISTIC: Deep mutual commitment (org-community, Feature 032)
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
    # Organization Base Model (Feature 031)
    MEMBERSHIP = "membership"  # Organization → SocialClass (weighted by population)
    RECRUITMENT = "recruitment"  # Organization → SocialClass (active pipeline)
    EMPLOYMENT = "employment"  # Business → SocialClass (employer relationship)
    COMMAND = "command"  # KeyFigure → KeyFigure (internal hierarchy)
    PRESENCE = "presence"  # Organization → Territory (operational footprint)
    # OODA Loop System (Feature 032)
    TRANSACTIONAL = "transactional"  # Organization → Community (service-for-support exchange)
    SOLIDARISTIC = "solidaristic"  # Organization → Community (deep mutual commitment)


def resolve_edge_type(raw: str | EdgeType | None) -> EdgeType | None:
    """Coerce a raw edge type value (str or enum) to EdgeType.

    Args:
        raw: String value, EdgeType instance, or None.

    Returns:
        EdgeType enum or None if input is None.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        return EdgeType(raw)
    return raw


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
    # D-P-D' Lifecycle Circuit (Feature 030)
    LIFECYCLE_TRANSITION = "lifecycle_transition"  # Population moved between phases
    LEGITIMATION_CRISIS = "legitimation_crisis"  # Classification changed to CRISIS
    LEGITIMATION_RECOVERY = "legitimation_recovery"  # Classification improved from CRISIS
    INHERITANCE_TRANSFER = "inheritance_transfer"  # D' death triggered inheritance flow
    DUAL_CIRCUIT_INTERFERENCE = "dual_circuit_interference"  # Resource competition detected
    # OODA Loop System (Feature 032)
    ORGANIZATIONAL_ACTION = "organizational_action"  # Any org action executed
    STATE_REPRESSION = "state_repression"  # REPRESS action by state
    STATE_SURVEILLANCE = "state_surveillance"  # SURVEIL action by state
    CONSCIOUSNESS_SHIFT = "consciousness_shift"  # Community CI change exceeds threshold
    INITIATIVE_CONTESTED = "initiative_contested"  # Non-state org seizes initiative
    INFRASTRUCTURE_CHANGE = "infrastructure_change"  # BUILD or ATTACK infrastructure
    # Bifurcation Topology Analysis (Feature 033)
    BIFURCATION_TENDENCY_CHANGE = "bifurcation_tendency_change"  # Overall tendency shifted


class LegitimationClassification(StrEnum):
    """Crisis classification for the legitimation index (Feature 030).

    Classifies the legitimation index into three regimes based on
    material conditions underwriting the D' promise.

    Values:
        CRISIS: Index < 0.3 — D' promise not credible, agitation routes to bifurcation.
        UNSTABLE: Index < 0.5 — D' promise weakening, risk accumulating.
        STABLE: Index >= 0.5 — D' promise credible, acquiescence maintained.
    """

    CRISIS = "crisis"
    UNSTABLE = "unstable"
    STABLE = "stable"


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


# Organization Base Model (Feature 031)


class OrgType(StrEnum):
    """Organization category discriminator (Feature 031).

    Used as the Pydantic discriminated union discriminator field to dispatch
    to the correct Organization subtype.

    Values:
        STATE_APPARATUS: Wields state violence/surveillance
        BUSINESS: Accumulates capital, employs labor
        POLITICAL_FACTION: Contests political power
        CIVIL_SOCIETY: Non-state, non-business collective
    """

    STATE_APPARATUS = "state_apparatus"
    BUSINESS = "business"
    POLITICAL_FACTION = "political_faction"
    CIVIL_SOCIETY = "civil_society"


class ClassCharacter(StrEnum):
    """Which class an organization objectively serves (Feature 031).

    May differ from the organization's stated mission or membership
    composition. Determined by material analysis of the organization's
    structural role in class reproduction.

    Values:
        BOURGEOIS: Serves bourgeois class interests
        PETTY_BOURGEOIS: Serves petty bourgeois class interests
        LABOR_ARISTOCRATIC: Serves labor aristocracy interests
        PROLETARIAN: Serves proletarian class interests
        LUMPEN: Serves lumpenproletariat interests
        CONTESTED: Class character actively contested
    """

    BOURGEOIS = "bourgeois"
    PETTY_BOURGEOIS = "petty_bourgeois"
    LABOR_ARISTOCRATIC = "labor_aristocratic"
    PROLETARIAN = "proletarian"
    LUMPEN = "lumpen"
    CONTESTED = "contested"


class TopologyType(StrEnum):
    """Computed internal topology classification (Feature 031).

    Derived from COMMAND edge subgraph analysis — NEVER stored on the
    Organization model. The graph speaks the truth.

    Values:
        STAR: Centralized around single leader (efficient, fragile)
        HIERARCHY: Multi-level command chain (scalable, vulnerable at branch points)
        MESH: Fully connected peers (resilient, slow to coordinate)
        CELL: Isolated cells connected by cutouts (resilient, compartmentalized)
    """

    STAR = "star"
    HIERARCHY = "hierarchy"
    MESH = "mesh"
    CELL = "cell"


class LegalStanding(StrEnum):
    """Legal status of an organization (Feature 031).

    Determines the organization's relationship to the state legal apparatus
    and affects credibility derivation for consciousness effect calculations.

    Values:
        SOVEREIGN: State itself (government agencies)
        CHARTERED: State-authorized entity (corporations, licensed orgs)
        REGISTERED: Officially registered (nonprofits, registered parties)
        INFORMAL: No legal registration (neighborhood groups, informal networks)
        UNDERGROUND: Explicitly illegal (banned organizations, clandestine cells)
    """

    SOVEREIGN = "sovereign"
    CHARTERED = "chartered"
    REGISTERED = "registered"
    INFORMAL = "informal"
    UNDERGROUND = "underground"


class JurisdictionLevel(StrEnum):
    """Scope of state apparatus authority (Feature 031).

    Used exclusively by StateApparatus subtypes to define the geographical
    and legal scope of their jurisdiction.

    Values:
        NATIONAL: Federal jurisdiction
        STATE: State-level jurisdiction
        COUNTY: County-level jurisdiction
        MUNICIPAL: City/municipal jurisdiction
    """

    NATIONAL = "national"
    STATE = "state"
    COUNTY = "county"
    MUNICIPAL = "municipal"


class ServiceType(StrEnum):
    """Civil society service domain (Feature 031).

    Categorizes the primary service provided by a CivilSocietyOrg.
    Affects legitimacy derivation and community trust.

    Values:
        RELIGIOUS: Churches, mosques, temples
        EDUCATIONAL: Schools, universities, training programs
        HEALTHCARE: Hospitals, clinics, health collectives
        LEGAL_AID: Legal defense, bail funds
        MUTUAL_AID: Direct material support networks
        CULTURAL: Arts, cultural preservation organizations
        MEDIA: News, broadcasting, publishing
        LABOR: Unions, worker centers, cooperatives
    """

    RELIGIOUS = "religious"
    EDUCATIONAL = "educational"
    HEALTHCARE = "healthcare"
    LEGAL_AID = "legal_aid"
    MUTUAL_AID = "mutual_aid"
    CULTURAL = "cultural"
    MEDIA = "media"
    LABOR = "labor"


# OODA Loop System (Feature 032)


class DecisionMode(StrEnum):
    """How an organization makes decisions (Feature 032).

    Determines the Decide phase duration in the OODA cycle time
    computation. Faster decision modes yield shorter cycle times
    and higher initiative scores.

    Values:
        AUTOCRATIC: Single leader decides (fastest, base 1.0)
        DELEGATE: Trusted delegates (fast, base 2.0)
        DEMOCRATIC: Majority vote (moderate, base 3.0)
        CONSENSUS: Full consensus (slowest, base 5.0)
    """

    AUTOCRATIC = "autocratic"
    DELEGATE = "delegate"
    DEMOCRATIC = "democratic"
    CONSENSUS = "consensus"


class ActionType(StrEnum):
    """Organizational action types for OODA resolution (Feature 032).

    21 action types across 7 categories. Eligibility depends on OrgType
    and organization attributes.

    Values:
        RECRUIT: Recruit new members
        ORGANIZE: Build organizational capacity
        EDUCATE: Raise consciousness through education
        AGITATE: Raise contestation (precondition for effective EDUCATE)
        PROPAGANDIZE: Broadcast messaging
        FUNDRAISE: Generate resources
        PROVIDE_SERVICE: Direct community service provision
        EMPLOY: Hire workers (Business only)
        REPRESS: State coercion (StateApparatus or violence_capacity > 0)
        PROTEST: Public demonstration
        STRIKE: Withdraw labor
        EXPROPRIATE: Seize assets
        SURVEIL: Monitor targets (StateApparatus or surveillance_capacity > 0)
        INFILTRATE: Plant agents (StateApparatus only)
        COUNTER_INTEL: Build counter-intelligence
        MAP_NETWORK: Intelligence gathering
        PROPOSE_ALLIANCE: Seek alliance
        DENOUNCE: Public denunciation
        BUILD_INFRASTRUCTURE: Build community infrastructure
        ATTACK_INFRASTRUCTURE: Destroy infrastructure
        ASSIMILATE: Absorb into hegemonic norm
    """

    RECRUIT = "recruit"
    ORGANIZE = "organize"
    EDUCATE = "educate"
    AGITATE = "agitate"
    PROPAGANDIZE = "propagandize"
    FUNDRAISE = "fundraise"
    PROVIDE_SERVICE = "provide_service"
    EMPLOY = "employ"
    REPRESS = "repress"
    PROTEST = "protest"
    STRIKE = "strike"
    EXPROPRIATE = "expropriate"
    SURVEIL = "surveil"
    INFILTRATE = "infiltrate"
    COUNTER_INTEL = "counter_intel"
    MAP_NETWORK = "map_network"
    PROPOSE_ALLIANCE = "propose_alliance"
    DENOUNCE = "denounce"
    BUILD_INFRASTRUCTURE = "build_infrastructure"
    ATTACK_INFRASTRUCTURE = "attack_infrastructure"
    ASSIMILATE = "assimilate"


# ---------------------------------------------------------------------------
# Infrastructure Topology Layer (Feature 036)
# ---------------------------------------------------------------------------


class TerrainType(StrEnum):
    """Hex terrain classification (Feature 036).

    Determined by spatial intersection of H3 cell boundaries with Natural
    Earth water/resource polygons. Classification uses majority coverage
    threshold from TerrainDefines.

    Values:
        LAND: Default — no dominant water/resource coverage
        WATER: Majority water coverage (lakes, rivers)
        RESOURCE: Majority resource region coverage (ranges, deltas, wetlands)
    """

    LAND = "land"
    WATER = "water"
    RESOURCE = "resource"


class BiocapacityType(StrEnum):
    """Renewable resource stock categories (Feature 036).

    Each non-LAND hex initializes biocapacity stocks based on terrain type.
    WATER hexes get FRESHWATER, FISHERY, SHIPPING_ACCESS.
    RESOURCE hexes get MINERAL, TIMBER, HYDROELECTRIC.

    Values:
        FRESHWATER: Potable water extraction capacity
        FISHERY: Marine/lacustrine food production
        SHIPPING_ACCESS: Navigable waterway throughput
        MINERAL: Extractable mineral resources
        TIMBER: Harvestable timber stock
        HYDROELECTRIC: Hydroelectric generation capacity
    """

    FRESHWATER = "freshwater"
    FISHERY = "fishery"
    SHIPPING_ACCESS = "shipping_access"
    MINERAL = "mineral"
    TIMBER = "timber"
    HYDROELECTRIC = "hydroelectric"


class InfrastructureType(StrEnum):
    """Physical infrastructure categories (Feature 036).

    Typed infrastructure links assigned to H3 mesh edges via spatial
    snapping from Natural Earth road, railroad, and other linear features.

    Values:
        HIGHWAY: Major highway / interstate (high FREIGHT + COMMUTER)
        ARTERIAL: Secondary highway (moderate FREIGHT + COMMUTER)
        LOCAL_ROAD: Local / county road (low capacity, commuter-focused)
        RAIL: Railroad line (high FREIGHT, low COMMUTER)
        PIPELINE: Energy pipeline (ENERGY only)
        TRANSMISSION: Power transmission line (ENERGY only)
        SHIPPING_LANE: Navigable waterway or sea lane (FREIGHT only)
        AIR_LINK: Air route between airports (all categories, nonlocal)
    """

    HIGHWAY = "highway"
    ARTERIAL = "arterial"
    LOCAL_ROAD = "local_road"
    RAIL = "rail"
    PIPELINE = "pipeline"
    TRANSMISSION = "transmission"
    SHIPPING_LANE = "shipping_lane"
    AIR_LINK = "air_link"


class FlowCategory(StrEnum):
    """Flow categories for infrastructure capacity (Feature 036).

    Each infrastructure link has per-category capacity values. Edge capacity
    aggregation sums across all links per category.

    Values:
        FREIGHT: Physical goods movement
        COMMUTER: Human movement (labor, consumption)
        VALUE: Financial/value flow
        ENERGY: Energy transmission
        CONSCIOUSNESS: Ideology/information diffusion
    """

    FREIGHT = "freight"
    COMMUTER = "commuter"
    VALUE = "value"
    ENERGY = "energy"
    CONSCIOUSNESS = "consciousness"


class JunctionType(StrEnum):
    """Point infrastructure at mesh vertices (Feature 036).

    Junction infrastructure snapped from NE point features (airports, ports)
    to H3 mesh vertices. Degradation cascades to all 3 adjacent edges.

    Values:
        INTERCHANGE: Highway interchange (roads intersection)
        SUBSTATION: Power substation (energy distribution)
        RAIL_JUNCTION: Railroad junction (freight routing)
        PORT: Seaport or river port (shipping + freight)
        AIRPORT: Airport terminal (air link generation)
    """

    INTERCHANGE = "interchange"
    SUBSTATION = "substation"
    RAIL_JUNCTION = "rail_junction"
    PORT = "port"
    AIRPORT = "airport"


class LocalityClass(StrEnum):
    """Distance classification for nonlocal edges (Feature 036).

    Ratio of great-circle distance to average hex diameter determines
    locality. LOCAL < 3.0, SEMI_LOCAL < 20.0, NONLOCAL >= 20.0.

    Values:
        LOCAL: Within 3 hex diameters (adjacent-equivalent)
        SEMI_LOCAL: 3-20 hex diameters (regional)
        NONLOCAL: 20+ hex diameters (transcontinental)
    """

    LOCAL = "local"
    SEMI_LOCAL = "semi_local"
    NONLOCAL = "nonlocal"


class InternetResponseMode(StrEnum):
    """State apparatus internet control modes (Feature 036).

    Determines how the state apparatus modulates internet consciousness
    diffusion at a given hex. PERMIT is default. THROTTLE is covert.
    SEVER is overt and triggers consciousness backfire.

    Values:
        PERMIT: Full throughput, full surveillance
        THROTTLE: Reduced throughput, maintained surveillance, covert
        SEVER: Zero throughput, zero surveillance, overt with backfire
    """

    PERMIT = "permit"
    THROTTLE = "throttle"
    SEVER = "sever"
