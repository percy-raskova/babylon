"""Stub engine bridge — returns correctly-shaped mock data.

Use this when running the Django server without the real Babylon engine
or a PostgreSQL database. All methods return deterministic, realistic-looking
data that matches the frontend's type contracts exactly.

Usage::

    from game.stub_bridge import StubEngineBridge
    game.api._bridge_instance = StubEngineBridge()

Or set ``BABYLON_STUB_BRIDGE=1`` to auto-initialize in ``_get_bridge()``.
"""

from __future__ import annotations

import logging
import random
from typing import Any
from uuid import UUID, uuid4

from .map_contract import MAP_HISTORY_REPLAYABLE_METRICS, MAP_METRIC_PROPERTIES

logger = logging.getLogger(__name__)

# Session-local state for the stub
_stub_sessions: dict[UUID, dict[str, Any]] = {}
_stub_actions: dict[UUID, list[dict[str, Any]]] = {}


def _make_wayne_county_entities() -> list[dict[str, Any]]:
    """Return 4 social class entities matching the Wayne County scenario."""
    return [
        {
            "id": "C001",
            "name": "Detroit Proletariat",
            "role": "proletariat",
            "wealth": 15.0,
            "consciousness": 0.35,
            "national_identity": 0.6,
            "agitation": 0.2,
            "organization": 0.15,
            "repression": 0.3,
            "p_acquiescence": 0.72,
            "p_revolution": 0.08,
            "subsistence": 10.0,
            "population": 350000,
            "inequality": 0.65,
            "active": True,
        },
        {
            "id": "C002",
            "name": "Suburban Petit-Bourgeois",
            "role": "petit_bourgeoisie",
            "wealth": 85.0,
            "consciousness": 0.15,
            "national_identity": 0.8,
            "agitation": 0.05,
            "organization": 0.10,
            "repression": 0.1,
            "p_acquiescence": 0.92,
            "p_revolution": 0.01,
            "subsistence": 30.0,
            "population": 180000,
            "inequality": 0.45,
            "active": True,
        },
        {
            "id": "C003",
            "name": "Wayne County Bourgeoisie",
            "role": "bourgeoisie",
            "wealth": 500.0,
            "consciousness": 0.05,
            "national_identity": 0.9,
            "agitation": 0.0,
            "organization": 0.60,
            "repression": 0.05,
            "p_acquiescence": 0.99,
            "p_revolution": 0.0,
            "subsistence": 100.0,
            "population": 25000,
            "inequality": 0.30,
            "active": True,
        },
        {
            "id": "C004",
            "name": "Downriver Workers",
            "role": "proletariat",
            "wealth": 20.0,
            "consciousness": 0.25,
            "national_identity": 0.7,
            "agitation": 0.15,
            "organization": 0.12,
            "repression": 0.25,
            "p_acquiescence": 0.78,
            "p_revolution": 0.05,
            "subsistence": 12.0,
            "population": 120000,
            "inequality": 0.55,
            "active": True,
        },
    ]


def _make_territories() -> list[dict[str, Any]]:
    """Return territory list for Wayne County."""
    return [
        {
            "id": "T001",
            "name": "Downtown Detroit",
            "h3_index": "872a30d8affffff",
            "heat": 0.45,
            "sector_type": "INDUSTRIAL",
            "territory_type": "URBAN",
            "profile": "HIGH_PROFILE",
            "rent_level": 1200.0,
            "population": 65000,
            "under_eviction": False,
            "biocapacity": 0.3,
            "host_id": "C003",
            "occupant_id": "C001",
        },
        {
            "id": "T002",
            "name": "Dearborn",
            "h3_index": "872a30d8bffffff",
            "heat": 0.20,
            "sector_type": "MIXED",
            "territory_type": "SUBURBAN",
            "profile": "LOW_PROFILE",
            "rent_level": 900.0,
            "population": 98000,
            "under_eviction": False,
            "biocapacity": 0.5,
            "host_id": "C002",
            "occupant_id": "C004",
        },
        {
            "id": "T003",
            "name": "Downriver",
            "h3_index": "872a30d8cffffff",
            "heat": 0.10,
            "sector_type": "INDUSTRIAL",
            "territory_type": "PERIURBAN",
            "profile": "LOW_PROFILE",
            "rent_level": 600.0,
            "population": 120000,
            "under_eviction": False,
            "biocapacity": 0.7,
            "host_id": "C002",
            "occupant_id": "C004",
        },
        {
            "id": "T004",
            "name": "Grosse Pointe",
            "h3_index": "872a30d8dffffff",
            "heat": 0.05,
            "sector_type": "RESIDENTIAL",
            "territory_type": "SUBURBAN",
            "profile": "LOW_PROFILE",
            "rent_level": 2500.0,
            "population": 45000,
            "under_eviction": False,
            "biocapacity": 0.6,
            "host_id": "C003",
            "occupant_id": "C002",
        },
    ]


def _make_organizations() -> list[dict[str, Any]]:
    """Return organizations for Wayne County."""
    return [
        {
            "id": "ORG001",
            "name": "Wayne County Organizing Committee",
            "org_type": "civil_society",
            "class_character": "proletarian",
            "cohesion": 0.55,
            "cadre_level": 0.10,
            "budget": 100.0,
            "heat": 0.0,
            "territory_ids": ["T001", "T002"],
            "consciousness_tendency": "revolutionary",
            "vanguard": {
                "cadre_labor": 1.0,
                "sympathizer_labor": 4.0,
                "reputation": 0.0,
                "budget": 100.0,
                "heat": 0.0,
                "max_cadre_labor": 3.0,
                "max_sympathizer_labor": 10.0,
            },
        },
    ]


def _make_institutions() -> list[dict[str, Any]]:
    """Return institutions for Wayne County."""
    return [
        {
            "id": "INST001",
            "name": "Wayne County DPD",
            "apparatus_type": "REPRESSIVE",
            "social_function": "policing",
            "class_inscription": "bourgeois",
            "legitimacy": 0.65,
            "budget": 500.0,
            "housed_org_ids": [],
            "territory_ids": ["T001", "T002", "T003"],
            "hegemonic_fraction": "institutionalist_bonapartist",
            "liberal_technocratic": 0.2,
            "revanchist_fascist": 0.3,
            "institutionalist_bonapartist": 0.5,
        },
    ]


def _make_edges() -> list[dict[str, Any]]:
    """Return relationship edges."""
    return [
        {
            "source_id": "C001",
            "target_id": "C004",
            "edge_type": "SOLIDARITY",
            "value_flow": 0.0,
            "tension": 0.1,
            "solidarity_strength": 0.4,
        },
        {
            "source_id": "C003",
            "target_id": "C001",
            "edge_type": "EXPLOITATION",
            "value_flow": 50.0,
            "tension": 0.6,
            "solidarity_strength": 0.0,
        },
    ]


def _make_events(tick: int) -> list[dict[str, Any]]:
    """Return sample events for a tick."""
    return [
        {
            "type": "IMPERIAL_RENT_EXTRACTION",
            "tick": tick,
            "data": {
                "source": "C003",
                "target": "C001",
                "amount": 50.0,
            },
        },
    ]


def _make_traps() -> dict[str, Any]:
    """Return initial trap detection results."""
    return {
        "liberal": {
            "trap_type": "liberal",
            "severity": "none",
            "score": 0.1,
            "indicators": [],
            "ticks_at_moderate": 0,
        },
        "ultra_left": {
            "trap_type": "ultra_left",
            "severity": "none",
            "score": 0.0,
            "indicators": [],
            "ticks_at_moderate": 0,
        },
        "rightist": {
            "trap_type": "rightist",
            "severity": "none",
            "score": 0.0,
            "indicators": [],
            "ticks_at_moderate": 0,
        },
        "active_trap": None,
        "game_over_trap": None,
    }


def _make_hex_features(tick: int, layer: str | None = None) -> list[dict[str, Any]]:
    """Generate GeoJSON hex features with per-hex mock metric data.

    Each hex has a deterministic but varied value for every metric,
    so per-layer map endpoints return different colors across the map.
    """
    # Wayne County h3 resolution-7 sample cells
    cells = [
        ("872a30d8affffff", "Downtown Detroit", "26127"),
        ("872a30d8bffffff", "Dearborn", "26163"),
        ("872a30d8cffffff", "Downriver (Wyandotte)", "26163"),
        ("872a30d8dffffff", "Grosse Pointe", "26163"),
        ("872a30d80ffffff", "Hamtramck", "26163"),
        ("872a30d81ffffff", "Highland Park", "26163"),
        ("872a30d82ffffff", "Redford Township", "26163"),
        ("872a30d83ffffff", "Inkster", "26163"),
    ]

    features: list[dict[str, Any]] = []
    for i, (h3_idx, name, fips) in enumerate(cells):
        # Deterministic pseudo-random per-cell variation
        seed = hash(h3_idx) % 1000
        r = seed / 1000.0

        props: dict[str, Any] = {
            "h3_index": h3_idx,
            "county_fips": fips,
            "county_name": name,
            "heat": round(0.1 + r * 0.8, 3),
            "consciousness": round(0.05 + r * 0.6, 3),
            "wealth": round(10.0 + r * 300.0, 1),
            "rent": round(400.0 + r * 2000.0, 0),
            "biocapacity": round(0.2 + (1.0 - r) * 0.7, 3),
            "population": int(5000 + r * 95000),
            # Original geo-economic metrics
            "profit_rate": round(0.02 + r * 0.12, 4),
            "exploitation_rate": round(0.3 + r * 0.5, 3),
            "occ": round(1.5 + r * 4.0, 2),
            "imperial_rent": round(r * 80.0, 1),
            "org_presence": round(r * 0.5, 3),
            "dominant_class": "proletariat" if r < 0.6 else "petit_bourgeoisie",
            # Spec-113 Lane D: deterministic per-cell SOLIDARITY-edge density,
            # matching the real bridge's population-weighted 0..~a-few range.
            "solidarity_index": round(r * 1.5, 3),
            # Wave 2 W2.4: deterministic per-cell throughput position (real
            # bridge range is centered near 1.0, the national π baseline) and
            # agitation (0..~a-few, matching solidarity_index's range).
            "throughput_position": round(0.5 + r * 1.0, 3),
            "agitation": round(r * 1.5, 3),
            # Real TerritoryType values only (CORE/PERIPHERY) — deliberately
            # NOT the legacy URBAN/SUBURBAN/PERIURBAN vocabulary _make_territories()
            # uses for the (unrelated) territories snapshot list.
            "territory_type": "core" if r < 0.5 else "periphery",
            # Audit Wave 4 straggler (task #76): deterministic per-cell
            # degree-centrality, matching the real bridge's [0, 1] range.
            "centrality": round(r, 3),
            # Wave 5 receptivity lens pair: deterministic per-cell M_r
            # (matching the real bridge's [0, 1] range) and its threshold-
            # derived vision_state (desert < 0.2, water >= 0.8, mud between —
            # the corpus's own thresholds, EpistemicHorizonDefines defaults).
            "mass_receptivity": round(r, 3),
            "vision_state": "desert" if r < 0.2 else ("water" if r >= 0.8 else "mud"),
            # Feature 021 lens pair: deterministic per-cell wage-discipline
            # coefficient (matching the real bridge's [0, wage_pressure_ceiling]
            # range, default ceiling 0.5) and composite dispossession
            # intensity (matching the real bridge's [0, 1] range).
            "wage_pressure": round(r * 0.5, 3),
            "dispossession_intensity": round(r, 3),
        }

        # Approximate hex boundary as a small polygon near Detroit
        lat_base = 42.33 + i * 0.015
        lng_base = -83.05 + i * 0.012
        boundary = [
            [lng_base, lat_base],
            [lng_base + 0.01, lat_base + 0.005],
            [lng_base + 0.01, lat_base + 0.015],
            [lng_base, lat_base + 0.02],
            [lng_base - 0.01, lat_base + 0.015],
            [lng_base - 0.01, lat_base + 0.005],
            [lng_base, lat_base],  # close ring
        ]

        features.append(
            {
                "type": "Feature",
                "id": h3_idx,
                "geometry": {"type": "Polygon", "coordinates": [boundary]},
                "properties": props,
            }
        )

    return features


def _make_aggregated_features(zoom: str, tick: int) -> list[dict[str, Any]]:
    """Generate mock aggregated features for non-hex zoom levels.

    Returns correctly-shaped GeoJSON features grouped by the zoom tier
    with population-weighted averages for numeric metrics.
    """
    # Mock data for each zoom level — Michigan-specific
    zoom_data: dict[str, list[tuple[str, str, int]]] = {
        "state": [("26", "Michigan", 10_037_000)],
        "bea": [
            ("DET", "Detroit-Warren-Ann Arbor", 5_400_000),
            ("GRR", "Grand Rapids-Muskegon-Holland", 1_500_000),
            ("LAN", "Lansing-East Lansing", 550_000),
            ("KAL", "Kalamazoo-Battle Creek-Portage", 480_000),
            ("SAG", "Saginaw-Midland-Bay City", 380_000),
            ("TVC", "Traverse City-Northern Lower", 620_000),
            ("MQT", "Marquette-Upper Peninsula", 307_000),
            ("CHI", "Chicago-Naperville (cross-border)", 130_000),
        ],
        "msa": [
            ("19820", "Detroit-Warren-Dearborn", 4_300_000),
            ("24340", "Grand Rapids-Kentwood", 1_070_000),
            ("29620", "Lansing-East Lansing", 478_000),
            ("25980", "Kalamazoo-Portage", 265_000),
            ("22420", "Flint", 406_000),
            ("11460", "Ann Arbor", 372_000),
            ("40980", "Saginaw", 190_000),
        ],
        "county": [
            ("26163", "Wayne County", 1_750_000),
            ("26125", "Oakland County", 1_275_000),
            ("26099", "Macomb County", 880_000),
            ("26081", "Kent County", 660_000),
            ("26049", "Genesee County", 406_000),
            ("26161", "Washtenaw County", 372_000),
            ("26065", "Ingham County", 285_000),
        ],
    }

    groups = zoom_data.get(zoom, zoom_data["county"])
    features: list[dict[str, Any]] = []

    for key, name, pop in groups:
        # Deterministic pseudo-random variation per group
        seed = hash(key + str(tick)) % 1000
        r = seed / 1000.0

        features.append(
            {
                "type": "Feature",
                "id": key,
                "geometry": None,  # Geometry from reference polygons
                "properties": {
                    "group_key": key,
                    "group_name": name,
                    "zoom": zoom,
                    "hex_count": int(pop / 250),  # Approximate hex density
                    "profit_rate": round(0.02 + r * 0.12, 6),
                    "exploitation_rate": round(0.3 + r * 0.5, 4),
                    "occ": round(1.5 + r * 4.0, 4),
                    "imperial_rent": round(r * 80.0, 2),
                    "heat": round(0.1 + r * 0.8, 4),
                    "org_presence": int(r * 500),
                    "population": pop,
                    # Spec-113 Lane D: matches the real bridge's population-
                    # weighted-mode categorical / weighted-mean numeric
                    # aggregation at every non-hex zoom.
                    "dominant_class": "proletariat" if r < 0.6 else "petit_bourgeoisie",
                    "solidarity_index": round(r * 1.5, 3),
                    # Wave 2 W2.4: same population-weighted-mode categorical /
                    # weighted-mean numeric aggregation shape as above.
                    "throughput_position": round(0.5 + r * 1.0, 3),
                    "agitation": round(r * 1.5, 3),
                    "territory_type": "core" if r < 0.5 else "periphery",
                    # Audit Wave 4 straggler (task #76): same deterministic
                    # per-group degree-centrality shape as above.
                    "centrality": round(r, 3),
                    # Wave 5 receptivity lens pair: same deterministic
                    # per-group M_r/vision_state shape as _make_hex_features.
                    "mass_receptivity": round(r, 3),
                    "vision_state": "desert" if r < 0.2 else ("water" if r >= 0.8 else "mud"),
                    # Feature 021 lens pair: same deterministic per-group
                    # wage_pressure/dispossession_intensity shape as
                    # _make_hex_features.
                    "wage_pressure": round(r * 0.5, 3),
                    "dispossession_intensity": round(r, 3),
                },
            }
        )

    return features


# Spec-113 Lane D: deterministic mock ``/explain/`` catalog — same 9 metric
# names + response shape as ``game.provenance.METRIC_PROVENANCE`` (real
# bridge), so frontend dev against the stub (no Postgres/engine) exercises
# the exact same InspectionStack FormulaCard code path. Deliberately does
# NOT import ``game.provenance`` (which pulls in ``game.engine_bridge`` and
# transitively ``babylon.engine``/``babylon.persistence``) — this whole
# module's point is to boot Django with zero engine/DB dependency weight,
# same as every other ``_make_*`` mock builder here.
_STUB_EXPLAIN_METRICS: dict[str, dict[str, Any]] = {
    "value_extraction_ratio": {
        "formula": {
            "name": None,
            "expression": "exchange_ratio = (value_produced + rent_extracted) / value_produced",
            "doc": "Graph-wide extraction proxy behind /economy/'s global exploitation_rate.",
        },
        "value": 1.82,
        "inputs": [
            {"name": "value_produced", "label": "Value produced", "value": 420.0, "kind": "state"},
            {"name": "rent_extracted", "label": "Rent extracted", "value": 344.4, "kind": "state"},
        ],
    },
    "exploitation_rate": {
        "formula": {
            "name": "exploitation_rate",
            "expression": "Convert exchange ratio to exploitation rate percentage.",
            "doc": "Convert exchange ratio to exploitation rate percentage.",
        },
        "value": 0.45,
        "inputs": [
            {
                "name": "exchange_ratio",
                "label": "Exchange ratio",
                "value": 1.82,
                "kind": "metric",
                "ref": "value_extraction_ratio",
            },
        ],
    },
    "profit_rate": {
        "formula": {
            "name": None,
            "expression": "rate of profit = s / (c + v) — not yet computed by any System",
            "doc": "No wired engine System computes this yet.",
        },
        "value": None,
        "inputs": [],
    },
    "occ": {
        "formula": {
            "name": None,
            "expression": "occ = c / v — not yet computed by any System",
            "doc": "No wired engine System computes this yet.",
        },
        "value": None,
        "inputs": [],
    },
    "imperial_rent": {
        "formula": {
            "name": None,
            "expression": "imperial_rent = state.economy.imperial_rent_pool",
            "doc": "Raw GlobalEconomy ledger balance, not a derived formula.",
        },
        "value": 50.0,
        "inputs": [],
    },
    "labor_aristocracy_ratio": {
        "formula": {
            "name": "labor_aristocracy_ratio",
            "expression": "Wc/Vc ratio. When > 1, worker receives more than produced.",
            "doc": "Wc/Vc ratio. When > 1, worker receives more than produced.",
        },
        "value": 1.2,
        "inputs": [
            {
                "name": "core_wages",
                "label": "Core wages (incoming WAGES edge flow)",
                "value": 102.0,
                "kind": "state",
            },
            {
                "name": "value_produced",
                "label": "Value produced (entity wealth)",
                "value": 85.0,
                "kind": "state",
            },
        ],
    },
    "revolution_probability": {
        "formula": {
            "name": "revolution_probability",
            "expression": "P(S|R) = Cohesion / (Repression + eps). Capped at 1.0.",
            "doc": "P(S|R) = Cohesion / (Repression + eps). Capped at 1.0.",
        },
        "value": 0.08,
        "inputs": [
            {
                "name": "cohesion",
                "label": "Cohesion (base class organization)",
                "value": 0.15,
                "kind": "state",
            },
            {"name": "repression", "label": "Repression faced", "value": 0.3, "kind": "state"},
        ],
    },
    "acquiescence_probability": {
        "formula": {
            "name": "acquiescence_probability",
            "expression": "P(S|A) sigmoid. At threshold, probability = 0.5.",
            "doc": "P(S|A) sigmoid. At threshold, probability = 0.5.",
        },
        "value": None,
        "inputs": [
            {"name": "wealth", "label": "Wealth", "value": 15.0, "kind": "state"},
            {
                "name": "subsistence_threshold",
                "label": "Subsistence threshold",
                "value": 10.0,
                "kind": "state",
            },
            {
                "name": "steepness_k",
                "label": "Sigmoid steepness (GameDefines survival.steepness_k)",
                "value": None,
                "kind": "constant",
            },
        ],
    },
    "consciousness_drift": {
        "formula": {
            "name": "consciousness_drift",
            "expression": "dPsi/dt = k(1 - Wc/Vc) - lambda*Psi + bifurcation.",
            "doc": "dPsi/dt = k(1 - Wc/Vc) - lambda*Psi + bifurcation.",
        },
        "value": None,
        "inputs": [
            {
                "name": "core_wages",
                "label": "Core wages (incoming WAGES edge flow)",
                "value": 102.0,
                "kind": "state",
            },
            {
                "name": "value_produced",
                "label": "Value produced (entity wealth)",
                "value": 85.0,
                "kind": "state",
            },
            {
                "name": "current_consciousness",
                "label": "Current class consciousness",
                "value": 0.35,
                "kind": "state",
            },
            {
                "name": "sensitivity_k",
                "label": "Sensitivity k (GameDefines)",
                "value": None,
                "kind": "constant",
            },
            {
                "name": "decay_lambda",
                "label": "Decay lambda (GameDefines)",
                "value": None,
                "kind": "constant",
            },
            {
                "name": "solidarity_pressure",
                "label": "Solidarity pressure (formula default)",
                "value": 0.0,
                "kind": "constant",
            },
            {
                "name": "wage_change",
                "label": "Wage change (formula default)",
                "value": 0.0,
                "kind": "constant",
            },
        ],
    },
}


def _stub_explain_response(metric: str, scope: str) -> dict[str, Any] | None:
    """Build one ``/explain/`` response body from :data:`_STUB_EXPLAIN_METRICS`.

    Returns ``None`` for an unknown metric (the view turns that into a
    404). Every known input dict gets a ``ref`` key defaulted to ``None``
    (matching the real bridge's always-present-key convention) and a
    ``constants`` list (the ``kind == "constant"`` subset of ``inputs``).
    """
    entry = _STUB_EXPLAIN_METRICS.get(metric)
    if entry is None:
        return None
    inputs = [{"ref": None, **row} for row in entry["inputs"]]
    constants = [row for row in inputs if row["kind"] == "constant"]
    return {
        "metric": metric,
        "scope": scope,
        "value": entry["value"],
        "formula": entry["formula"],
        "inputs": inputs,
        "constants": constants,
    }


def _stub_org_by_id(org_id: str) -> dict[str, Any] | None:
    """Look up one mock organization dict by id from :func:`_make_organizations`.

    Only ``ORG001`` exists in the stub's coherent Wayne County world — any
    other id honestly resolves to ``None``, matching the real bridge's
    "org absent from the graph" case.
    """
    for org in _make_organizations():
        if org["id"] == org_id:
            return org
    return None


def _stub_all_mock_nodes() -> list[dict[str, Any]]:
    """Every mock node dict across the stub's coherent Wayne County world —
    the same union :meth:`StubEngineBridge.get_snapshot` serves. Used only
    for the graph-wide numeric averages ``EngineBridge`` derives from the
    real hydrated graph (:func:`_stub_avg_attr`, consumed by
    ``get_endgame_state``/``get_journal_objectives``).
    """
    return [
        *_make_wayne_county_entities(),
        *_make_territories(),
        *_make_organizations(),
        *_make_institutions(),
    ]


def _stub_avg_attr(attr: str) -> float:
    """Mean of ``attr`` across every mock node that carries it.

    Matches ``EngineBridge``'s ``_compute_avg_node_attr`` semantics: nodes
    missing the attribute are skipped, and the mean is ``0.0`` when none
    carry it — never a fabricated nonzero default.
    """
    values = [float(node[attr]) for node in _stub_all_mock_nodes() if node.get(attr) is not None]
    return sum(values) / len(values) if values else 0.0


def _stub_vanguard_resources(
    *,
    cadre_level: float,
    cohesion: float,
    budget: float,
    heat: float,
    territory_count: int,
) -> dict[str, float]:
    """Reimplements ``VanguardResources.from_organization``'s formula inline.

    This module cannot import ``babylon.models.vanguard_resources`` —
    ``tests/unit/web/test_import_boundary.py`` statically forbids any
    ``babylon.models``/``babylon.config``/``babylon.engine``/``babylon.ooda``/
    ``babylon.persistence`` import outside ``game/engine_bridge.py`` (+ a
    couple of explicitly-listed exceptions the stub is deliberately not
    one of — its whole point is zero engine-package dependency weight).
    The formula itself (``CL_max = cadre_level * 10 * (1 - heat*0.5)``,
    ``SL_max = cohesion * territory_count * 5 * (1 - heat*0.3)``,
    ``CL = min(CL_max, budget/2)``, ``SL = min(SL_max, CL*2 + territory_count)``)
    is copied verbatim from ``src/babylon/models/vanguard_resources.py`` —
    real math, not invented, just duplicated across the import boundary.
    """
    heat_penalty_cl = 1.0 - heat * 0.5
    heat_penalty_sl = 1.0 - heat * 0.3
    max_cl = cadre_level * 10.0 * heat_penalty_cl
    max_sl = cohesion * max(territory_count, 1) * 5.0 * heat_penalty_sl
    cl = min(max_cl, budget / 2.0)
    sl = min(max_sl, cl * 2.0 + territory_count * 1.0)
    return {"cadre_labor": round(cl, 2), "sympathizer_labor": round(sl, 2), "budget": budget}


class StubEngineBridge:
    """Mock bridge that returns correctly-shaped data without engine deps.

    All methods match the ``EngineBridge`` interface so they can be used
    interchangeably in ``game.api._bridge_instance``. Parity (every public
    ``get_*`` method present with a compatible signature) is enforced by
    ``tests/unit/web/test_stub_bridge_parity.py``.
    """

    def __init__(self) -> None:
        logger.info("StubEngineBridge initialized — serving mock data")

    def create_game(
        self,
        scenario: str = "wayne_county",
        _config: dict[str, Any] | None = None,
        _defines: dict[str, Any] | None = None,
        _rng_seed: int = 0,
        player_id: int | None = None,
    ) -> UUID:
        """Create a mock game session and return its UUID.

        Also creates a GameSession Django model row so API views
        can look up the session via ``_get_session_or_none()``.
        """
        sid = uuid4()
        _stub_sessions[sid] = {
            "scenario": scenario,
            "tick": 0,
            "player_id": player_id,
        }
        _stub_actions[sid] = []

        # Persist a Django model row for API view lookups
        try:
            from game.models import GameSession

            GameSession.objects.create(
                id=sid,
                player_id=player_id,
                scenario=scenario,
                current_tick=0,
                status="active",
            )
        except Exception:
            logger.warning("Stub: could not create GameSession row for %s", sid)

        logger.info("Stub: created session=%s scenario=%s", sid, scenario)
        return sid

    def get_snapshot(self, session_id: UUID) -> dict[str, Any]:
        """Return a full game state snapshot with mock data."""
        session = _stub_sessions.get(session_id, {"tick": 0, "scenario": "wayne_county"})
        tick = session["tick"]
        return {
            "session_id": str(session_id),
            "tick": tick,
            "entities": _make_wayne_county_entities(),
            "territories": _make_territories(),
            "organizations": _make_organizations(),
            "institutions": _make_institutions(),
            "edges": _make_edges(),
            "economy": {
                "imperial_rent_total": 50.0,
                "avg_profit_rate": 0.08,
                "total_value_transfer": 120.0,
            },
            "events": _make_events(tick),
            "traps": _make_traps(),
        }

    def get_map_snapshot(
        self,
        session_id: UUID,
        tick: int | None = None,
        layer: str | None = None,
        zoom: str = "county",
    ) -> dict[str, Any]:
        """Return a GeoJSON FeatureCollection for the hex map.

        When zoom is 'hex', returns individual hex features.
        For higher zoom levels, returns aggregated mock data.
        """
        session = _stub_sessions.get(session_id, {"tick": 0, "scenario": "wayne_county"})
        effective_tick = tick if tick is not None else session["tick"]

        if zoom == "hex":
            features: list[dict[str, Any]] = _make_hex_features(effective_tick, layer)
        else:
            features = _make_aggregated_features(zoom, effective_tick)

        return {
            "type": "FeatureCollection",
            "metadata": {
                "tick": effective_tick,
                "scenario": session["scenario"],
                "h3_resolution": 7,
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
                    # Spec-113 Lane D
                    "dominant_class",
                    "solidarity_index",
                    # Wave 2 W2.4
                    "throughput_position",
                    "agitation",
                    "territory_type",
                    # Audit Wave 4 straggler (task #76)
                    "centrality",
                    # Wave 5 receptivity lens pair
                    "mass_receptivity",
                    "vision_state",
                    # Feature 021 lens pair
                    "wage_pressure",
                    "dispossession_intensity",
                ],
            },
            "features": features,
        }

    def get_map_history(
        self,
        _session_id: UUID,
        *,
        metric: str,
        from_tick: int | None = None,
        to_tick: int | None = None,
    ) -> dict[str, Any]:
        """Stub parity for GET /api/games/{id}/map/history/ (Backend-W3R3).

        The stub bridge persists nothing, so there is no historical map
        data to replay under any metric — mirrors the real
        ``EngineBridge.get_map_history``'s validation (unknown/
        non-replayable metric -> the same ``error``/``message`` shape) and
        its degrade-to-empty path when a persistence layer lacks the query
        capability (Constitution III.11: never fabricate frames).
        """
        if metric not in MAP_METRIC_PROPERTIES:
            return {
                "metric": metric,
                "from_tick": from_tick or 0,
                "to_tick": to_tick or 0,
                "capped": False,
                "frames": [],
                "error": "unknown_metric",
                "message": (
                    f"Invalid metric {metric!r}. Valid metrics: {sorted(MAP_METRIC_PROPERTIES)}"
                ),
            }
        if metric not in MAP_HISTORY_REPLAYABLE_METRICS:
            return {
                "metric": metric,
                "from_tick": from_tick or 0,
                "to_tick": to_tick or 0,
                "capped": False,
                "frames": [],
                "error": "not_replayable",
                "message": (
                    f"Metric {metric!r} has no persisted per-tick history — it is only "
                    "computed live at serialize time (Constitution III.11: never replayed "
                    f"as fabricated nulls). Replayable metrics: "
                    f"{sorted(MAP_HISTORY_REPLAYABLE_METRICS)}"
                ),
            }
        return {
            "metric": metric,
            "from_tick": from_tick or 0,
            "to_tick": to_tick or 0,
            "capped": False,
            "frames": [],
        }

    def get_explain(self, _session_id: UUID, metric: str, scope: str) -> dict[str, Any] | None:
        """GET .../explain/ mock (spec-113 Lane D).

        Mirrors ``game.provenance.METRIC_PROVENANCE``'s catalog of 9
        metric names and the real bridge's response shape, so frontend
        dev against the stub (no Postgres/engine) exercises the same
        InspectionStack FormulaCard code path. Unlike the real bridge
        this does not validate ``scope`` per metric (it is mock data —
        the same body regardless of which hex/org is asked about); the
        one honest check is metric membership, matching the real
        bridge's 404-on-unknown-metric behavior.

        Returns:
            The response body, or ``None`` for an unknown metric (the
            view turns that into a 404).
        """
        return _stub_explain_response(metric, scope)

    # ------------------------------------------------------------------ #
    # Domain Dashboards (Scaffolding for full UI requirements)
    # ------------------------------------------------------------------ #

    def get_game_summary(self, session_id: UUID) -> dict[str, Any]:
        session = _stub_sessions.get(session_id, {"tick": 0})
        tick = session.get("tick", 0)
        return {
            "tick": tick,
            "profit_rate": 0.08,
            "exploitation_rate": 0.45,
            "phi": 50.0,
            "hegemon": "institutionalist_bonapartist",
            "alerts": [
                {"id": "A1", "severity": "high", "message": "Evictions expected in Hamtramck"}
            ],
        }

    def get_game_timeseries(self, _session_id: UUID) -> dict[str, Any]:
        return {"data": []}

    def get_economy_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        return {}

    def get_communities_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        return {}

    def get_organizations_dashboard(
        self, _session_id: UUID, _player_only: bool = False
    ) -> dict[str, Any]:
        return {"organizations": []}

    def get_edges_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        return {}

    def get_state_apparatus_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        return {}

    def get_doctrine_tree(self, _session_id: UUID) -> dict[str, Any]:
        """Return the same static Doctrine Tree the real bridge serves.

        Unlike every stub dashboard above (which return an honest ``{}``
        because they'd otherwise need a real engine tick), the Doctrine
        Tree is static game-data, not session state — identical to how
        ``api.scenario_list`` serves ``SCENARIO_CATALOG`` regardless of
        which bridge is live. Calling the same loader here (rather than a
        hand-duplicated payload) keeps stub/real parity automatic as the
        11-node MVP corpus evolves.
        """
        from babylon.domain.doctrine import load_doctrine_tree, starting_tags

        tree = load_doctrine_tree()
        return {
            "root_id": tree.root_id,
            "nodes": [node.model_dump(mode="json") for node in tree.nodes.values()],
            "acquired_ids": [],
            "tags": {tag.value: value for tag, value in starting_tags().items()},
            "theoretical_labor": 0.0,
        }

    def get_journal_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        return {}

    def get_alerts_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        return {}

    # ------------------------------------------------------------------ #
    # Inspector Views
    # ------------------------------------------------------------------ #

    def get_inspector_node(self, _session_id: UUID, node_id: str) -> dict[str, Any]:
        return {"id": node_id, "type": "node", "details": "Stub details for node."}

    def get_inspector_org(self, _session_id: UUID, org_id: str) -> dict[str, Any]:
        return {
            "id": org_id,
            "name": "Wayne County Organizing Committee",
            "type": "Vanguard",
            "cadre_level": 0.10,
            "cohesion": 0.55,
            "funds": 100.0,
            "heat": 0.0,
            "territories": ["T001", "T002"],
        }

    def get_inspector_community(self, _session_id: UUID, hyperedge_id: str) -> dict[str, Any]:
        return {"id": hyperedge_id, "type": "community"}

    def get_inspector_edge(self, _session_id: UUID, edge_id: str) -> dict[str, Any]:
        return {"id": edge_id, "type": "edge"}

    def get_inspector_hex(self, _session_id: UUID, h3_index: str) -> dict[str, Any]:
        return {
            "h3_index": h3_index,
            "county_fips": "26163",
            "county_name": "Wayne County",
            "population": 45000,
            "profit_rate": 0.08,
            "heat": 0.1,
            "dominant_class": "proletariat",
        }

    def get_available_actions(self, _session_id: UUID) -> list[dict[str, Any]]:
        """Return available actions for current tick."""
        return [
            {
                "org_id": "ORG001",
                "verb": "educate",
                "action_type": "EDUCATE",
                "targets": ["C001", "C004"],
                "cost": 1.0,
            },
            {
                "org_id": "ORG001",
                "verb": "attack",
                "action_type": "ATTACK_INFRASTRUCTURE",
                "targets": ["C003"],
                "cost": 2.0,
            },
            {
                "org_id": "ORG001",
                "verb": "mobilize",
                "action_type": "PROTEST",
                "targets": ["T001", "T002"],
                "cost": 1.0,
            },
        ]

    def submit_action(
        self,
        session_id: UUID,
        tick: int,
        org_id: str,
        verb: str,
        target_id: str | None = None,
        params_json: dict[str, Any] | None = None,
    ) -> int:
        """Record a mock action submission. Returns a turn ID."""
        actions = _stub_actions.setdefault(session_id, [])
        turn_id = len(actions) + 1
        actions.append(
            {
                "turn_id": turn_id,
                "tick": tick,
                "org_id": org_id,
                "verb": verb,
                "target_id": target_id,
                "params": params_json,
            }
        )
        logger.info(
            "Stub: action submitted session=%s verb=%s turn_id=%d", session_id, verb, turn_id
        )
        return turn_id

    def preview_action(
        self,
        _session_id: UUID,
        _org_id: str,
        verb: str,
        _target_id: str | None = None,
    ) -> dict[str, Any]:
        """Return estimated effects of a proposed action."""
        # Vary estimates by verb category
        if verb in {"educate", "campaign"}:
            return {
                "estimated_consciousness_delta": 0.05,
                "estimated_heat_delta": 0.01,
                "action_point_cost": 1,
                "success_probability": 0.7,
                "affected_territory_ids": ["T001"],
                "warnings": [],
            }
        if verb in {"attack", "mobilize"}:
            return {
                "estimated_consciousness_delta": 0.02,
                "estimated_heat_delta": 0.15,
                "action_point_cost": 2,
                "success_probability": 0.4,
                "affected_territory_ids": ["T001", "T002"],
                "warnings": ["This action will increase heat significantly"],
            }
        # Default
        return {
            "estimated_consciousness_delta": 0.01,
            "estimated_heat_delta": 0.02,
            "action_point_cost": 1,
            "success_probability": 0.6,
            "affected_territory_ids": [],
            "warnings": [],
        }

    def resolve_tick(
        self,
        session_id: UUID,
    ) -> list[dict[str, Any]]:
        """Advance the game by one tick. Returns action results."""
        session = _stub_sessions.get(session_id)
        if session:
            session["tick"] += 1
            # Sync Django model row
            try:
                from game.models import GameSession

                GameSession.objects.filter(id=session_id).update(
                    current_tick=session["tick"],
                )
            except Exception:
                pass

        actions = _stub_actions.get(session_id, [])
        results = []
        for action in actions:
            results.append(
                {
                    "org_id": action["org_id"],
                    "action_type": action["verb"].upper(),
                    "target_id": action.get("target_id"),
                    "initiative_score": round(random.uniform(0.3, 0.9), 2),
                    "action_cost": 1.0,
                    "success": random.random() > 0.3,
                    "consciousness_delta": round(random.uniform(-0.02, 0.08), 3),
                    "heat_delta": round(random.uniform(0.0, 0.1), 3),
                    "details": {},
                }
            )

        _stub_actions[session_id] = []
        return results

    # ------------------------------------------------------------------ #
    # Spec 103: Trade surfaces — stub returns honest empty states.
    # ------------------------------------------------------------------ #

    def get_field_state(self, session_id: UUID) -> dict[str, Any]:
        """Program 19/20 (Wave 3 Round 1): honest empty-but-well-formed stub.

        The hypergraph/communities cautionary tale (a real bridge method the
        stub never implemented -> guaranteed 500) does not repeat here: the
        stub carries no engine, so it has no field stack to report — nulls
        and empty lists, never fabricated field/gradient values.
        """
        session = _stub_sessions.get(session_id, {"tick": 0})
        tick = session.get("tick", 0)
        return {
            "tick": tick,
            "nodes": [],
            "edges": [],
            "principal_field": None,
            "dialectical_regime": None,
        }

    # ------------------------------------------------------------------ #
    # AW4-R1 (audit Wave 4): Spatial Multi-Scale — stub returns honest
    # empty states (same pattern as get_field_state above).
    # ------------------------------------------------------------------ #

    def get_org_network(
        self,
        session_id: UUID,
        *,
        territory_filter: str | None = None,  # noqa: ARG002 — stub has no graph
    ) -> dict[str, Any]:
        """Honest empty-but-well-formed stub (AW4-R1 Deliverable 1).

        The stub carries no engine, so it has no org-network graph to
        report — empty lists/dicts and a null percolation ratio, never
        fabricated nodes/edges/centrality. ``territory_filter`` is
        accepted for signature parity with the real bridge (the view
        forwards it unconditionally) but has no effect here.
        """
        session = _stub_sessions.get(session_id, {"tick": 0})
        tick = session.get("tick", 0)
        return {
            "tick": tick,
            "nodes": [],
            "edges": [],
            "centrality": {},
            "percolation_ratio": None,
        }

    def get_hypergraph_communities(
        self,
        session_id: UUID,
        *,
        territory_filter: str | None = None,  # noqa: ARG002 — stub has no graph
    ) -> dict[str, Any]:
        """Honest empty-but-well-formed stub (AW4-R1 Deliverable 2).

        Closes the exact gap :meth:`get_field_state`'s docstring above
        calls out by name as a cautionary tale: before AW4-R1 neither
        bridge implemented ``get_hypergraph_communities`` at all, so the
        real ``GET .../hypergraph/communities/`` route 500'd
        unconditionally. Field name is ``hyperedges`` (``HypergraphPayload``,
        ``src/frontend/src/types/game.ts`` ~648-651), not ``communities``.
        """
        session = _stub_sessions.get(session_id, {"tick": 0})
        tick = session.get("tick", 0)
        return {"tick": tick, "hyperedges": []}

    def get_trade_flows(self, _session_id: UUID) -> dict[str, Any]:
        """Stub: no boundary_flow_register in stub mode → has_data: False."""
        return {"tick": 0, "has_data": False, "blocs": []}

    def get_county_import_exposure(self, _session_id: UUID, county_fips: str) -> dict[str, Any]:
        """Stub: no exposure data in stub mode → has_data: False."""
        return {
            "county_fips": county_fips,
            "has_data": False,
            "total_exposure": 0.0,
            "breakdown": {"total": 0.0, "contributors": []},
            "citations": [],
        }

    def get_trade_panel(self, _session_id: UUID) -> dict[str, Any]:
        """Stub: no boundary_flow_register in stub mode → has_data: False."""
        return {
            "tick": 0,
            "has_data": False,
            "total_phi_inflow": 0.0,
            "total_trade": 0.0,
            "blocs": [],
            "flow_types": [],
        }

    # ------------------------------------------------------------------ #
    # Spec 111 C2 / audit Wave 4 straggler (task #76): per-tick history
    # endpoints. The real bridge sources these from ``org_snapshot``/
    # ``territory_snapshot``/``class_snapshot``/``edge_snapshot`` via the
    # persistence layer's OPTIONAL ``query_*_history`` capability — a
    # SQLite-backed ``RuntimeDatabase`` (dev/test, no such tables) already
    # degrades to an empty list there. The stub persists nothing at all, so
    # the same honest-empty shape is exactly right here too (Constitution
    # III.11: never a fabricated history).
    # ------------------------------------------------------------------ #

    def get_org_history(self, _session_id: UUID, org_id: str) -> dict[str, Any]:
        return {"org_id": org_id, "history": []}

    def get_territory_history(self, _session_id: UUID, county_fips: str) -> dict[str, Any]:
        return {"county_fips": county_fips, "history": []}

    def get_class_history(self, _session_id: UUID, node_id: str) -> dict[str, Any]:
        return {"class_id": node_id, "history": [], "ruptures": []}

    def get_edge_history(self, _session_id: UUID, edge_id: str) -> dict[str, Any]:
        return {"edge_id": edge_id, "history": []}

    def get_economy(self, session_id: UUID, territory_id: str | None = None) -> dict[str, Any]:
        """Spec 093 US5. No ``territory_id`` delegates to the (honest-empty)
        economy dashboard, matching the real bridge's backward-compatible
        fallback. A given ``territory_id`` gets an honest empty payload: the
        stub's mock territories carry ``host_id``/``occupant_id``, not the
        ``territory_ids`` back-reference the real aggregation reads off
        social_class/organization nodes, so there is nothing to honestly sum.
        """
        if territory_id is None:
            return self.get_economy_dashboard(session_id)
        return {
            "territory_id": territory_id,
            "has_data": False,
            "value_produced": 0.0,
            "wage_share": None,
            "rent_extracted": 0.0,
            "exploitation_rate": None,
            "extraction_intensity": 0.0,
        }

    # ------------------------------------------------------------------ #
    # Spec 111 C2: infrastructure network overlay.
    # ------------------------------------------------------------------ #

    def get_infrastructure(self, session_id: UUID) -> dict[str, Any]:
        """Honest empty ``InfrastructurePayload``.

        Matches the real bridge's OWN current behavior, not just a stub
        degradation: Amendment O's corridor build/degrade write path is
        ``[RATIFIED · PENDING CODE]``, so every real session legitimately
        gets ``edges: []`` too (see ``EngineBridge.get_infrastructure``'s
        docstring) — this is one of the rare cases where stub and real
        bridge are byte-identical by construction.
        """
        session = _stub_sessions.get(session_id, {"tick": 0})
        return {"tick": session.get("tick", 0), "nodes": [], "edges": []}

    # ------------------------------------------------------------------ #
    # Spec 094: The Wire feed.
    # ------------------------------------------------------------------ #

    def get_wire_feed(self, session_id: UUID) -> dict[str, Any]:
        """Run the same :class:`~game.narrator.DeterministicNarrator` the
        real bridge uses over the stub's (always-empty) mock journal.

        Deliberately skips the optional spec-111 ``NarrativeService``
        augmentation layer: it is engine-adjacent (imports ``babylon.*``,
        per its own module docstring) and gated behind
        ``BABYLON_LLM_NARRATOR`` (default OFF); at that default the real
        bridge's ``augment_feed`` is a no-op anyway, so skipping it keeps
        this method byte-identical to the real bridge in the common
        (flag-off) case while preserving ``game.narrator``'s
        zero-``babylon.*``-import guarantee for this module too.
        """
        journal = self.get_journal_dashboard(session_id)
        events = journal.get("events", [])
        session = _stub_sessions.get(session_id, {"tick": 0})
        tick = session.get("tick", 0)
        meta = {
            "tick": tick,
            "session": str(session_id),
            "operator": "RASKOVA-2",
            "freq": "88.7 MHz",
            "qth": "WAYNE CO / GRID EN82",
            "classification": "TS//SI//NOFORN",
            "cable_id": f"{tick:04d}-A",
            "page_of": "001/001",
            "timestamp_utc": "2026-05-12T08:47:22Z",
            "class_names": {e["id"]: e["name"] for e in _make_wayne_county_entities()},
            "org_names": {o["id"]: o["name"] for o in _make_organizations()},
        }

        from .narrator import DeterministicNarrator

        return DeterministicNarrator().narrate(events, meta)

    # ------------------------------------------------------------------ #
    # Spec 095: Endgame Chronicle + Journal + Dialectic screen. No stub
    # session ever runs ContradictionFieldSystem or reaches a terminal
    # outcome (no engine, no endgame persistence) — every value below is
    # either honestly empty/None or a real average over the stub's own
    # mock entities/territories/organizations (never invented).
    # ------------------------------------------------------------------ #

    def get_contradiction_snapshot(self, session_id: UUID) -> dict[str, Any]:
        session = _stub_sessions.get(session_id, {"tick": 0})
        return {
            "tick": session.get("tick", 0),
            "regime": "reproduction",
            "oppositions": [],
            "principal_key": "",
            "frame": {"principal": {}, "secondary": {}},
        }

    def get_endgame_state(self, session_id: UUID) -> dict[str, Any]:
        session = _stub_sessions.get(session_id, {"tick": 0})
        tick = session.get("tick", 0)
        return {
            "tick": tick,
            "outcome": None,
            "headline": "",
            "summary": "",
            "stats": {
                "final_tick": tick,
                "consciousness": _stub_avg_attr("consciousness"),
                "solidarity_edges": 0,
                "heat": _stub_avg_attr("heat"),
            },
        }

    def get_journal_objectives(self, session_id: UUID) -> dict[str, Any]:
        session = _stub_sessions.get(session_id, {"tick": 0})
        tick = session.get("tick", 0)
        consciousness_avg = _stub_avg_attr("consciousness")
        heat_avg = _stub_avg_attr("heat")
        principal_gap = 0.0  # No ContradictionFieldSystem has ever run here.

        objectives = [
            {
                "id": "revolution",
                "title": "Revolutionary Victory",
                "description": (
                    "Build mass class consciousness and solidarity edges to overthrow the empire."
                ),
                "progress": min(1.0, consciousness_avg),
                "status": "active",
                "category": "revolution",
            },
            {
                "id": "ecological_collapse",
                "title": "Ecological Collapse",
                "description": "Biocapacity depletion forces a terminal retreat from extraction.",
                "progress": min(1.0, heat_avg),
                "status": "active",
                "category": "collapse",
            },
            {
                "id": "fascist_consolidation",
                "title": "Fascist Consolidation",
                "description": "False-consciousness bloc achieves a sovereign grip on the state.",
                "progress": min(1.0, principal_gap),
                "status": "active",
                "category": "fascist",
            },
            {
                "id": "red_ogv",
                "title": "Red OGV Trap",
                "description": (
                    "Settler-socialist formation captures the movement without abolishing empire."
                ),
                "progress": min(1.0, principal_gap * 0.5),
                "status": "active",
                "category": "red_ogv",
            },
            {
                "id": "fragmented_collapse",
                "title": "Fragmented Collapse",
                "description": "Balkanization — sovereign fragmentation outpaces solidarity.",
                "progress": min(1.0, heat_avg * 0.5),
                "status": "active",
                "category": "fragmented",
            },
        ]
        return {"tick": tick, "objectives": objectives}

    # ------------------------------------------------------------------ #
    # Org status + pending actions — internal-helper-style methods in the
    # real bridge (called by the verb-target methods below), implemented
    # here for the same reason.
    # ------------------------------------------------------------------ #

    def get_pending_actions(self, session_id: UUID, tick: int) -> list[dict[str, Any]]:
        """Unresolved mock action queue for ``tick`` (mirrors the real
        bridge's ``game_turn`` row shape — ``PendingAction``'s required
        fields — via the stub's own ``_stub_actions`` queue)."""
        return [
            {
                "id": action["turn_id"],
                "org_id": action["org_id"],
                "verb": action["verb"],
                "target_id": action.get("target_id"),
                "tick": action["tick"],
            }
            for action in _stub_actions.get(session_id, [])
            if action["tick"] == tick
        ]

    def get_org_status(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Mock org status + OODA cycle info. Only ``ORG001`` (the stub's one
        mock organization) resolves; any other id gets the same honest
        ``{}`` the real bridge returns for an org absent from the graph.
        """
        org_data = _stub_org_by_id(org_id)
        if org_data is None:
            return {}

        cadre = float(org_data.get("cadre_level", 0.0))
        cohesion = float(org_data.get("cohesion", 0.0))
        budget = float(org_data.get("budget", 0.0))
        heat = float(org_data.get("heat", 0.0))
        territory_ids = org_data.get("territory_ids", [])

        resources = _stub_vanguard_resources(
            cadre_level=cadre,
            cohesion=cohesion,
            budget=budget,
            heat=heat,
            territory_count=len(territory_ids),
        )

        session = _stub_sessions.get(session_id, {"tick": 0})
        tick = session.get("tick", 0)
        pending = self.get_pending_actions(session_id, tick)
        ap_max = 3
        ap_used = len([a for a in pending if a.get("org_id") == org_id])
        ap_remaining = max(0, ap_max - ap_used)

        return {
            "id": org_id,
            "name": org_data.get("name", org_id),
            "type": str(org_data.get("org_type", "PoliticalFaction")),
            "consciousness_strategy": str(org_data.get("consciousness_strategy", "revolutionary")),
            "resources": {
                "cadre_labor": resources["cadre_labor"],
                "sympathizer_labor": resources["sympathizer_labor"],
                "material": resources["budget"],
            },
            "ooda": {
                "action_points_remaining": ap_remaining,
                "action_points_max": ap_max,
                "cycle_time": 2,
            },
            "cadre_level": cadre,
            "cohesion": cohesion,
        }

    # ------------------------------------------------------------------ #
    # Verb-target methods (specs 043/045-050). Each mirrors its verb's own
    # response shape (they are NOT identical — educate/aid/mobilize/attack/
    # reproduce/investigate/move/negotiate each nest ``targets`` differently
    # in the real bridge, so no shared helper is faithful here). Dynamic
    # parts reuse the stub's coherent mock world (ORG001, T001-T004,
    # C001-C004, INST001); parts that are STATIC placeholders in the real
    # bridge too (not derived from any graph — negotiate's targets/
    # de_escalation_targets, investigate's targeted_scans/
    # counter_intelligence/observe_capability) are copied verbatim for
    # byte-for-byte parity.
    # ------------------------------------------------------------------ #

    def get_educate_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}
        session = _stub_sessions.get(session_id, {"tick": 0})
        cadre_labor = org_status["resources"]["cadre_labor"]

        def _target(
            community_id: str,
            territory_id: str,
            territory_name: str,
            agitation: float,
        ) -> dict[str, Any]:
            return {
                "community_id": community_id,
                "community_type": "PROLETARIAT",
                "category": "social_class",
                "territory_name": territory_name,
                "territory_id": territory_id,
                "credibility": org_status["cohesion"],
                "credibility_explanation": (
                    f"{int(org_status['cohesion'] * 100)}% org cohesion (mock — the "
                    "stub has no per-community overlap metric)"
                ),
                "consciousness": {
                    "r": 0.0,
                    "l": 0.0,
                    "f": 0.0,
                    "dominant_tendency": "unknown",
                    "collective_identity": None,
                    "ideological_contestation": None,
                    "note": (
                        "TernaryConsciousness lives on XGI hypergraph communities, "
                        "not modeled by the stub."
                    ),
                },
                "material_readiness": {
                    "avg_agitation": agitation,
                    "readiness_score": min(1.0, agitation / 0.5) if agitation else 0.0,
                    "readiness_explanation": (
                        "Mock — matches this class's agitation in _make_wayne_county_entities()."
                    ),
                },
                "education_pressure": {
                    "current": 0.0,
                    "projected_delta": None,
                    "projected_new": None,
                    "decay_per_tick": None,
                    "note": (
                        "education_pressure lives on XGI community hyperedges, "
                        "not modeled by the stub."
                    ),
                },
                "feedforward": {"note": "No per-tick routing-shift projection exists in the stub."},
            }

        return {
            "status": "ok",
            "tick": session.get("tick", 0),
            "verb": "educate",
            "acting_org": org_status,
            "cost": {
                "action_points": 1,
                "cadre_labor": 3.0,
                "sympathizer_labor": 0.0,
                "material": 0.0,
                "can_afford": cadre_labor >= 3.0,
                "over_budget": False,
                "over_budget_penalty": None,
            },
            "targets": [
                _target("C001", "T001", "Downtown Detroit", 0.2),
                _target("C004", "T002", "Dearborn", 0.15),
            ],
            "unavailable_communities": [],
        }

    def get_aid_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}
        session = _stub_sessions.get(session_id, {"tick": 0})
        cadre_labor = org_status["resources"]["cadre_labor"]
        no_edge = {"type": "NONE", "value_flow": 0.0, "tension": 0.0}

        return {
            "status": "ok",
            "tick": session.get("tick", 0),
            "verb": "aid",
            "acting_org": org_status,
            "cost": {
                "action_points": 1,
                "cadre_labor": 1.0,
                "sympathizer_labor": 1.0,
                "material": 0.0,
                "can_afford": cadre_labor >= 1.0,
                "over_budget": False,
                "over_budget_penalty": None,
            },
            "population_targets": [
                {
                    "community_id": "C001",
                    "community_name": "Detroit Proletariat",
                    "population": 350000,
                    "class_name": "PROLETARIAT",
                    "material_conditions": {
                        "v_value_produced": 15.0,
                        "wage_received": None,
                        "consumption_gap": None,
                        "subsistence_level": 10.0,
                        "agitation_level": 0.2,
                    },
                    "edge_status": no_edge,
                    "feedforward": {
                        "note": "No per-tick aid-effect projection exists in the stub."
                    },
                },
                {
                    "community_id": "C004",
                    "community_name": "Downriver Workers",
                    "population": 120000,
                    "class_name": "PROLETARIAT",
                    "material_conditions": {
                        "v_value_produced": 20.0,
                        "wage_received": None,
                        "consumption_gap": None,
                        "subsistence_level": 12.0,
                        "agitation_level": 0.15,
                    },
                    "edge_status": no_edge,
                    "feedforward": {
                        "note": "No per-tick aid-effect projection exists in the stub."
                    },
                },
            ],
            "org_targets": [],
            "unavailable_targets": [],
        }

    def get_mobilize_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """The stub's mock world has exactly one organization (ORG001, the
        acting org itself) — real MOBILIZE targets are OTHER business/
        civil_society orgs sharing a territory, so an honest empty list
        beats fabricating a rival org that exists nowhere else in this
        file's mock world."""
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        return {
            "entity_id": org_id,
            "name": org_status.get("name", "Unknown Org"),
            "available_sl": org_status["resources"]["sympathizer_labor"],
            "available_cl": org_status["resources"]["cadre_labor"],
            # GameDefines().mobilize.mobilize_cl_cost, src/babylon/data/
            # defines.yaml:56 — a literal snapshot, not a live read: this
            # module cannot import babylon.config.defines (import-boundary
            # guard, tests/unit/web/test_import_boundary.py).
            "mobilize_cost_cl": 0.2,
            "targets": [],
        }

    def get_attack_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}
        session = _stub_sessions.get(session_id, {"tick": 0})
        resources = org_status["resources"]

        return {
            "status": "ok",
            "tick": session.get("tick", 0),
            "verb": "attack",
            "acting_org": org_status,
            "cost": {
                "action_points": 3,
                "cadre_labor_if_targeted": 2.5,
                "sympathizer_labor_if_mass": 25.0,
                "material": 100.0,
                "can_afford_targeted": resources["cadre_labor"] >= 2.5,
                "can_afford_mass": resources["sympathizer_labor"] >= 25.0,
                "over_budget_ap": False,
                "cost_explanation": (
                    "TARGETED attacks use dense cadre formations. MASS actions use "
                    "diffused sympathizer labor. Both require AP and initial materials."
                ),
            },
            "ultra_left_warning": {
                "active": False,
                "trap_score": 0.0,
                "indicators": [],
                "explanation": "No trap detection has run yet this session (requires a resolved tick).",
            },
            # C001/C004 are ORG001's mock territories' occupants (T001/T002);
            # 0.72 is the real min of their two p_acquiescence values.
            "warsaw_ghetto_flag": {
                "active": False,
                "population_p_acquiescence": 0.72,
                "threshold": 0.05,
                "explanation": (
                    "If survival probabilities reach near absolute zero, mass base "
                    "will endorse desperate measures regardless of military feasibility."
                ),
            },
            "targets": {
                "organizations": [],
                "edges": [],
                "institutions": [
                    {
                        "target_id": "INST001",
                        "target_type": "INSTITUTION",
                        "name": "Wayne County DPD",
                        "factional_control": {
                            "liberal_technocratic": 0.2,
                            "revanchist_fascist": 0.3,
                            "institutionalist_bonapartist": 0.5,
                        },
                    }
                ],
            },
            "unavailable_targets": [],
        }

    def get_reproduce_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}
        session = _stub_sessions.get(session_id, {"tick": 0})
        resources = org_status["resources"]
        # C001 (T001, pop 350000) + C004 (T002, pop 120000) — ORG001's real
        # mock territories' occupant populations.
        base_population = 350_000 + 120_000

        return {
            "status": "ok",
            "tick": session.get("tick", 0),
            "verb": "reproduce",
            "acting_org": org_status,
            "cost": {
                "action_points": 1,
                "cadre_labor": 0.0,
                "sympathizer_labor": 10.0,
                "material": 0.0,
                "can_afford": resources["sympathizer_labor"] >= 10.0,
                "over_budget": False,
                "over_budget_penalty": None,
            },
            "targets": [
                {
                    "target_id": org_id,
                    "name": org_status.get("name", org_id),
                    "type": "ORGANIZATION",
                    "modes": {
                        "cadre_training": {
                            "resource_cost": {"sympathizer_labor": 10.0},
                            "projected_effect": {
                                "cadre_delta": 1.0,
                                "cohesion_delta": 0.02,
                                "agitation_delta": 0.0,
                            },
                            "recruitment_pool": {
                                "sympathizers": int(resources["sympathizer_labor"])
                            },
                            "cooldown_applied": 0,
                            "explanation": (
                                "Converts 10 sympathizer labor into 1 cadre labor, "
                                "increasing cohesion."
                            ),
                        },
                        "mass_recruitment": {
                            "resource_cost": {"cadre_labor": 2.0},
                            "projected_effect": {
                                "cadre_delta": 0.0,
                                "cohesion_delta": -0.05,
                                "agitation_delta": 0.1,
                            },
                            "recruitment_pool": {"base_population": base_population},
                            "cooldown_applied": 1,
                            "explanation": (
                                "Spends cadre labor to prospect among the agitated "
                                "base. Dilutes cohesion but gains sympathizers."
                            ),
                        },
                    },
                    "state_response": {"state_visibility": "LOW", "attention_diverted": 0.0},
                }
            ],
        }

    def get_investigate_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}
        session = _stub_sessions.get(session_id, {"tick": 0})
        resources = org_status["resources"]

        def _territory_scan(target_id: str, name: str, heat: float) -> dict[str, Any]:
            return {
                "target_id": target_id,
                "name": name,
                "target_type": "TERRITORY",
                "heat": heat,
                "current_knowledge": {
                    "visibility_level": "SURFACE",
                    "known_attributes": ["population"],
                    "last_scanned_tick": None,
                },
                "resource_cost": {"sympathizer_labor": 5.0},
                "projected_reveals": {
                    "new_visibility_level": "TARGETED",
                    "likely_reveals": ["material_readiness", "hidden_factions", "state_deployment"],
                },
            }

        return {
            "status": "ok",
            "tick": session.get("tick", 0),
            "verb": "investigate",
            "acting_org": org_status,
            "cost": {
                "action_points": 1,
                "cadre_labor": 2.0,
                "sympathizer_labor": 0.0,
                "material": 0.0,
                "can_afford": resources["cadre_labor"] >= 2.0,
                "over_budget": False,
                "over_budget_penalty": None,
            },
            # observe_capability + targeted_scans + counter_intelligence are
            # STATIC placeholders in the real bridge too (not graph-derived)
            # — copied verbatim for byte-for-byte parity.
            "observe_capability": {"intel_network_strength": 0.6, "max_scan_depth": "TARGETED"},
            "targets": {
                "territory_scans": [
                    _territory_scan("T001", "Downtown Detroit", 0.45),
                    _territory_scan("T002", "Dearborn", 0.20),
                ],
                "targeted_scans": [
                    {
                        "target_id": "org-police-union",
                        "name": "Fraternal Order of Police",
                        "target_type": "INSTITUTION",
                        "current_knowledge": {
                            "visibility_level": "NONE",
                            "known_attributes": [],
                            "last_scanned_tick": None,
                        },
                        "resource_cost": {"cadre_labor": 4.0},
                        "projected_reveals": {
                            "new_visibility_level": "SURFACE",
                            "likely_reveals": ["factional_control", "defensive_capacity"],
                        },
                        "detection_risk": {
                            "probability": 0.35,
                            "consequence": "Increases organization heat by 0.15",
                        },
                    }
                ],
                "counter_intelligence": {
                    "active_moles_suspected": 1,
                    "resource_cost": {"cadre_labor": 5.0},
                    "projected_reveals": {
                        "new_visibility_level": "INTERNAL_AUDIT",
                        "likely_reveals": ["mole_identities", "leaked_information_vectors"],
                    },
                },
            },
        }

    def get_move_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}
        session = _stub_sessions.get(session_id, {"tick": 0})
        resources = org_status["resources"]

        return {
            "status": "ok",
            "tick": session.get("tick", 0),
            "verb": "move",
            "acting_org": org_status,
            "cost": {
                "action_points": 1,
                "cadre_labor": 10.0,
                "sympathizer_labor": 0.0,
                "material": 0.0,
                "can_afford": resources["cadre_labor"] >= 10.0,
                "over_budget": False,
                "over_budget_penalty": None,
            },
            "current_territories": ["T001", "T002"],
            # T003 (Downriver) — one of the stub's mock territories ORG001
            # does not yet occupy, per _make_territories().
            "targets": [
                {
                    "id": "T003",
                    "name": "Downriver",
                    "community_reception": {"overlap_score": 0.45, "cross_community_penalty": 0.1},
                    "strategic_assessment": {
                        "value_circuit_position": {"type": "logistics_hub", "s_v_ratio": 1.2},
                        "surveillance_evasion": 0.65,
                    },
                    "projected_outcomes": {
                        "expand": {
                            "presence_value": 0.5,
                            "edges_at_risk": 2,
                            "ticks_to_operational": 3,
                        },
                        "relocate": {
                            "presence_value": 1.0,
                            "edges_at_risk": 5,
                            "ticks_to_operational": 1,
                        },
                    },
                }
            ],
        }

    def get_negotiate_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """The real bridge's ``targets``/``de_escalation_targets`` are STATIC
        placeholders (not graph-derived — negotiate mechanics aren't wired to
        the graph yet), so this copies the identical content verbatim for
        byte-for-byte parity."""
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}
        session = _stub_sessions.get(session_id, {"tick": 0})

        return {
            "status": "ok",
            "tick": session.get("tick", 0),
            "verb": "negotiate",
            "acting_org": org_status,
            "cost": {
                "action_points": 1,
                "cadre_labor": 0.0,
                "sympathizer_labor": 0.0,
                "material": 0.0,
                "can_afford": True,
                "over_budget": False,
                "over_budget_penalty": None,
            },
            "org_leverage": 0.8,
            "targets": [
                {
                    "id": "org-auto-union",
                    "name": "Auto Workers Union",
                    "type": "ORGANIZATION",
                    "interest_alignment": {
                        "score": 0.75,
                        "shared_interests": ["wage_increases", "safety"],
                        "divergent_interests": ["systemic_change"],
                        "alliance_type": "tactical",
                    },
                    "negotiation_options": [
                        {
                            "proposal": "coordination_pact",
                            "success_probability": 0.65,
                            "edge_effect": "TRANSACTIONAL edge created",
                            "state_response_prediction": "State may attempt CO-OPT:DIVIDE",
                            "betrayal_risk": 0.3,
                        }
                    ],
                    "betrayal_risk": 0.3,
                    "existing_edge_state": None,
                }
            ],
            "de_escalation_targets": [
                {
                    "target_id": "org-rival-faction",
                    "name": "Rival Revolutionary Faction",
                    "antagonism_cause": "ideological_divergence",
                    "reconciliation_requirement": "joint_action_against_state",
                }
            ],
        }
