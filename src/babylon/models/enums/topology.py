"""Graph topology and flow enums (edge types, modes, infrastructure).

Spec 058: extracted from the historical ``babylon.models.enums`` monolith.
Re-exported via :mod:`babylon.models.enums.__init__`.
"""

from __future__ import annotations

from enum import StrEnum


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
        ANTAGONISTIC: Manufactured conflict between orgs (Feature 039)
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
    ANTAGONISTIC = "antagonistic"  # Manufactured conflict between orgs (Feature 039)
    # State Apparatus AI (Feature 039)
    TARGETS = "targets"  # AttentionThread → target entity
    OWNED_BY = "owned_by"  # AttentionThread → StateApparatus
    JURISDICTION = "jurisdiction"  # LegalFramework → Territory
    # Institution Base Model (Feature 040)
    HOUSES = "houses"  # Institution → Organization (housing relationship)
    # Spec-070 Balkanization (political topology overlay per Constitution I.20)
    CLAIMS = "claims"  # Sovereign → Territory (FR-009)
    INFLUENCES = "influences"  # BalkanizationFaction → Territory (FR-014)
    ADMINISTERS = "administers"  # Sovereign → Sovereign (FR-018; acyclic DAG)


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


__all__ = [
    "EdgeMode",
    "EdgeType",
    "FlowCategory",
    "InfrastructureType",
    "JunctionType",
    "TopologyType",
]
