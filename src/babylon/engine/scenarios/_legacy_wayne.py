"""Wayne County Organizer scenario — MVP entry point.

Creates a playable simulation centered on Wayne County, Michigan (Detroit metro).
Uses H3 resolution 5 hexes (~252 km² each, ~50 hexes for the county) for the MVP,
with the intent to drill down to res 7 (~5 km², ~3,500 hexes) later.

The player controls a small, nascent political organization with limited resources.
NPCs include local police, existing parties (DSA, Democrats), businesses, and
community orgs. The scenario runs for 52 ticks (1 year of game time).

Geography
---------
Wayne County sits at roughly 42.3°N, 83.1°W. It contains Detroit (pop ~640k),
Dearborn, Livonia, Westland, and dozens of smaller suburbs. The county has
extreme class stratification: Grosse Pointe wealth adjacent to deep poverty
in the city core.

Design Note
-----------
This scenario follows the same factory pattern as ``create_us_scenario()`` in
``scenarios.py``. It returns ``(WorldState, SimulationConfig, GameDefines)``.
"""

from __future__ import annotations

import math

import h3

from babylon.config.defines import (
    EconomyDefines,
    GameDefines,
    SurvivalDefines,
)
from babylon.models.config import SimulationConfig
from babylon.models.entities.organization import CivilSocietyOrg, StateApparatus
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.state_apparatus_ai import FactionBalance
from babylon.models.entities.territory import Territory
from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    EdgeType,
    JurisdictionLevel,
    LegalStanding,
    OperationalProfile,
    SectorType,
    ServiceType,
    SocialRole,
    TerritoryType,
)
from babylon.models.world_state import WorldState

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Wayne County bounding box (generous to catch edge hexes)
WAYNE_COUNTY_BOUNDS = {
    "lat_min": 42.05,
    "lat_max": 42.55,
    "lon_min": -83.55,
    "lon_max": -82.90,
}

# Key locations within Wayne County for hex classification
_DETROIT_CORE = (42.33, -83.05)  # Downtown Detroit
_DEARBORN = (42.32, -83.18)  # Dearborn (Ford HQ)
_GROSSE_POINTE = (42.39, -82.91)  # Grosse Pointe (wealthy enclave)
_HAMTRAMCK = (42.39, -83.05)  # Hamtramck (working-class, diverse)
_HIGHLAND_PARK = (42.41, -83.10)  # Highland Park (impoverished)
_DOWNRIVER = (42.18, -83.15)  # Downriver communities (industrial)
_DTW_AIRPORT = (42.21, -83.35)  # DTW airport area
_LIVONIA = (42.37, -83.35)  # Livonia (white-flight suburb)

# Population estimates by area type
_POP_DENSE_URBAN = 25_000  # per res-5 hex in dense Detroit
_POP_URBAN = 15_000  # per res-5 hex in inner-ring suburbs
_POP_SUBURBAN = 8_000  # per res-5 hex in outer suburbs
_POP_INDUSTRIAL = 3_000  # per res-5 hex in industrial/airport zones

# H3 resolution for MVP — res 6 ≈ 36 km² each, ~81 hexes for Wayne County
H3_RESOLUTION = 6


# ---------------------------------------------------------------------------
# Helper: distance between two lat/lon points (km, Haversine approx)
# ---------------------------------------------------------------------------


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate great-circle distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Hex classification: determine sector, territory type, rent, population
# ---------------------------------------------------------------------------


def _classify_wayne_hex(
    lat: float, lon: float
) -> tuple[str, SectorType, TerritoryType, float, float, int, OperationalProfile]:
    """Classify a Wayne County hex by its geographic position.

    Uses proximity to known landmarks to determine economic character.
    Returns (name, sector, territory_type, rent_level, biocapacity, population, profile).
    """
    # Distance to key locations
    d_detroit = _haversine_km(lat, lon, *_DETROIT_CORE)
    d_grosse_pointe = _haversine_km(lat, lon, *_GROSSE_POINTE)
    d_dearborn = _haversine_km(lat, lon, *_DEARBORN)
    d_hamtramck = _haversine_km(lat, lon, *_HAMTRAMCK)
    d_highland_park = _haversine_km(lat, lon, *_HIGHLAND_PARK)
    d_downriver = _haversine_km(lat, lon, *_DOWNRIVER)
    d_airport = _haversine_km(lat, lon, *_DTW_AIRPORT)
    d_livonia = _haversine_km(lat, lon, *_LIVONIA)

    # Grosse Pointe enclave — wealthy, CORE territory
    if d_grosse_pointe < 5.0:
        return (
            "Grosse Pointe",
            SectorType.RESIDENTIAL,
            TerritoryType.CORE,
            8.0,  # Very high rent
            30.0,  # Low biocapacity (developed)
            _POP_SUBURBAN,
            OperationalProfile.LOW_PROFILE,
        )

    # Livonia / northwest suburbs — white-flight, CORE territory
    if d_livonia < 8.0:
        return (
            "Livonia",
            SectorType.RESIDENTIAL,
            TerritoryType.CORE,
            5.0,
            50.0,
            _POP_SUBURBAN,
            OperationalProfile.LOW_PROFILE,
        )

    # Dearborn — industrial (Ford), mixed
    if d_dearborn < 5.0:
        return (
            "Dearborn",
            SectorType.INDUSTRIAL,
            TerritoryType.CORE,
            4.0,
            40.0,
            _POP_URBAN,
            OperationalProfile.LOW_PROFILE,
        )

    # Airport zone — logistics, low population
    if d_airport < 6.0:
        return (
            "DTW Airport Zone",
            SectorType.DOCKS,
            TerritoryType.CORE,
            2.0,
            20.0,
            _POP_INDUSTRIAL,
            OperationalProfile.LOW_PROFILE,
        )

    # Highland Park — deeply impoverished enclave within Detroit
    if d_highland_park < 3.0:
        return (
            "Highland Park",
            SectorType.RESIDENTIAL,
            TerritoryType.PERIPHERY,
            0.5,  # Very low rent (abandoned)
            15.0,
            _POP_URBAN,
            OperationalProfile.LOW_PROFILE,
        )

    # Hamtramck — diverse working-class enclave
    if d_hamtramck < 3.0:
        return (
            "Hamtramck",
            SectorType.RESIDENTIAL,
            TerritoryType.PERIPHERY,
            1.5,
            20.0,
            _POP_URBAN,
            OperationalProfile.LOW_PROFILE,
        )

    # Detroit core — commercial downtown + surrounding residential
    if d_detroit < 5.0:
        return (
            "Detroit Core",
            SectorType.COMMERCIAL,
            TerritoryType.PERIPHERY,
            3.0,
            15.0,  # Low biocapacity (concrete)
            _POP_DENSE_URBAN,
            OperationalProfile.LOW_PROFILE,
        )

    # Inner Detroit ring
    if d_detroit < 12.0:
        return (
            "Detroit",
            SectorType.RESIDENTIAL,
            TerritoryType.PERIPHERY,
            1.5,
            25.0,
            _POP_URBAN,
            OperationalProfile.LOW_PROFILE,
        )

    # Downriver — industrial south (River Rouge, Ecorse, etc.)
    if d_downriver < 8.0:
        return (
            "Downriver",
            SectorType.INDUSTRIAL,
            TerritoryType.PERIPHERY,
            2.0,
            35.0,
            _POP_URBAN,
            OperationalProfile.LOW_PROFILE,
        )

    # Default: outer Wayne County — suburban/rural
    return (
        "Wayne County",
        SectorType.RESIDENTIAL,
        TerritoryType.CORE,
        3.5,
        80.0,
        _POP_SUBURBAN,
        OperationalProfile.LOW_PROFILE,
    )


# ---------------------------------------------------------------------------
# Territory generation
# ---------------------------------------------------------------------------


def _create_wayne_county_territories() -> dict[str, Territory]:
    """Generate H3 resolution-5 Territory objects covering Wayne County.

    Returns dict mapping H3 cell ID to Territory.
    """
    # Build polygon from bounding box (LatLngPoly expects outer ring)
    bounds = WAYNE_COUNTY_BOUNDS
    polygon = h3.LatLngPoly(
        [
            (bounds["lat_min"], bounds["lon_min"]),
            (bounds["lat_max"], bounds["lon_min"]),
            (bounds["lat_max"], bounds["lon_max"]),
            (bounds["lat_min"], bounds["lon_max"]),
        ]
    )
    cells = h3.polygon_to_cells(polygon, H3_RESOLUTION)

    territories: dict[str, Territory] = {}
    for cell in cells:
        lat, lon = h3.cell_to_latlng(cell)
        name, sector, t_type, rent, biocap, pop, profile = _classify_wayne_hex(lat, lon)

        territories[cell] = Territory(
            id=cell,
            h3_index=cell,
            name=name,
            sector_type=sector,
            territory_type=t_type,
            population=pop,
            rent_level=rent,
            biocapacity=biocap,
            max_biocapacity=biocap,
            heat=0.0,
            profile=profile,
        )

    return territories


# ---------------------------------------------------------------------------
# Social class entities for Wayne County
# ---------------------------------------------------------------------------

# Entity IDs (must match ^(C[0-9]{3}|T[0-9]{3}|...) pattern)
_DETROIT_PROLETARIAT_ID = "C001"
_SUBURBAN_PETTY_BOURGEOIS_ID = "C002"
_WAYNE_BOURGEOISIE_ID = "C003"
_DEARBORN_WORKERS_ID = "C004"


def _create_wayne_county_entities() -> dict[str, SocialClass]:
    """Create social class entities representing Wayne County demographics."""
    # Detroit proletariat — majority Black, deeply exploited
    detroit_proletariat = SocialClass(
        id=_DETROIT_PROLETARIAT_ID,
        name="Detroit Proletariat",
        role=SocialRole.INTERNAL_PROLETARIAT,
        description="Working class and unemployed in Detroit proper",
        wealth=0.15,  # Very poor — deindustrialized city
        ideology=-0.2,  # type: ignore[arg-type]  # Slightly left (Black radical tradition)
        organization=0.05,  # Nearly atomized
        repression_faced=0.7,  # Heavy policing
        subsistence_threshold=0.4,  # High survival costs
        p_acquiescence=0.0,
        p_revolution=0.0,
        population=640_000,
    )

    # Suburban petty bourgeoisie — Livonia, Grosse Pointe, Dearborn Heights
    suburban_petty_bourgeois = SocialClass(
        id=_SUBURBAN_PETTY_BOURGEOIS_ID,
        name="Suburban Petty Bourgeoisie",
        role=SocialRole.LABOR_ARISTOCRACY,
        description="Middle-class suburbanites in Wayne County outer ring",
        wealth=0.65,
        ideology=0.4,  # type: ignore[arg-type]  # Conservative
        organization=0.3,  # HOAs, churches, civic groups
        repression_faced=0.1,  # Protected
        subsistence_threshold=0.15,
        p_acquiescence=0.0,
        p_revolution=0.0,
        population=800_000,
    )

    # Wayne County bourgeoisie — auto industry execs, real estate, finance
    wayne_bourgeoisie = SocialClass(
        id=_WAYNE_BOURGEOISIE_ID,
        name="Wayne County Bourgeoisie",
        role=SocialRole.CORE_BOURGEOISIE,
        description="Capital owners: auto industry, real estate, finance",
        wealth=0.9,
        ideology=0.7,  # type: ignore[arg-type]  # Reactionary
        organization=0.8,  # Well-organized via chambers of commerce
        repression_faced=0.05,  # Above the law
        subsistence_threshold=0.05,
        p_acquiescence=0.0,
        p_revolution=0.0,
        population=50_000,
    )

    # Dearborn workers — Ford plant workers, Arab-American community
    dearborn_workers = SocialClass(
        id=_DEARBORN_WORKERS_ID,
        name="Dearborn Industrial Workers",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        description="Auto workers and immigrant labor in Dearborn/Downriver",
        wealth=0.35,
        ideology=-0.1,  # type: ignore[arg-type]  # Slightly left (union tradition)
        organization=0.15,  # Some union remnants
        repression_faced=0.4,
        subsistence_threshold=0.25,
        p_acquiescence=0.0,
        p_revolution=0.0,
        population=300_000,
    )

    return {
        _DETROIT_PROLETARIAT_ID: detroit_proletariat,
        _SUBURBAN_PETTY_BOURGEOIS_ID: suburban_petty_bourgeois,
        _WAYNE_BOURGEOISIE_ID: wayne_bourgeoisie,
        _DEARBORN_WORKERS_ID: dearborn_workers,
    }


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


def _create_wayne_county_relationships(
    territory_ids: list[str],
    territories: dict[str, Territory],
) -> list[Relationship]:
    """Create edges: exploitation, wages, solidarity, tenancy."""
    relationships: list[Relationship] = []

    # Exploitation: Detroit proletariat → Bourgeoisie
    relationships.append(
        Relationship(
            source_id=_DETROIT_PROLETARIAT_ID,
            target_id=_WAYNE_BOURGEOISIE_ID,
            edge_type=EdgeType.EXPLOITATION,
            description="Surplus value extraction from Detroit labor",
            value_flow=0.0,
            tension=0.3,  # Pre-existing tension
        )
    )

    # Exploitation: Dearborn workers → Bourgeoisie
    relationships.append(
        Relationship(
            source_id=_DEARBORN_WORKERS_ID,
            target_id=_WAYNE_BOURGEOISIE_ID,
            edge_type=EdgeType.EXPLOITATION,
            description="Industrial exploitation of Dearborn/Downriver labor",
            value_flow=0.0,
            tension=0.2,
        )
    )

    # Wages: Bourgeoisie → Suburban petty bourgeoisie (super-wages)
    relationships.append(
        Relationship(
            source_id=_WAYNE_BOURGEOISIE_ID,
            target_id=_SUBURBAN_PETTY_BOURGEOIS_ID,
            edge_type=EdgeType.WAGES,
            description="Super-wages buying suburban loyalty",
            value_flow=0.0,
            tension=0.0,
        )
    )

    # Potential solidarity: Detroit proletariat ↔ Dearborn workers
    relationships.append(
        Relationship(
            source_id=_DETROIT_PROLETARIAT_ID,
            target_id=_DEARBORN_WORKERS_ID,
            edge_type=EdgeType.SOLIDARITY,
            description="Potential cross-community worker solidarity",
            value_flow=0.0,
            tension=0.0,
            solidarity_strength=0.05,  # Very low — needs organizing
        )
    )

    # Tenancy edges: assign classes to territory zones by type
    sorted_ids = sorted(
        territory_ids,
        key=lambda tid: territories[tid].rent_level,
        reverse=True,
    )
    n = len(sorted_ids)

    # Bourgeoisie → top 10% rent hexes
    bourgeois_hexes = sorted_ids[: max(1, n // 10)]
    # Suburban petty bourgeoisie → next 30% (10-40%)
    suburban_hexes = sorted_ids[n // 10 : 2 * n // 5]
    # Dearborn workers → middle 20% (40-60%)
    dearborn_hexes = sorted_ids[2 * n // 5 : 3 * n // 5]
    # Detroit proletariat → bottom 40%
    detroit_hexes = sorted_ids[3 * n // 5 :]

    class_zones = [
        (_WAYNE_BOURGEOISIE_ID, bourgeois_hexes, "Bourgeois zone"),
        (_SUBURBAN_PETTY_BOURGEOIS_ID, suburban_hexes, "Suburban zone"),
        (_DEARBORN_WORKERS_ID, dearborn_hexes, "Industrial zone"),
        (_DETROIT_PROLETARIAT_ID, detroit_hexes, "Proletarian zone"),
    ]

    for class_id, zone_ids, description in class_zones:
        for tid in zone_ids:
            relationships.append(
                Relationship(
                    source_id=class_id,
                    target_id=tid,
                    edge_type=EdgeType.TENANCY,
                    description=description,
                    value_flow=0.0,
                    tension=0.0,
                )
            )

    return relationships


# ---------------------------------------------------------------------------
# Player organization
# ---------------------------------------------------------------------------

_PLAYER_ORG_ID = "ORG001"


def _create_player_org(starting_territory_ids: list[str]) -> CivilSocietyOrg:
    """Create the player's starting organization.

    A small, nascent political formation — a reading group that wants
    to become something more. Low resources, low heat, high potential.
    """
    return CivilSocietyOrg(
        id=_PLAYER_ORG_ID,
        name="Wayne County Organizing Committee",
        class_character=ClassCharacter.PROLETARIAN,
        consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
        legal_standing=LegalStanding.INFORMAL,
        service_type=ServiceType.MUTUAL_AID,
        territory_ids=starting_territory_ids[:2],
        cohesion=0.5,
        cadre_level=0.1,
        budget=100.0,
        heat=0.0,
    )


# ---------------------------------------------------------------------------
# State apparatus (Feature 039 / AW3-R2 item 3)
# ---------------------------------------------------------------------------

_STATE_APPARATUS_ID = "ORG002"


def _create_state_apparatus_org(policed_territory_ids: list[str]) -> StateApparatus:
    """Create the Detroit Police Department — the module docstring's
    long-promised "local police" NPC, never actually built until now.

    Setting ``faction_balance`` is the single documented activation gate
    for ``RuleBasedStateAI`` (``babylon.ooda.npc_stub._try_state_ai_dispatch``
    — every other Feature 039 entry point, State Action Menu / Attention
    Threads / Legal Frameworks / Legitimacy-Gated RoE tiers, hangs off this
    same dispatch and was real, tested-in-isolation code that had never once
    executed in a scenario before this).

    Faction weights lean Security-State (0.6), matching the org's own
    ``factional_alignment`` default and Detroit's real material history of
    heavy policing (mirrors the scenario's ``repression_level=0.6`` param
    and the Detroit proletariat's ``repression_faced=0.7``). ``heat=0.3``
    is deliberately the same value ``_try_state_ai_dispatch`` falls back to
    when heat is absent (FR-D06 escalation ladder input) — chosen so the
    seeded org sits at a believable "actively surveilling" starting point
    rather than a cold 0.0 that would understate a functioning apparatus.

    ``rng_seed`` MUST be set alongside ``faction_balance``: without it,
    ``RuleBasedStateAI.select_action``'s per-candidate tiebreaker falls back
    to OS-entropy-seeded ``random.Random(None)`` — a genuine Constitution
    III.7 determinism violation this scenario must not introduce.

    Formerly a known limitation, FIXED by task #73:
    ``RuleBasedStateAI.select_action`` used to always set
    ``target_id=org_id`` (itself) — Feature 039 never wired real target
    selection. It now sorts visible non-state-org threats by
    ``Heat x Visibility`` (``babylon.ooda.state_ai.decision.
    select_repress_target``, the epoch-3 "Blind Giant" doctrine) and
    targets the top one; with zero visible threats (heat 0 everywhere,
    e.g. right at scenario start before ORG001 has done anything to
    attract attention) it honestly no-ops rather than self-targeting.
    """
    balance = FactionBalance(
        finance_capital=0.2,
        security_state=0.6,
        settler_populist=0.2,
        stability=0.5,
        legitimacy=0.5,
    )
    return StateApparatus(
        id=_STATE_APPARATUS_ID,
        name="Detroit Police Department",
        class_character=ClassCharacter.BOURGEOIS,
        consciousness_tendency=ConsciousnessTendency.LIBERAL,
        jurisdiction=JurisdictionLevel.COUNTY,
        territory_ids=policed_territory_ids[:3],
        cohesion=0.8,
        cadre_level=0.6,
        budget=100.0,
        heat=0.3,
        violence_capacity=0.6,
        surveillance_capacity=0.5,
        faction_balance=balance,
        rng_seed=0,
    )


# ---------------------------------------------------------------------------
# Public factory function
# ---------------------------------------------------------------------------


def create_wayne_county_scenario(
    extraction_efficiency: float = 0.8,
    repression_level: float = 0.6,
) -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Create the Wayne County Organizer scenario.

    A single-player strategy game centered on Wayne County, Michigan.
    The player controls a small political organization trying to build
    power in one of America's most class-stratified counties.

    Args:
        extraction_efficiency: Alpha in imperial rent formula (default 0.8).
        repression_level: Base repression (default 0.6 — Detroit is heavily policed).

    Returns:
        Tuple of (WorldState, SimulationConfig, GameDefines).
    """
    # Generate H3 hex grid
    territories = _create_wayne_county_territories()
    territory_ids = list(territories.keys())

    # Create social classes
    entities = _create_wayne_county_entities()

    # Create relationships (exploitation, wages, solidarity, tenancy)
    relationships = _create_wayne_county_relationships(territory_ids, territories)

    # Create player organization in a Detroit periphery hex
    detroit_hexes = [
        tid for tid, t in territories.items() if t.territory_type == TerritoryType.PERIPHERY
    ]
    player_org = _create_player_org(detroit_hexes)

    # Create the state apparatus NPC (Feature 039 activation — see
    # _create_state_apparatus_org's docstring).
    state_apparatus_org = _create_state_apparatus_org(detroit_hexes)

    # Assemble WorldState
    state = WorldState(
        tick=0,
        entities=entities,
        territories=territories,
        organizations={
            _PLAYER_ORG_ID: player_org,
            _STATE_APPARATUS_ID: state_apparatus_org,
        },
        relationships=relationships,
        event_log=[],
        # EH ruling 6 (owner 2026-07-16): the engine-side player pointer —
        # EpistemicHorizonSystem computes player-relative C_p/I_c from it.
        player_org_id=_PLAYER_ORG_ID,
    )

    # Configuration
    config = SimulationConfig()

    # Game defines tuned for Wayne County dynamics
    economy_defines = EconomyDefines(
        extraction_efficiency=extraction_efficiency,
        superwage_multiplier=1.3,  # Moderate imperial rent bribe
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
