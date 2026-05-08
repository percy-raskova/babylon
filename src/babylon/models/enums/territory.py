"""Spatial and territorial enums (sectors, profiles, terrain).

Spec 058: extracted from the historical ``babylon.models.enums`` monolith.
Re-exported via :mod:`babylon.models.enums.__init__`.
"""

from __future__ import annotations

from enum import StrEnum


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


__all__ = [
    "BiocapacityType",
    "DisplacementPriorityMode",
    "LocalityClass",
    "OperationalProfile",
    "SectorType",
    "TerrainType",
    "TerritoryType",
]
