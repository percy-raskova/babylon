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
                },
            }
        )

    return features


class StubEngineBridge:
    """Mock bridge that returns correctly-shaped data without engine deps.

    All methods match the ``EngineBridge`` interface so they can be used
    interchangeably in ``game.api._bridge_instance``.
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
                ],
            },
            "features": features,
        }

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

    def get_organizations_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        return {}

    def get_edges_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        return {}

    def get_state_apparatus_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        return {}

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
