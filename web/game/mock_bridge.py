"""MockEngineBridge — deterministic mock for full-stack end-to-end testing.

Implements the same interface as ``StubEngineBridge`` but persists state in
``GameSession.snapshot_json`` and advances it deterministically.  Every tick
produces identical output for identical input — no RNG.

This bridge lights up **all** Spec 042 UI components:
- DeckGLMap (H3 hexagons with real Wayne/Oakland/Macomb indexes)
- GraphView (orgs + institutions + territories + edges → Sigma.js topology)
- TimeSeries (tick summaries from TickSummary extraction)
- Inspector (full TerritoryState / OrgState / InstitutionState)
- TopBar indicators (derived.imperial_rent, avg_consciousness, etc.)
- ResourcePanel (vanguard economy on player org)
- TrapIndicator (TrapDetectionResult)
- ActionComposer (available verbs)
- EventLog (per-tick events)

Conforms to **Spec 052 — WorldState Snapshot Contract v0**.

.. warning::
    This file is disposable scaffolding.  It will be replaced by real engine
    wiring.  Do NOT extend with complex logic or calibrate against these values.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from .mock_defines import MockDefines
from .models import ActionResult, GameSession, PlayerAction

logger = logging.getLogger(__name__)

DEFINES = MockDefines()

# --------------------------------------------------------------------------- #
# H3 indexes — resolution-4 hexes covering Wayne, Oakland, Macomb counties
# --------------------------------------------------------------------------- #
# These are real H3 indexes that will render as actual hexagons on the map.
_MOCK_TERRITORIES: list[dict[str, Any]] = [
    {
        "id": "terr-wayne-01",
        "name": "Downtown Detroit",
        "h3_index": "842a9b7ffffffff",
        "h3_resolution": 7,
        "county_fips": "26163",
        "state_fips": "26",
        "state_name": "Michigan",
        "cz_id": "19804",
        "cz_name": "Detroit CZ",
        "bea_ea_code": "DET",
        "bea_ea_name": "Detroit-Warren-Ann Arbor",
        "msa_code": "19820",
        "msa_name": "Detroit-Warren-Dearborn",
        "sector_type": "urban_core",
        "territory_type": "metropolitan",
        "profile": "HIGH_PROFILE",
        "rent_level": 0.85,
        "population": 245000,
        "heat": 0.35,
        "biocapacity": 0.2,
        "host_id": None,
        "occupant_id": None,
        "under_eviction": False,
    },
    {
        "id": "terr-wayne-02",
        "name": "Midtown Detroit",
        "h3_index": "842a9b5ffffffff",
        "h3_resolution": 7,
        "county_fips": "26163",
        "state_fips": "26",
        "state_name": "Michigan",
        "cz_id": "19804",
        "cz_name": "Detroit CZ",
        "bea_ea_code": "DET",
        "bea_ea_name": "Detroit-Warren-Ann Arbor",
        "msa_code": "19820",
        "msa_name": "Detroit-Warren-Dearborn",
        "sector_type": "mixed",
        "territory_type": "metropolitan",
        "profile": "HIGH_PROFILE",
        "rent_level": 0.70,
        "population": 180000,
        "heat": 0.28,
        "biocapacity": 0.25,
        "host_id": None,
        "occupant_id": None,
        "under_eviction": False,
    },
    {
        "id": "terr-wayne-03",
        "name": "Southwest Detroit",
        "h3_index": "842a9adffffffff",
        "h3_resolution": 7,
        "county_fips": "26163",
        "state_fips": "26",
        "state_name": "Michigan",
        "cz_id": "19804",
        "cz_name": "Detroit CZ",
        "bea_ea_code": "DET",
        "bea_ea_name": "Detroit-Warren-Ann Arbor",
        "msa_code": "19820",
        "msa_name": "Detroit-Warren-Dearborn",
        "sector_type": "industrial",
        "territory_type": "metropolitan",
        "profile": "LOW_PROFILE",
        "rent_level": 0.45,
        "population": 95000,
        "heat": 0.42,
        "biocapacity": 0.3,
        "host_id": None,
        "occupant_id": None,
        "under_eviction": False,
    },
    {
        "id": "terr-wayne-04",
        "name": "Dearborn",
        "h3_index": "842a9a9ffffffff",
        "h3_resolution": 7,
        "county_fips": "26163",
        "state_fips": "26",
        "state_name": "Michigan",
        "cz_id": "19804",
        "cz_name": "Detroit CZ",
        "bea_ea_code": "DET",
        "bea_ea_name": "Detroit-Warren-Ann Arbor",
        "msa_code": "19820",
        "msa_name": "Detroit-Warren-Dearborn",
        "sector_type": "suburban",
        "territory_type": "metropolitan",
        "profile": "LOW_PROFILE",
        "rent_level": 0.55,
        "population": 110000,
        "heat": 0.15,
        "biocapacity": 0.4,
        "host_id": None,
        "occupant_id": None,
        "under_eviction": False,
    },
    {
        "id": "terr-wayne-05",
        "name": "Downriver",
        "h3_index": "842a987ffffffff",
        "h3_resolution": 7,
        "county_fips": "26163",
        "state_fips": "26",
        "state_name": "Michigan",
        "cz_id": "19804",
        "cz_name": "Detroit CZ",
        "bea_ea_code": "DET",
        "bea_ea_name": "Detroit-Warren-Ann Arbor",
        "msa_code": "19820",
        "msa_name": "Detroit-Warren-Dearborn",
        "sector_type": "industrial",
        "territory_type": "suburban",
        "profile": "LOW_PROFILE",
        "rent_level": 0.35,
        "population": 75000,
        "heat": 0.20,
        "biocapacity": 0.5,
        "host_id": None,
        "occupant_id": None,
        "under_eviction": False,
    },
    {
        "id": "terr-oakland-01",
        "name": "Pontiac",
        "h3_index": "842a995ffffffff",
        "h3_resolution": 7,
        "county_fips": "26125",
        "state_fips": "26",
        "state_name": "Michigan",
        "cz_id": "19804",
        "cz_name": "Detroit CZ",
        "bea_ea_code": "DET",
        "bea_ea_name": "Detroit-Warren-Ann Arbor",
        "msa_code": "19820",
        "msa_name": "Detroit-Warren-Dearborn",
        "sector_type": "urban_core",
        "territory_type": "metropolitan",
        "profile": "HIGH_PROFILE",
        "rent_level": 0.40,
        "population": 62000,
        "heat": 0.30,
        "biocapacity": 0.35,
        "host_id": None,
        "occupant_id": None,
        "under_eviction": False,
    },
    {
        "id": "terr-oakland-02",
        "name": "Troy/Sterling Heights",
        "h3_index": "842a993ffffffff",
        "h3_resolution": 7,
        "county_fips": "26125",
        "state_fips": "26",
        "state_name": "Michigan",
        "cz_id": "19804",
        "cz_name": "Detroit CZ",
        "bea_ea_code": "DET",
        "bea_ea_name": "Detroit-Warren-Ann Arbor",
        "msa_code": "19820",
        "msa_name": "Detroit-Warren-Dearborn",
        "sector_type": "suburban",
        "territory_type": "suburban",
        "profile": "LOW_PROFILE",
        "rent_level": 0.75,
        "population": 185000,
        "heat": 0.08,
        "biocapacity": 0.6,
        "host_id": None,
        "occupant_id": None,
        "under_eviction": False,
    },
    {
        "id": "terr-oakland-03",
        "name": "Bloomfield Hills",
        "h3_index": "842a991ffffffff",
        "h3_resolution": 7,
        "county_fips": "26125",
        "state_fips": "26",
        "state_name": "Michigan",
        "cz_id": "19804",
        "cz_name": "Detroit CZ",
        "bea_ea_code": "DET",
        "bea_ea_name": "Detroit-Warren-Ann Arbor",
        "msa_code": "19820",
        "msa_name": "Detroit-Warren-Dearborn",
        "sector_type": "residential",
        "territory_type": "suburban",
        "profile": "LOW_PROFILE",
        "rent_level": 0.92,
        "population": 45000,
        "heat": 0.03,
        "biocapacity": 0.7,
        "host_id": None,
        "occupant_id": None,
        "under_eviction": False,
    },
    {
        "id": "terr-macomb-01",
        "name": "Warren",
        "h3_index": "842a9cdffffffff",
        "h3_resolution": 7,
        "county_fips": "26099",
        "state_fips": "26",
        "state_name": "Michigan",
        "cz_id": "19804",
        "cz_name": "Detroit CZ",
        "bea_ea_code": "DET",
        "bea_ea_name": "Detroit-Warren-Ann Arbor",
        "msa_code": "19820",
        "msa_name": "Detroit-Warren-Dearborn",
        "sector_type": "industrial",
        "territory_type": "suburban",
        "profile": "LOW_PROFILE",
        "rent_level": 0.50,
        "population": 139000,
        "heat": 0.18,
        "biocapacity": 0.45,
        "host_id": None,
        "occupant_id": None,
        "under_eviction": False,
    },
    {
        "id": "terr-macomb-02",
        "name": "Clinton Township",
        "h3_index": "842a9cbffffffff",
        "h3_resolution": 7,
        "county_fips": "26099",
        "state_fips": "26",
        "state_name": "Michigan",
        "cz_id": "19804",
        "cz_name": "Detroit CZ",
        "bea_ea_code": "DET",
        "bea_ea_name": "Detroit-Warren-Ann Arbor",
        "msa_code": "19820",
        "msa_name": "Detroit-Warren-Dearborn",
        "sector_type": "suburban",
        "territory_type": "suburban",
        "profile": "LOW_PROFILE",
        "rent_level": 0.60,
        "population": 102000,
        "heat": 0.10,
        "biocapacity": 0.55,
        "host_id": None,
        "occupant_id": None,
        "under_eviction": False,
    },
]

# --------------------------------------------------------------------------- #
# Organizations — the only agents (Spec 052 §6)
# --------------------------------------------------------------------------- #
_MOCK_ORGS: list[dict[str, Any]] = [
    {
        "id": "org-peoples-front",
        "name": "People's United Front",
        "org_type": "civil_society_org",
        "class_character": "proletarian",
        "cohesion": 0.60,
        "cadre_level": 0.35,
        "budget": 12.0,
        "heat": 0.20,
        "territory_ids": ["terr-wayne-01", "terr-wayne-03"],
        "hyperedge_memberships": ["hx-new-afrikan", "hx-women"],
        "consciousness": {
            "liberal": 0.10,
            "fascist": 0.05,
            "revolutionary": 0.85,
        },
        "ooda": {
            "observe": 0.6,
            "orient": 0.5,
            "decide": 0.7,
            "act": 0.8,
            "cycle_ticks": 1,
        },
        "vanguard": {
            "cadre_labor": 8.0,
            "sympathizer_labor": 15.0,
            "reputation": 0.45,
            "budget": 12.0,
            "heat": 0.20,
            "max_cadre_labor": 20.0,
            "max_sympathizer_labor": 50.0,
        },
    },
    {
        "id": "org-state-apparatus",
        "name": "Michigan State Apparatus",
        "org_type": "state_apparatus",
        "class_character": "bourgeois",
        "cohesion": 0.85,
        "cadre_level": 0.70,
        "budget": 200.0,
        "heat": 0.05,
        "territory_ids": ["terr-wayne-01", "terr-oakland-01", "terr-macomb-01"],
        "hyperedge_memberships": ["hx-settler"],
        "consciousness": {
            "liberal": 0.70,
            "fascist": 0.20,
            "revolutionary": 0.10,
        },
        "ooda": {
            "observe": 0.8,
            "orient": 0.7,
            "decide": 0.6,
            "act": 0.5,
            "cycle_ticks": 2,
        },
        "vanguard": None,
    },
    {
        "id": "org-auto-union",
        "name": "Auto Workers Union",
        "org_type": "civil_society_org",
        "class_character": "proletarian",
        "cohesion": 0.50,
        "cadre_level": 0.25,
        "budget": 8.0,
        "heat": 0.10,
        "territory_ids": ["terr-wayne-05", "terr-macomb-01"],
        "hyperedge_memberships": ["hx-settler"],
        "consciousness": {
            "liberal": 0.60,
            "fascist": 0.10,
            "revolutionary": 0.30,
        },
        "ooda": {
            "observe": 0.5,
            "orient": 0.4,
            "decide": 0.5,
            "act": 0.6,
            "cycle_ticks": 2,
        },
        "vanguard": {
            "cadre_labor": 5.0,
            "sympathizer_labor": 25.0,
            "reputation": 0.55,
            "budget": 8.0,
            "heat": 0.10,
            "max_cadre_labor": 15.0,
            "max_sympathizer_labor": 60.0,
        },
    },
    {
        "id": "org-proud-boys",
        "name": "Settler Reactionary Militia",
        "org_type": "political_faction",
        "class_character": "settler",
        "cohesion": 0.70,
        "cadre_level": 0.40,
        "budget": 15.0,
        "heat": 0.30,
        "territory_ids": ["terr-macomb-02", "terr-oakland-02"],
        "hyperedge_memberships": ["hx-settler", "hx-patriarchal"],
        "consciousness": {
            "liberal": 0.05,
            "fascist": 0.85,
            "revolutionary": 0.10,
        },
        "ooda": {
            "observe": 0.4,
            "orient": 0.3,
            "decide": 0.6,
            "act": 0.7,
            "cycle_ticks": 1,
        },
        "vanguard": None,
    },
    {
        "id": "org-finance-bloc",
        "name": "Detroit Finance Bloc",
        "org_type": "business",
        "class_character": "bourgeois",
        "cohesion": 0.90,
        "cadre_level": 0.80,
        "budget": 350.0,
        "heat": 0.02,
        "territory_ids": ["terr-wayne-01", "terr-oakland-03"],
        "hyperedge_memberships": ["hx-settler"],
        "consciousness": {
            "liberal": 0.75,
            "fascist": 0.15,
            "revolutionary": 0.10,
        },
        "ooda": {
            "observe": 0.9,
            "orient": 0.8,
            "decide": 0.7,
            "act": 0.4,
            "cycle_ticks": 3,
        },
        "vanguard": None,
    },
]

# --------------------------------------------------------------------------- #
# Institutions (Spec 052 §7)
# --------------------------------------------------------------------------- #
_MOCK_INSTITUTIONS: list[dict[str, Any]] = [
    {
        "id": "inst-city-hall",
        "name": "Detroit City Hall",
        "apparatus_type": "executive",
        "social_function": "governance",
        "class_inscription": "bourgeois-democratic",
        "legitimacy": 0.55,
        "budget": 80.0,
        "housed_org_ids": ["org-state-apparatus"],
        "territory_ids": ["terr-wayne-01"],
        "factional_composition": {
            "liberal_technocratic": 0.45,
            "revanchist_fascist": 0.25,
            "institutionalist_bonapartist": 0.30,
        },
    },
    {
        "id": "inst-dpd",
        "name": "Detroit Police Department",
        "apparatus_type": "repressive",
        "social_function": "coercion",
        "class_inscription": "settler-colonial",
        "legitimacy": 0.35,
        "budget": 45.0,
        "housed_org_ids": [],
        "territory_ids": ["terr-wayne-01", "terr-wayne-02", "terr-wayne-03"],
        "factional_composition": {
            "liberal_technocratic": 0.15,
            "revanchist_fascist": 0.60,
            "institutionalist_bonapartist": 0.25,
        },
    },
]

# --------------------------------------------------------------------------- #
# Edges — dyadic flows between orgs (Spec 052 §10)
# --------------------------------------------------------------------------- #
_MOCK_EDGES: list[dict[str, Any]] = [
    {
        "id": "edge-finance-peoples-01",
        "source_id": "org-finance-bloc",
        "target_id": "org-peoples-front",
        "mode": "EXTRACTIVE",
        "value_flow": 25.0,
        "tension": 0.65,
        "repression_flow": 0.0,
    },
    {
        "id": "edge-finance-auto-01",
        "source_id": "org-finance-bloc",
        "target_id": "org-auto-union",
        "mode": "TRANSACTIONAL",
        "value_flow": 18.0,
        "tension": 0.15,
        "repression_flow": 0.0,
    },
    {
        "id": "edge-peoples-auto-01",
        "source_id": "org-peoples-front",
        "target_id": "org-auto-union",
        "mode": "SOLIDARISTIC",
        "value_flow": 3.0,
        "tension": 0.05,
        "repression_flow": 0.0,
    },
    {
        "id": "edge-state-peoples-01",
        "source_id": "org-state-apparatus",
        "target_id": "org-peoples-front",
        "mode": "EXTRACTIVE",
        "value_flow": 8.0,
        "tension": 0.55,
        "repression_flow": 3.0,
    },
    {
        "id": "edge-proud-peoples-01",
        "source_id": "org-proud-boys",
        "target_id": "org-peoples-front",
        "mode": "ANTAGONISTIC",
        "value_flow": 0.0,
        "tension": 0.80,
        "repression_flow": 2.0,
    },
    {
        "id": "edge-state-finance-01",
        "source_id": "org-state-apparatus",
        "target_id": "org-finance-bloc",
        "mode": "CO_OPTIVE",
        "value_flow": 12.0,
        "tension": 0.10,
        "repression_flow": 0.0,
    },
]

# --------------------------------------------------------------------------- #
# Hyperedges — XGI layer (Spec 052 §9)
# --------------------------------------------------------------------------- #
_MOCK_HYPEREDGES: list[dict[str, Any]] = [
    {
        "id": "hx-new-afrikan",
        "category": "contradiction_pair",
        "label": "NEW_AFRIKAN",
        "contradiction_partner_id": "hx-settler",
        "member_ids": [
            "org-peoples-front",
            "terr-wayne-01",
            "terr-wayne-02",
            "terr-wayne-03",
        ],
        "material_basis": {
            "description": (
                "Structural position under settler-colonial capital accumulation in Wayne County"
            ),
            "indicators": [
                "residential_segregation",
                "wealth_gap",
                "incarceration_rate",
            ],
        },
        "ideological_dimension": {
            "collective_identity_strength": 0.55,
            "organizational_vehicles": ["org-peoples-front"],
        },
    },
    {
        "id": "hx-settler",
        "category": "contradiction_pair",
        "label": "SETTLER",
        "contradiction_partner_id": "hx-new-afrikan",
        "member_ids": [
            "org-state-apparatus",
            "org-auto-union",
            "org-proud-boys",
            "org-finance-bloc",
            "terr-oakland-02",
            "terr-oakland-03",
            "terr-macomb-01",
            "terr-macomb-02",
        ],
        "material_basis": {
            "description": (
                "Beneficiary position in settler-colonial wealth distribution "
                "across Macomb/Oakland counties"
            ),
            "indicators": [
                "property_ownership",
                "median_income",
                "policing_investment",
            ],
        },
        "ideological_dimension": {
            "collective_identity_strength": 0.70,
            "organizational_vehicles": [
                "org-state-apparatus",
                "org-proud-boys",
            ],
        },
    },
    {
        "id": "hx-women",
        "category": "contradiction_pair",
        "label": "WOMEN",
        "contradiction_partner_id": "hx-patriarchal",
        "member_ids": ["org-peoples-front", "terr-wayne-01"],
        "material_basis": {
            "description": "Gendered division of reproductive labor",
            "indicators": ["wage_gap", "care_burden", "domestic_violence_rate"],
        },
        "ideological_dimension": {
            "collective_identity_strength": 0.40,
            "organizational_vehicles": ["org-peoples-front"],
        },
    },
    {
        "id": "hx-patriarchal",
        "category": "contradiction_pair",
        "label": "PATRIARCHAL",
        "contradiction_partner_id": "hx-women",
        "member_ids": ["org-proud-boys"],
        "material_basis": {
            "description": "Structural beneficiaries of gendered labour extraction",
            "indicators": ["income_premium", "property_control"],
        },
        "ideological_dimension": {
            "collective_identity_strength": 0.60,
            "organizational_vehicles": ["org-proud-boys"],
        },
    },
    {
        "id": "hx-incarcerated",
        "category": "institutional_exclusion",
        "label": "INCARCERATED",
        "contradiction_partner_id": None,
        "member_ids": ["terr-wayne-01", "terr-wayne-03"],
        "material_basis": {
            "description": (
                "Population under carceral control in Wayne County — "
                "load-bearing for territorial heat dynamics"
            ),
            "indicators": [
                "incarceration_rate",
                "recidivism",
                "bail_poverty",
            ],
        },
        "ideological_dimension": {
            "collective_identity_strength": 0.20,
            "organizational_vehicles": [],
        },
    },
]

# --------------------------------------------------------------------------- #
# Derived block (Spec 052 §11) — engine-computed, read-only cache
# --------------------------------------------------------------------------- #
_MOCK_DERIVED: dict[str, Any] = {
    "value_tensor": {
        "departments": ["I", "IIa", "IIb", "III"],
        "components": ["c", "v", "s"],
        "values": [
            [40.0, 20.0, 12.0],  # Dept I  — means of production
            [15.0, 10.0, 6.0],  # Dept IIa — wage goods
            [8.0, 5.0, 3.0],  # Dept IIb — luxury goods
            [0.0, 12.0, 4.0],  # Dept III — reproductive labor
        ],
        "conservation_residual": 0.0,
    },
    "imperial_rent": {
        "unequal_exchange": 6.2,
        "externalized_reproductive": 5.1,
        "domestic_shadow": 4.2,
        "total": 15.5,
    },
    "dept_iii_visibility": {
        "g33": 0.12,
    },
    "class_aggregates": {
        "proletariat": {
            "population": 850000,
            "wage_share": 0.38,
            "agitation_proxy": 0.20,
        },
        "labor_aristocracy": {
            "population": 210000,
            "wage_share": 0.28,
            "agitation_proxy": 0.05,
        },
        "petite_bourgeoisie": {
            "population": 320000,
            "wage_share": 0.18,
            "agitation_proxy": 0.08,
        },
        "bourgeoisie": {
            "population": 45000,
            "wage_share": 0.14,
            "agitation_proxy": 0.02,
        },
        "lumpenproletariat": {
            "population": 120000,
            "wage_share": 0.02,
            "agitation_proxy": 0.30,
        },
    },
    "economy": {
        "gdp": 180.0,
        "gini": 0.62,
        "profit_rate": 0.18,
        "exploitation_rate": 0.55,
    },
    "predictions": {
        "per_hyperedge": {
            "hx-new-afrikan": {
                "p_acquiescence": 0.55,
                "p_revolution": 0.18,
                "warsaw_ghetto_corollary_triggered": False,
            },
            "hx-settler": {
                "p_acquiescence": 0.85,
                "p_revolution": 0.02,
                "warsaw_ghetto_corollary_triggered": False,
            },
        },
    },
}

_MOCK_TRAPS: dict[str, Any] = {
    "liberal": {
        "severity": "none",
        "score": 0.1,
        "indicators": ["electoralism_drift"],
        "ticks_at_moderate": 0,
    },
    "ultra_left": {
        "severity": "none",
        "score": 0.05,
        "indicators": ["adventurism_risk"],
        "ticks_at_moderate": 0,
    },
    "rightist": {
        "severity": "none",
        "score": 0.08,
        "indicators": ["nativist_framing"],
        "ticks_at_moderate": 0,
    },
    "active_trap": None,
    "game_over_trap": None,
}


def _build_initial_snapshot(session_id: str, tick: int = 0) -> dict[str, Any]:
    """Build the canonical initial mock snapshot.

    Produces a snapshot dict conforming to **Spec 052 — WorldState Snapshot
    Contract v0**.  The top-level shape is::

        {tick, session_id, organizations, institutions, territories,
         hyperedges, edges, events, traps, derived}

    Note what is absent: no ``entities`` array, no top-level ``economy``.
    """
    import copy

    return {
        "session_id": session_id,
        "tick": tick,
        "organizations": copy.deepcopy(_MOCK_ORGS),
        "institutions": copy.deepcopy(_MOCK_INSTITUTIONS),
        "territories": copy.deepcopy(_MOCK_TERRITORIES),
        "hyperedges": copy.deepcopy(_MOCK_HYPEREDGES),
        "edges": copy.deepcopy(_MOCK_EDGES),
        "events": [
            {"type": "GAME_STARTED", "tick": tick, "data": {"scenario": "wayne_county_mock"}}
        ],
        "traps": copy.deepcopy(_MOCK_TRAPS),
        "derived": copy.deepcopy(_MOCK_DERIVED),
    }


# --------------------------------------------------------------------------- #
# MockEngineBridge
# --------------------------------------------------------------------------- #


class MockEngineBridge:
    """Deterministic engine bridge for MVP end-to-end testing.

    Persists world state in ``GameSession.snapshot_json`` and advances it
    using the coefficients in ``MockDefines``.  No randomness — identical
    inputs always produce identical outputs.

    Conforms to **Spec 052 — WorldState Snapshot Contract v0**.

    .. warning::
        Non-empirical scaffolding.  Do NOT calibrate against this.
    """

    def __init__(self) -> None:
        self._defines = DEFINES

    # ------------------------------------------------------------------ #
    # Game lifecycle
    # ------------------------------------------------------------------ #

    def create_game(
        self,
        player_id: int,
        scenario: str = "wayne_county",
        config: dict[str, Any] | None = None,
        defines: dict[str, Any] | None = None,
        rng_seed: int = 0,
    ) -> dict[str, Any]:
        """Create a new game session with initial snapshot."""
        session_id = str(uuid.uuid4())
        snapshot = _build_initial_snapshot(session_id)

        GameSession.objects.create(
            id=session_id,
            player_id=player_id,
            scenario=scenario,
            current_tick=0,
            status="active",
            config_json=config or {},
            game_defines_json=defines or {},
            snapshot_json=snapshot,
            rng_seed=rng_seed,
        )

        logger.info("MockEngineBridge: created game session=%s", session_id)
        return {
            "id": session_id,
            "scenario": scenario,
            "current_tick": 0,
            "status": "active",
            "created_at": str(GameSession.objects.get(id=session_id).created_at),
        }

    # ------------------------------------------------------------------ #
    # State retrieval
    # ------------------------------------------------------------------ #

    def get_snapshot(self, session_id: uuid.UUID) -> dict[str, Any]:
        """Return the current snapshot from snapshot_json."""
        session = GameSession.objects.get(id=session_id)
        snapshot = session.snapshot_json
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)
        result: dict[str, Any] = dict(snapshot) if isinstance(snapshot, dict) else {}
        return result

    def get_game_state(self, session_id: uuid.UUID) -> dict[str, Any]:
        """Alias for get_snapshot — used by the state endpoint."""
        return self.get_snapshot(session_id)

    def get_map_data(self, session_id: uuid.UUID, **_kwargs: Any) -> dict[str, Any]:
        """Return GeoJSON-shaped map data from territories."""
        snap = self.get_snapshot(session_id)
        features = []
        for t in snap.get("territories", []):
            derived_economy = snap.get("derived", {}).get("economy", {})
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "id": t["id"],
                        "name": t["name"],
                        "heat": t["heat"],
                        "profit_rate": derived_economy.get("profit_rate", 0),
                        "exploitation_rate": derived_economy.get("exploitation_rate", 0),
                        "occ": t.get("rent_level", 0),
                        "imperial_rent": snap.get("derived", {})
                        .get("imperial_rent", {})
                        .get("total", 0),
                        "org_presence": len(
                            [
                                o
                                for o in snap.get("organizations", [])
                                if t["id"] in o.get("territory_ids", [])
                            ]
                        ),
                    },
                    "geometry": None,  # DeckGLMap uses H3, not GeoJSON geometry
                }
            )
        return {
            "type": "FeatureCollection",
            "features": features,
        }

    # ------------------------------------------------------------------ #
    # Tick resolution — the core deterministic algorithm
    # ------------------------------------------------------------------ #

    def resolve_tick(
        self,
        session_id: uuid.UUID,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Resolve one tick of mock progression.

        Algorithm:
        1. Increment tick
        2. Apply passive drift (heat decay)
        3. Apply verb effects from pending PlayerAction rows
        4. Write ActionResult rows
        5. Recompute events
        6. Persist mutated snapshot to snapshot_json
        """
        session = GameSession.objects.get(id=session_id)
        snapshot = session.snapshot_json
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)

        old_tick = snapshot.get("tick", 0)
        new_tick = old_tick + 1
        snapshot["tick"] = new_tick
        d = self._defines

        # 1. Passive drift — heat decays
        for t in snapshot.get("territories", []):
            t["heat"] = self._clamp(
                t["heat"] * d.HEAT_DECAY,
                d.HEAT_FLOOR,
                d.HEAT_CEILING,
            )

        # 2. Process pending actions
        pending = PlayerAction.objects.filter(
            session_id=session_id,
            tick=old_tick,
            resolved=False,
        )

        events: list[dict[str, Any]] = []
        for action in pending:
            result = self._apply_verb(snapshot, action, d)
            ActionResult.objects.create(
                session_id=session_id,
                tick=new_tick,
                org_id=action.org_id,
                action_type=action.verb,
                target_id=action.target_id,
                initiative_score=d.INITIATIVE_SCORE,
                action_cost=d.ACTION_COST,
                success=True,
                consciousness_delta=result.get("consciousness_delta", 0),
                heat_delta=result.get("heat_delta", 0),
                details=json.dumps(result.get("details", {})),
            )
            action.resolved = True
            action.save()

            events.append(
                {
                    "type": f"ACTION_{action.verb.upper()}",
                    "tick": new_tick,
                    "data": {
                        "org_id": action.org_id,
                        "target_id": action.target_id,
                        "verb": action.verb,
                    },
                }
            )

        # 3. Always emit a tick event
        events.append({"type": "TICK_RESOLVED", "tick": new_tick, "data": {"old_tick": old_tick}})
        snapshot["events"] = events

        # 4. Update session_id in snapshot
        snapshot["session_id"] = str(session_id)

        # 5. Persist
        GameSession.objects.filter(id=session_id).update(
            snapshot_json=snapshot,
            current_tick=new_tick,
        )

        logger.info(
            "MockEngineBridge: resolved tick %d→%d session=%s", old_tick, new_tick, session_id
        )
        tick_result: dict[str, Any] = dict(snapshot)
        return tick_result

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def submit_action(
        self,
        session_id: uuid.UUID,
        org_id: str,
        verb: str,
        action_type: str | None = None,
        target_id: str | None = None,
        target_community: str | None = None,
        params_json: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Record a player action for resolution on next tick."""
        session = GameSession.objects.get(id=session_id)
        PlayerAction.objects.create(
            session_id=str(session.id),
            tick=session.current_tick,
            org_id=org_id,
            verb=verb,
            action_type=action_type or verb,
            target_id=target_id or "",
            target_community=target_community or "",
            params_json=json.dumps(params_json or {}),
        )
        return {"status": "ok", "action": verb, "tick": session.current_tick}

    def get_available_actions(
        self, session_id: uuid.UUID, org_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Return available actions for all player orgs."""
        snap = self.get_snapshot(session_id)
        actions: list[dict[str, Any]] = []
        player_orgs = [o for o in snap.get("organizations", []) if o.get("vanguard") is not None]
        territories = snap.get("territories", [])

        for org in player_orgs:
            if org_id and org["id"] != org_id:
                continue
            for verb in ["educate", "mobilize", "attack", "campaign", "aid", "reproduce"]:
                targets = [t["id"] for t in territories[:3]]
                actions.append(
                    {
                        "org_id": org["id"],
                        "verb": verb,
                        "action_type": verb,
                        "targets": targets,
                        "cost": 1,
                    }
                )
        return actions

    # ------------------------------------------------------------------ #
    # Dashboard / inspector endpoints
    # ------------------------------------------------------------------ #

    def get_game_summary(self, session_id: uuid.UUID) -> dict[str, Any]:
        """Return game summary for the TopBar indicators."""
        snap = self.get_snapshot(session_id)
        derived: dict[str, Any] = snap.get("derived", {})
        economy: dict[str, Any] = derived.get("economy", {})
        imperial_rent: dict[str, Any] = derived.get("imperial_rent", {})
        return {
            "tick": snap.get("tick", 0),
            "profit_rate": economy.get("profit_rate", 0),
            "exploitation_rate": economy.get("exploitation_rate", 0),
            "phi": imperial_rent.get("total", 0),
            "hegemon": "institutionalist_bonapartist",
            "alerts": [],
        }

    def get_economy_summary(self, session_id: uuid.UUID) -> dict[str, Any]:
        """Return economy summary from derived block."""
        snap = self.get_snapshot(session_id)
        economy: dict[str, Any] = snap.get("derived", {}).get("economy", {})
        return economy

    def get_phase_space(self, _session_id: uuid.UUID) -> dict[str, Any]:
        return {}

    def get_class_analysis(self, _session_id: uuid.UUID) -> dict[str, Any]:
        return {}

    def get_event_log(self, session_id: uuid.UUID) -> list[dict[str, Any]]:
        snap = self.get_snapshot(session_id)
        events: list[dict[str, Any]] = snap.get("events", [])
        return events

    def get_solidarity_network(self, _session_id: uuid.UUID) -> dict[str, Any]:
        return {}

    def get_trap_status(self, session_id: uuid.UUID) -> dict[str, Any]:
        snap = self.get_snapshot(session_id)
        traps: dict[str, Any] = snap.get("traps", {})
        return traps

    # ------------------------------------------------------------------ #
    # Map Snapshot (GeoJSON for DeckGLMap)
    # ------------------------------------------------------------------ #

    def get_map_snapshot(
        self,
        session_id: uuid.UUID,
        tick: int | None = None,
        layer: str | None = None,
        zoom: str = "county",
    ) -> dict[str, Any]:
        """Return a GeoJSON FeatureCollection for the hex map.

        Supports multi-scale spatial rendering: when ``zoom`` is an admin
        framing level (state, county, cz, bea_ea, msa), hex-level features
        are aggregated into administrative groupings.  For ``zoom=hex``,
        individual hex features are returned.
        """
        snap = self.get_snapshot(session_id)
        effective_tick = tick if tick is not None else snap.get("tick", 0)
        derived_economy = snap.get("derived", {}).get("economy", {})
        imperial_rent_total = snap.get("derived", {}).get("imperial_rent", {}).get("total", 0)

        # Build raw hex-level feature list
        raw_features: list[dict[str, Any]] = []
        for t in snap.get("territories", []):
            raw_features.append(
                {
                    "type": "Feature",
                    "id": t["id"],
                    "properties": {
                        "h3_index": t.get("h3_index"),
                        "county_fips": t.get("county_fips", "26163"),
                        "state_fips": t.get("state_fips", "26"),
                        "state_name": t.get("state_name", "Michigan"),
                        "cz_id": t.get("cz_id", "19804"),
                        "cz_name": t.get("cz_name", "Detroit CZ"),
                        "bea_ea_code": t.get("bea_ea_code", "DET"),
                        "bea_ea_name": t.get("bea_ea_name", "Detroit-Warren-Ann Arbor"),
                        "msa_code": t.get("msa_code", "19820"),
                        "msa_name": t.get("msa_name", "Detroit-Warren-Dearborn"),
                        "county_name": t["name"],
                        "heat": t["heat"],
                        "consciousness": 0.0,
                        "wealth": 0.0,
                        "rent": t.get("rent_level", 0),
                        "biocapacity": t.get("biocapacity", 1.0),
                        "population": t.get("population", 0),
                        "profit_rate": derived_economy.get("profit_rate", 0),
                        "exploitation_rate": derived_economy.get("exploitation_rate", 0),
                        "occ": t.get("rent_level", 0),
                        "imperial_rent": imperial_rent_total,
                        "org_presence": len(
                            [
                                o
                                for o in snap.get("organizations", [])
                                if t["id"] in o.get("territory_ids", [])
                            ]
                        ),
                    },
                    "geometry": None,
                }
            )

        # Framing-level group keys
        _FRAMING_KEYS: dict[str, tuple[str, str]] = {
            "state": ("state_fips", "state_name"),
            "county": ("county_fips", "county_name"),
            "cz": ("cz_id", "cz_name"),
            "bea_ea": ("bea_ea_code", "bea_ea_name"),
            "bea": ("bea_ea_code", "bea_ea_name"),
            "msa": ("msa_code", "msa_name"),
        }

        if zoom == "hex":
            features = raw_features
        elif zoom in _FRAMING_KEYS:
            key_field, name_field = _FRAMING_KEYS[zoom]
            features = self._aggregate_features(raw_features, key_field, name_field, zoom)
        else:
            features = raw_features

        return {
            "type": "FeatureCollection",
            "metadata": {
                "tick": effective_tick,
                "scenario": "wayne_county_mock",
                "h3_resolution": 4,
                "zoom": zoom,
                "layer": layer,
                "available_metrics": [
                    "heat",
                    "consciousness",
                    "wealth",
                    "rent",
                    "biocapacity",
                    "population",
                    "profit_rate",
                    "exploitation_rate",
                    "occ",
                    "imperial_rent",
                    "org_presence",
                ],
            },
            "features": features,
        }

    @staticmethod
    def _aggregate_features(
        raw_features: list[dict[str, Any]],
        key_field: str,
        name_field: str,
        zoom: str,
    ) -> list[dict[str, Any]]:
        """Aggregate hex features into admin groupings.

        Population is summed; all other numeric metrics are mean-averaged.
        ``org_presence`` is summed (total org touches in the admin area).
        """
        groups: dict[str, list[dict[str, Any]]] = {}
        for f in raw_features:
            props = f.get("properties", {})
            key = props.get(key_field, "unknown")
            groups.setdefault(key, []).append(props)

        _SUM_FIELDS = {"population", "org_presence"}
        _MEAN_FIELDS = {
            "heat",
            "consciousness",
            "wealth",
            "rent",
            "biocapacity",
            "profit_rate",
            "exploitation_rate",
            "occ",
            "imperial_rent",
        }

        aggregated: list[dict[str, Any]] = []
        for group_key, members in groups.items():
            agg_props: dict[str, Any] = {
                "group_key": group_key,
                "group_name": members[0].get(name_field, group_key),
                "group_level": zoom,
                "hex_count": len(members),
            }
            # Copy all framing identifiers from first member
            for fk in (
                "county_fips",
                "state_fips",
                "state_name",
                "cz_id",
                "cz_name",
                "bea_ea_code",
                "bea_ea_name",
                "msa_code",
                "msa_name",
            ):
                agg_props[fk] = members[0].get(fk)

            for field in _SUM_FIELDS:
                agg_props[field] = sum(m.get(field, 0) for m in members)
            for field in _MEAN_FIELDS:
                vals = [m.get(field, 0) for m in members]
                agg_props[field] = sum(vals) / len(vals) if vals else 0

            aggregated.append(
                {
                    "type": "Feature",
                    "id": f"{zoom}:{group_key}",
                    "properties": agg_props,
                    "geometry": None,
                }
            )
        return aggregated

    # ------------------------------------------------------------------ #
    # Spatial Multi-Scale Endpoints
    # ------------------------------------------------------------------ #

    def get_org_network(
        self,
        session_id: uuid.UUID,
        territory_filter: str | None = None,
    ) -> dict[str, Any]:
        """Return the org-network graph for topology visualization.

        Nodes are organizations, institutions, and territories.
        Edges encode PRESENCE, EXPLOITATION, SOLIDARITY, and other edge modes.
        """
        snap = self.get_snapshot(session_id)
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        # Organization nodes
        for o in snap.get("organizations", []):
            org_territory_ids = o.get("territory_ids", [])
            if territory_filter and territory_filter not in org_territory_ids:
                continue
            nodes.append(
                {
                    "id": o["id"],
                    "type": "organization",
                    "attributes": {
                        "name": o.get("name", ""),
                        "class_character": o.get("class_character", ""),
                        "org_type": o.get("org_type", ""),
                        "cohesion": o.get("cohesion", 0),
                        "cadre_level": o.get("cadre_level", 0),
                    },
                }
            )
            # PRESENCE edges: org → territory
            for tid in org_territory_ids:
                edges.append(
                    {
                        "source": o["id"],
                        "target": tid,
                        "mode": "PRESENCE",
                        "attributes": {"weight": 1.0},
                    }
                )

        # Institution nodes
        for inst in snap.get("institutions", []):
            inst_territory_ids = inst.get("territory_ids", [])
            if territory_filter and territory_filter not in inst_territory_ids:
                continue
            nodes.append(
                {
                    "id": inst["id"],
                    "type": "institution",
                    "attributes": {
                        "name": inst.get("name", ""),
                        "inst_type": inst.get("inst_type", ""),
                        "legitimacy": inst.get("legitimacy", 0),
                    },
                }
            )

        # Territory nodes
        for t in snap.get("territories", []):
            if territory_filter and t["id"] != territory_filter:
                continue
            nodes.append(
                {
                    "id": t["id"],
                    "type": "territory",
                    "attributes": {
                        "name": t.get("name", ""),
                        "county_fips": t.get("county_fips", ""),
                        "h3_index": t.get("h3_index", ""),
                        "population": t.get("population", 0),
                    },
                }
            )

        # Inter-org edges from snapshot relationships
        for rel in snap.get("relationships", []):
            edges.append(
                {
                    "source": rel.get("source", ""),
                    "target": rel.get("target", ""),
                    "mode": rel.get("edge_type", "TRANSACTIONAL"),
                    "attributes": {
                        "weight": rel.get("weight", 1.0),
                        "intensity": rel.get("intensity", 0),
                    },
                }
            )

        return {
            "tick": snap.get("tick", 0),
            "nodes": nodes,
            "edges": edges,
        }

    def get_hypergraph_communities(
        self,
        session_id: uuid.UUID,
        territory_filter: str | None = None,
    ) -> dict[str, Any]:
        """Return hyperedge/community data for graph visualization.

        Each hyperedge represents an N-ary community membership.
        """
        snap = self.get_snapshot(session_id)
        hyperedges: list[dict[str, Any]] = []

        for hx in snap.get("hyperedges", []):
            members = hx.get("members", [])
            if territory_filter:
                # Filter to members that operate in the specified territory
                filtered_members = []
                for m in members:
                    for o in snap.get("organizations", []):
                        if o["id"] == m and territory_filter in o.get("territory_ids", []):
                            filtered_members.append(m)
                            break
                if not filtered_members:
                    continue
                members = filtered_members

            hyperedges.append(
                {
                    "id": hx.get("id", ""),
                    "community_type": hx.get("community_type", ""),
                    "category": hx.get("category", ""),
                    "members": members,
                }
            )

        return {
            "tick": snap.get("tick", 0),
            "hyperedges": hyperedges,
        }

    def get_infrastructure(
        self,
        session_id: uuid.UUID,
        _bbox: list[float] | None = None,
    ) -> dict[str, Any]:
        """Return infrastructure network for map overlay.

        Currently returns minimal mock data — infrastructure modeling
        is a future phase.
        """
        snap = self.get_snapshot(session_id)
        return {
            "tick": snap.get("tick", 0),
            "nodes": [],
            "edges": [],
        }

    # ------------------------------------------------------------------ #
    # Domain Dashboards (scaffold stubs for API completeness)
    # ------------------------------------------------------------------ #

    def get_game_timeseries(self, _session_id: uuid.UUID) -> dict[str, Any]:
        """Return empty time series — frontend accumulates via extractSummary."""
        return {"data": []}

    def get_economy_dashboard(self, _session_id: uuid.UUID) -> dict[str, Any]:
        return {}

    def get_communities_dashboard(self, _session_id: uuid.UUID) -> dict[str, Any]:
        return {}

    def get_organizations_dashboard(self, _session_id: uuid.UUID) -> dict[str, Any]:
        return {}

    def get_edges_dashboard(self, _session_id: uuid.UUID) -> dict[str, Any]:
        return {}

    def get_state_apparatus_dashboard(self, _session_id: uuid.UUID) -> dict[str, Any]:
        return {}

    def get_journal_dashboard(self, _session_id: uuid.UUID) -> dict[str, Any]:
        return {}

    def get_alerts_dashboard(self, _session_id: uuid.UUID) -> dict[str, Any]:
        return {}

    # ------------------------------------------------------------------ #
    # Inspector Views
    # ------------------------------------------------------------------ #

    def get_inspector_node(self, session_id: uuid.UUID, node_id: str) -> dict[str, Any]:
        """Return org or institution detail by ID for the inspector panel."""
        snap = self.get_snapshot(session_id)
        for o in snap.get("organizations", []):
            if o["id"] == node_id:
                return dict(o)
        for i in snap.get("institutions", []):
            if i["id"] == node_id:
                return dict(i)
        return {"id": node_id, "type": "node", "details": "Not found"}

    def get_inspector_org(self, session_id: uuid.UUID, org_id: str) -> dict[str, Any]:
        """Return organization detail by ID for the inspector panel."""
        snap = self.get_snapshot(session_id)
        for o in snap.get("organizations", []):
            if o["id"] == org_id:
                return dict(o)
        return {"id": org_id, "type": "organization", "details": "Not found"}

    def get_inspector_community(self, session_id: uuid.UUID, hyperedge_id: str) -> dict[str, Any]:
        """Return hyperedge detail by ID."""
        snap = self.get_snapshot(session_id)
        for hx in snap.get("hyperedges", []):
            if hx["id"] == hyperedge_id:
                return dict(hx)
        return {"id": hyperedge_id, "type": "community"}

    def get_inspector_edge(self, session_id: uuid.UUID, edge_id: str) -> dict[str, Any]:
        """Return edge detail by ID."""
        snap = self.get_snapshot(session_id)
        for e in snap.get("edges", []):
            if e["id"] == edge_id:
                return dict(e)
        return {"id": edge_id, "type": "edge"}

    def get_inspector_hex(self, session_id: uuid.UUID, h3_index: str) -> dict[str, Any]:
        """Return territory detail by H3 index for the inspector panel."""
        snap = self.get_snapshot(session_id)
        for t in snap.get("territories", []):
            if t.get("h3_index") == h3_index:
                return dict(t)
        return {
            "h3_index": h3_index,
            "county_fips": "26163",
            "county_name": "Wayne County",
            "population": 0,
            "heat": 0.0,
        }

    def preview_action(
        self,
        _session_id: uuid.UUID,
        _org_id: str,
        _verb: str,
        _target_id: str,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Return a preview of the action's expected effects."""
        return {
            "status": "ok",
            "preview": {
                "consciousness_delta": 0.05,
                "heat_delta": 0.02,
                "cost": 1.0,
                "success_probability": 0.8,
            },
        }

    # Verb-specific endpoints (return minimal stubs)
    # Parameters are part of the interface contract but unused in mock mode.
    def get_educate_targets(self, _session_id: uuid.UUID, _org_id: str) -> dict[str, Any]:
        return {"status": "ok", "targets": [], "unavailable_communities": []}

    def get_aid_targets(self, _session_id: uuid.UUID, _org_id: str) -> dict[str, Any]:
        return {"status": "ok", "targets": [], "unavailable_targets": []}

    def get_attack_targets(self, _session_id: uuid.UUID, _org_id: str) -> dict[str, Any]:
        return {
            "status": "ok",
            "targets": {"organizations": [], "edges": [], "institutions": []},
            "unavailable_targets": [],
        }

    def get_mobilize_targets(self, _session_id: uuid.UUID, _org_id: str) -> dict[str, Any]:
        return {"status": "ok", "targets": []}

    def get_campaign_targets(self, _session_id: uuid.UUID, _org_id: str) -> dict[str, Any]:
        return {"status": "ok", "targets": []}

    def get_reproduce_targets(self, _session_id: uuid.UUID, _org_id: str) -> dict[str, Any]:
        return {"status": "ok", "targets": []}

    def get_investigate_targets(self, _session_id: uuid.UUID, _org_id: str) -> dict[str, Any]:
        return {"status": "ok", "targets": []}

    def get_move_targets(self, _session_id: uuid.UUID, _org_id: str) -> dict[str, Any]:
        return {"status": "ok", "targets": []}

    def get_negotiate_targets(self, _session_id: uuid.UUID, _org_id: str) -> dict[str, Any]:
        return {"status": "ok", "targets": []}

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _apply_verb(
        self,
        snapshot: dict[str, Any],
        action: PlayerAction,
        d: MockDefines,
    ) -> dict[str, Any]:
        """Apply a single verb's effect to the snapshot (mutates in place)."""
        verb = action.verb.lower()
        dispatch = {
            "educate": self._verb_educate,
            "mobilize": self._verb_mobilize,
            "attack": self._verb_attack,
            "campaign": self._verb_campaign,
            "aid": self._verb_aid,
            "reproduce": self._verb_reproduce,
        }
        handler = dispatch.get(verb)
        if handler is None:
            return {"consciousness_delta": 0, "heat_delta": 0, "details": {}}
        return handler(snapshot, action, d)

    def _verb_educate(
        self, snapshot: dict[str, Any], action: PlayerAction, d: MockDefines
    ) -> dict[str, Any]:
        target_id = action.target_id or ""
        # Shift org consciousness toward revolutionary
        for org in snapshot.get("organizations", []):
            c = org.get("consciousness", {})
            rev = c.get("revolutionary", 0)
            lib = c.get("liberal", 0)
            delta = min(d.EDUCATE_CONSCIOUSNESS, lib)
            c["revolutionary"] = min(1.0, rev + delta)
            c["liberal"] = max(0.0, lib - delta)
        for t in snapshot.get("territories", []):
            if t["id"] == target_id:
                t["heat"] = self._clamp(t["heat"] + d.EDUCATE_HEAT, d.HEAT_FLOOR, d.HEAT_CEILING)
        return {
            "consciousness_delta": d.EDUCATE_CONSCIOUSNESS,
            "heat_delta": d.EDUCATE_HEAT,
            "details": {},
        }

    def _verb_mobilize(
        self, snapshot: dict[str, Any], action: PlayerAction, d: MockDefines
    ) -> dict[str, Any]:
        target_id = action.target_id or ""
        for t in snapshot.get("territories", []):
            if t["id"] == target_id:
                t["heat"] = self._clamp(t["heat"] + d.MOBILIZE_HEAT, d.HEAT_FLOOR, d.HEAT_CEILING)
        # Bump agitation_proxy in derived
        derived = snapshot.get("derived", {})
        aggs = derived.get("class_aggregates", {})
        for cls_key in ("proletariat", "lumpenproletariat"):
            cls = aggs.get(cls_key, {})
            cls["agitation_proxy"] = min(1.0, cls.get("agitation_proxy", 0) + d.MOBILIZE_AGITATION)
        return {"consciousness_delta": 0, "heat_delta": d.MOBILIZE_HEAT, "details": {}}

    def _verb_attack(
        self, snapshot: dict[str, Any], action: PlayerAction, d: MockDefines
    ) -> dict[str, Any]:
        target_id = action.target_id or ""
        for t in snapshot.get("territories", []):
            if t["id"] == target_id:
                t["heat"] = self._clamp(t["heat"] + d.ATTACK_HEAT, d.HEAT_FLOOR, d.HEAT_CEILING)
        # Shift org consciousness toward revolutionary, reduce budget
        for org in snapshot.get("organizations", []):
            c = org.get("consciousness", {})
            rev = c.get("revolutionary", 0)
            lib = c.get("liberal", 0)
            delta = min(d.ATTACK_CONSCIOUSNESS, lib)
            c["revolutionary"] = min(1.0, rev + delta)
            c["liberal"] = max(0.0, lib - delta)
            org["budget"] = max(0.0, org["budget"] - d.ATTACK_WEALTH_DAMAGE)
        return {
            "consciousness_delta": d.ATTACK_CONSCIOUSNESS,
            "heat_delta": d.ATTACK_HEAT,
            "details": {},
        }

    def _verb_campaign(
        self, snapshot: dict[str, Any], _action: PlayerAction, d: MockDefines
    ) -> dict[str, Any]:
        for org in snapshot.get("organizations", []):
            c = org.get("consciousness", {})
            rev = c.get("revolutionary", 0)
            lib = c.get("liberal", 0)
            delta = min(d.CAMPAIGN_CONSCIOUSNESS, lib)
            c["revolutionary"] = min(1.0, rev + delta)
            c["liberal"] = max(0.0, lib - delta)
        return {"consciousness_delta": d.CAMPAIGN_CONSCIOUSNESS, "heat_delta": 0, "details": {}}

    def _verb_aid(
        self, snapshot: dict[str, Any], action: PlayerAction, d: MockDefines
    ) -> dict[str, Any]:
        target_id = action.target_id or ""
        for t in snapshot.get("territories", []):
            if t["id"] == target_id:
                t["heat"] = self._clamp(t["heat"] + d.AID_HEAT, d.HEAT_FLOOR, d.HEAT_CEILING)
        # Increase proletariat wage_share in derived
        derived = snapshot.get("derived", {})
        aggs = derived.get("class_aggregates", {})
        prolet = aggs.get("proletariat", {})
        prolet["wage_share"] = prolet.get("wage_share", 0) + d.AID_WEALTH * 0.01
        return {"consciousness_delta": 0, "heat_delta": d.AID_HEAT, "details": {}}

    def _verb_reproduce(
        self, snapshot: dict[str, Any], action: PlayerAction, d: MockDefines
    ) -> dict[str, Any]:
        for org in snapshot.get("organizations", []):
            if org["id"] == action.org_id:
                org["cohesion"] = min(1.0, org["cohesion"] + d.REPRODUCE_COHESION)
        return {
            "consciousness_delta": 0,
            "heat_delta": 0,
            "details": {"membership_delta": d.REPRODUCE_MEMBERSHIP},
        }

    @staticmethod
    def _clamp(value: float, floor: float, ceiling: float) -> float:
        """Clamp a value between floor and ceiling."""
        return max(floor, min(ceiling, value))
