"""MockEngineBridge — deterministic mock for full-stack end-to-end testing.

Implements the same interface as ``StubEngineBridge`` but persists state in
``GameSession.snapshot_json`` and advances it deterministically.  Every tick
produces identical output for identical input — no RNG.

This bridge lights up **all** Spec 042 UI components:
- DeckGLMap (H3 hexagons with real Wayne/Oakland/Macomb indexes)
- GraphView (entities + orgs + institutions + edges → Sigma.js topology)
- TimeSeries (tick summaries from TickSummary extraction)
- Inspector (full EntityState / TerritoryState / OrgState / InstitutionState)
- TopBar indicators (imperial_rent, avg_consciousness, etc.)
- ResourcePanel (vanguard economy on player org)
- TrapIndicator (TrapDetectionResult)
- ActionComposer (available verbs)
- EventLog (per-tick events)

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
# Entities — social classes
# --------------------------------------------------------------------------- #
_MOCK_ENTITIES: list[dict[str, Any]] = [
    {
        "id": "ent-proletariat",
        "name": "Industrial Proletariat",
        "role": "PROLETARIAT",
        "wealth": 15.0,
        "consciousness": 0.25,
        "national_identity": 0.3,
        "agitation": 0.2,
        "organization": 0.15,
        "repression": 0.4,
        "p_acquiescence": 0.75,
        "p_revolution": 0.10,
        "subsistence": 12.0,
        "population": 850000,
        "inequality": 0.65,
        "active": True,
    },
    {
        "id": "ent-petit-bourg",
        "name": "Petite Bourgeoisie",
        "role": "PETITE_BOURGEOISIE",
        "wealth": 45.0,
        "consciousness": 0.15,
        "national_identity": 0.5,
        "agitation": 0.08,
        "organization": 0.25,
        "repression": 0.15,
        "p_acquiescence": 0.88,
        "p_revolution": 0.03,
        "subsistence": 20.0,
        "population": 320000,
        "inequality": 0.40,
        "active": True,
    },
    {
        "id": "ent-bourgeoisie",
        "name": "Finance Bourgeoisie",
        "role": "BOURGEOISIE",
        "wealth": 250.0,
        "consciousness": 0.05,
        "national_identity": 0.7,
        "agitation": 0.02,
        "organization": 0.60,
        "repression": 0.05,
        "p_acquiescence": 0.95,
        "p_revolution": 0.01,
        "subsistence": 50.0,
        "population": 45000,
        "inequality": 0.10,
        "active": True,
    },
    {
        "id": "ent-lumpen",
        "name": "Lumpenproletariat",
        "role": "LUMPENPROLETARIAT",
        "wealth": 3.0,
        "consciousness": 0.10,
        "national_identity": 0.2,
        "agitation": 0.30,
        "organization": 0.05,
        "repression": 0.70,
        "p_acquiescence": 0.60,
        "p_revolution": 0.15,
        "subsistence": 8.0,
        "population": 120000,
        "inequality": 0.85,
        "active": True,
    },
    {
        "id": "ent-labor-arist",
        "name": "Labor Aristocracy",
        "role": "LABOR_ARISTOCRACY",
        "wealth": 80.0,
        "consciousness": 0.08,
        "national_identity": 0.6,
        "agitation": 0.05,
        "organization": 0.40,
        "repression": 0.10,
        "p_acquiescence": 0.90,
        "p_revolution": 0.02,
        "subsistence": 30.0,
        "population": 210000,
        "inequality": 0.30,
        "active": True,
    },
]

# --------------------------------------------------------------------------- #
# Organizations
# --------------------------------------------------------------------------- #
_MOCK_ORGS: list[dict[str, Any]] = [
    {
        "id": "org-peoples-front",
        "name": "People's United Front",
        "org_type": "civil_society",
        "class_character": "proletarian",
        "cohesion": 0.60,
        "cadre_level": 0.35,
        "budget": 12.0,
        "heat": 0.20,
        "territory_ids": ["terr-wayne-01", "terr-wayne-03"],
        "consciousness_tendency": "REVOLUTIONARY",
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
        "consciousness_tendency": "LIBERAL",
        "vanguard": None,
    },
    {
        "id": "org-auto-union",
        "name": "Auto Workers Union",
        "org_type": "civil_society",
        "class_character": "proletarian",
        "cohesion": 0.50,
        "cadre_level": 0.25,
        "budget": 8.0,
        "heat": 0.10,
        "territory_ids": ["terr-wayne-05", "terr-macomb-01"],
        "consciousness_tendency": "LIBERAL",
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
        "org_type": "paramilitary",
        "class_character": "settler",
        "cohesion": 0.70,
        "cadre_level": 0.40,
        "budget": 15.0,
        "heat": 0.30,
        "territory_ids": ["terr-macomb-02", "terr-oakland-02"],
        "consciousness_tendency": "FASCIST",
        "vanguard": None,
    },
]

# --------------------------------------------------------------------------- #
# Institutions
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
        "hegemonic_fraction": "finance_capital",
        "liberal_technocratic": 0.45,
        "revanchist_fascist": 0.25,
        "institutionalist_bonapartist": 0.30,
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
        "hegemonic_fraction": "security_state",
        "liberal_technocratic": 0.15,
        "revanchist_fascist": 0.60,
        "institutionalist_bonapartist": 0.25,
    },
]

# --------------------------------------------------------------------------- #
# Edges — relationships between entities/orgs/territories
# --------------------------------------------------------------------------- #
_MOCK_EDGES: list[dict[str, Any]] = [
    {
        "source_id": "ent-bourgeoisie",
        "target_id": "ent-proletariat",
        "edge_type": "EXPLOITATION",
        "value_flow": 25.0,
        "tension": 0.65,
        "solidarity_strength": 0.0,
    },
    {
        "source_id": "ent-bourgeoisie",
        "target_id": "ent-petit-bourg",
        "edge_type": "EXPLOITATION",
        "value_flow": 10.0,
        "tension": 0.30,
        "solidarity_strength": 0.0,
    },
    {
        "source_id": "ent-bourgeoisie",
        "target_id": "ent-labor-arist",
        "edge_type": "WAGES",
        "value_flow": 18.0,
        "tension": 0.15,
        "solidarity_strength": 0.0,
    },
    {
        "source_id": "ent-proletariat",
        "target_id": "ent-lumpen",
        "edge_type": "SOLIDARITY",
        "value_flow": 2.0,
        "tension": 0.10,
        "solidarity_strength": 0.45,
    },
    {
        "source_id": "org-peoples-front",
        "target_id": "ent-proletariat",
        "edge_type": "SOLIDARITY",
        "value_flow": 3.0,
        "tension": 0.05,
        "solidarity_strength": 0.60,
    },
    {
        "source_id": "org-auto-union",
        "target_id": "ent-labor-arist",
        "edge_type": "SOLIDARITY",
        "value_flow": 4.0,
        "tension": 0.08,
        "solidarity_strength": 0.50,
    },
    {
        "source_id": "org-state-apparatus",
        "target_id": "ent-proletariat",
        "edge_type": "TRIBUTE",
        "value_flow": 8.0,
        "tension": 0.55,
        "solidarity_strength": 0.0,
    },
    {
        "source_id": "terr-wayne-01",
        "target_id": "terr-wayne-02",
        "edge_type": "ADJACENCY",
        "value_flow": 0.0,
        "tension": 0.0,
        "solidarity_strength": 0.0,
    },
    {
        "source_id": "terr-wayne-02",
        "target_id": "terr-wayne-03",
        "edge_type": "ADJACENCY",
        "value_flow": 0.0,
        "tension": 0.0,
        "solidarity_strength": 0.0,
    },
    {
        "source_id": "terr-oakland-01",
        "target_id": "terr-oakland-02",
        "edge_type": "ADJACENCY",
        "value_flow": 0.0,
        "tension": 0.0,
        "solidarity_strength": 0.0,
    },
    {
        "source_id": "inst-city-hall",
        "target_id": "ent-bourgeoisie",
        "edge_type": "HOUSES",
        "value_flow": 5.0,
        "tension": 0.20,
        "solidarity_strength": 0.0,
    },
]

_MOCK_ECONOMY: dict[str, Any] = {
    "imperial_rent": 15.5,
    "total_surplus": 42.0,
    "gdp": 180.0,
    "gini": 0.62,
    "profit_rate": 0.18,
    "exploitation_rate": 0.55,
    "wage_share": 0.38,
}

_MOCK_TRAPS: dict[str, Any] = {
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
        "score": 0.05,
        "indicators": [],
        "ticks_at_moderate": 0,
    },
    "rightist": {
        "trap_type": "rightist",
        "severity": "none",
        "score": 0.08,
        "indicators": [],
        "ticks_at_moderate": 0,
    },
    "active_trap": None,
    "game_over_trap": None,
}


def _build_initial_snapshot(session_id: str, tick: int = 0) -> dict[str, Any]:
    """Build the canonical initial mock snapshot.

    Produces a ``GameSnapshot``-shaped dict matching the TypeScript interface
    in ``frontend/src/types/game.ts``.
    """
    import copy

    return {
        "session_id": session_id,
        "tick": tick,
        "entities": copy.deepcopy(_MOCK_ENTITIES),
        "territories": copy.deepcopy(_MOCK_TERRITORIES),
        "organizations": copy.deepcopy(_MOCK_ORGS),
        "institutions": copy.deepcopy(_MOCK_INSTITUTIONS),
        "edges": copy.deepcopy(_MOCK_EDGES),
        "economy": copy.deepcopy(_MOCK_ECONOMY),
        "events": [
            {"type": "GAME_STARTED", "tick": tick, "data": {"scenario": "wayne_county_mock"}}
        ],
        "traps": copy.deepcopy(_MOCK_TRAPS),
    }


# --------------------------------------------------------------------------- #
# MockEngineBridge
# --------------------------------------------------------------------------- #


class MockEngineBridge:
    """Deterministic engine bridge for MVP end-to-end testing.

    Persists world state in ``GameSession.snapshot_json`` and advances it
    using the coefficients in ``MockDefines``.  No randomness — identical
    inputs always produce identical outputs.

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
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "id": t["id"],
                        "name": t["name"],
                        "heat": t["heat"],
                        "profit_rate": snap.get("economy", {}).get("profit_rate", 0),
                        "exploitation_rate": snap.get("economy", {}).get("exploitation_rate", 0),
                        "occ": t.get("rent_level", 0),
                        "imperial_rent": snap.get("economy", {}).get("imperial_rent", 0),
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
        _persistent_context: dict[str, Any] | None = None,
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

    def preview_action(self, _session_id: uuid.UUID, **_kwargs: Any) -> dict[str, Any]:
        """Return a stub preview."""
        return {
            "estimated_consciousness_delta": 0.05,
            "estimated_heat_delta": 0.02,
            "action_point_cost": 1,
            "success_probability": 0.85,
            "affected_territory_ids": [],
            "warnings": [],
        }

    # ------------------------------------------------------------------ #
    # Dashboard / inspector endpoints (mostly empty stubs)
    # ------------------------------------------------------------------ #

    def get_entity_detail(self, session_id: uuid.UUID, entity_id: str) -> dict[str, Any]:
        """Return a single entity by ID."""
        snap = self.get_snapshot(session_id)
        for e in snap.get("entities", []):
            if e["id"] == entity_id:
                return dict(e)
        return {}

    def get_territory_detail(self, session_id: uuid.UUID, territory_id: str) -> dict[str, Any]:
        """Return a single territory by ID."""
        snap = self.get_snapshot(session_id)
        for t in snap.get("territories", []):
            if t["id"] == territory_id:
                return dict(t)
        return {}

    def get_economy_summary(self, session_id: uuid.UUID) -> dict[str, Any]:
        """Return economy summary."""
        snap = self.get_snapshot(session_id)
        economy: dict[str, Any] = snap.get("economy", {})
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
        for e in snapshot.get("entities", []):
            e["consciousness"] = self._clamp(
                e["consciousness"] + d.EDUCATE_CONSCIOUSNESS,
                d.CONSCIOUSNESS_FLOOR,
                d.CONSCIOUSNESS_CEILING,
            )
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
        for e in snapshot.get("entities", []):
            e["agitation"] = min(1.0, e["agitation"] + d.MOBILIZE_AGITATION)
        return {"consciousness_delta": 0, "heat_delta": d.MOBILIZE_HEAT, "details": {}}

    def _verb_attack(
        self, snapshot: dict[str, Any], action: PlayerAction, d: MockDefines
    ) -> dict[str, Any]:
        target_id = action.target_id or ""
        for t in snapshot.get("territories", []):
            if t["id"] == target_id:
                t["heat"] = self._clamp(t["heat"] + d.ATTACK_HEAT, d.HEAT_FLOOR, d.HEAT_CEILING)
        for e in snapshot.get("entities", []):
            e["consciousness"] = self._clamp(
                e["consciousness"] + d.ATTACK_CONSCIOUSNESS,
                d.CONSCIOUSNESS_FLOOR,
                d.CONSCIOUSNESS_CEILING,
            )
            e["wealth"] = max(d.WEALTH_FLOOR, e["wealth"] - d.ATTACK_WEALTH_DAMAGE)
        return {
            "consciousness_delta": d.ATTACK_CONSCIOUSNESS,
            "heat_delta": d.ATTACK_HEAT,
            "details": {},
        }

    def _verb_campaign(
        self, snapshot: dict[str, Any], _action: PlayerAction, d: MockDefines
    ) -> dict[str, Any]:
        for e in snapshot.get("entities", []):
            e["consciousness"] = self._clamp(
                e["consciousness"] + d.CAMPAIGN_CONSCIOUSNESS,
                d.CONSCIOUSNESS_FLOOR,
                d.CONSCIOUSNESS_CEILING,
            )
        return {"consciousness_delta": d.CAMPAIGN_CONSCIOUSNESS, "heat_delta": 0, "details": {}}

    def _verb_aid(
        self, snapshot: dict[str, Any], action: PlayerAction, d: MockDefines
    ) -> dict[str, Any]:
        target_id = action.target_id or ""
        for t in snapshot.get("territories", []):
            if t["id"] == target_id:
                t["heat"] = self._clamp(t["heat"] + d.AID_HEAT, d.HEAT_FLOOR, d.HEAT_CEILING)
        for e in snapshot.get("entities", []):
            if e["role"] in ("PROLETARIAT", "LUMPENPROLETARIAT"):
                e["wealth"] = e["wealth"] + d.AID_WEALTH
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
