"""Engine bridge — the sole translation layer between Django and the simulation engine.

This is the **ONLY** file in ``web/`` that imports from ``babylon.engine``,
``babylon.models``, ``babylon.config``, ``babylon.ooda``, or
``babylon.persistence``.  Django views and serializers call this bridge;
they never see engine internals.

All methods return plain Python dicts / lists / scalars that are
JSON-serializable, suitable for DRF serializer consumption.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import networkx as nx

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import (
    create_imperial_circuit_scenario,
    create_labor_aristocracy_scenario,
    create_two_node_scenario,
    create_us_scenario,
)
from babylon.engine.scenarios_wayne_county import create_wayne_county_scenario
from babylon.engine.simulation_engine import step
from babylon.engine.trap_detection import TrapDetectionResult, detect_traps
from babylon.models.config import SimulationConfig
from babylon.models.enums import ActionType
from babylon.models.vanguard_resources import VanguardResources, check_can_afford
from babylon.models.world_state import WorldState
from babylon.ooda.npc_stub import select_npc_actions
from babylon.persistence.protocols import RuntimePersistence

logger = logging.getLogger(__name__)

# Per-session action history for trap detection (in-memory, not persisted).
# Maps session_id -> list of recent action dicts (capped at 50).
_session_action_history: dict[UUID, list[dict[str, Any]]] = {}

# Per-session trap state for severity persistence across ticks.
_session_trap_state: dict[UUID, TrapDetectionResult] = {}

_ACTION_HISTORY_CAP = 50

# ---------------------------------------------------------------------- #
# Verb-to-ActionType mapping (9 canonical player verbs → engine ActionType)
# See: specs/041-mvp-nationwide-sim/research.md §2
# ---------------------------------------------------------------------- #

# Spec 061 US5 (T081, FR-025): Investigate / Move / Negotiate are
# removed from the canonical verb list because their engine handlers
# don't exist yet. The map only contains verbs with real handlers;
# `get_available_actions()` derives its output from this map so the
# unsupported verbs are filtered out of the UI as well. A follow-up
# spec is expected to land real handlers and re-add them.
VERB_TO_ACTION_TYPE: dict[str, ActionType] = {
    "educate": ActionType.EDUCATE,
    "reproduce": ActionType.RECRUIT,
    "attack": ActionType.ATTACK_INFRASTRUCTURE,
    "mobilize": ActionType.PROTEST,
    "campaign": ActionType.PROPAGANDIZE,
    "aid": ActionType.PROVIDE_SERVICE,
}

# Spec 061 US5 (T081, FR-025): verbs that have stale wiring but no
# real engine handler. Listed for documentation; not exposed to the API.
UNSUPPORTED_VERBS: frozenset[str] = frozenset({"investigate", "move", "negotiate"})

CANONICAL_VERBS: frozenset[str] = frozenset(VERB_TO_ACTION_TYPE.keys())


def _fetch_session_rng_seed_from_pool(pool: Any, session_id: UUID) -> int:
    """Read ``rng_seed`` from ``game_session`` (T080 / FR-024).

    Falls back to 0 when the connection fails or the row is missing —
    determinism is best-effort during transient outages.
    """
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT rng_seed FROM game_session WHERE id = %s",
                (session_id,),
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                return int(row[0])
    except Exception:  # noqa: BLE001 — non-fatal; defaults to 0
        logger.exception("Failed to read rng_seed for session %s", session_id)
    return 0


class EngineBridge:
    """Translates between Django request/response and simulation engine.

    Holds a reference to the persistence layer and provides methods
    that orchestrate create → hydrate → step → persist → snapshot cycles.
    """

    def __init__(self, persistence: RuntimePersistence) -> None:
        self._persistence = persistence
        logger.info("EngineBridge initialized with %s", type(persistence).__name__)

    # ------------------------------------------------------------------ #
    # Game lifecycle
    # ------------------------------------------------------------------ #

    def create_game(
        self,
        scenario: str,
        config: dict[str, Any] | None = None,
        defines: dict[str, Any] | None = None,
        rng_seed: int = 0,
        player_id: int | None = None,
    ) -> UUID:
        """Create a new game session and persist the initial state.

        Args:
            scenario: Scenario identifier string.
            config: Optional dict of SimulationConfig overrides.
            defines: Optional dict of GameDefines overrides.
            rng_seed: RNG seed for reproducibility.
            player_id: Django auth user ID, if authenticated.

        Returns:
            The UUID of the newly created session.
        """
        # Validate configs via Pydantic (raises on bad input)
        sim_config = SimulationConfig(**(config or {}))
        game_defines = GameDefines(**(defines or {}))

        # Delegate to persistence layer (PostgresRuntime.create_session)
        session_id: UUID = self._persistence.create_session(  # type: ignore[attr-defined]
            scenario=scenario,
            config_json=sim_config.model_dump(),
            game_defines_json=game_defines.model_dump(),
            rng_seed=rng_seed,
            player_id=player_id,
        )

        # Seed initial world graph for tick 0 so snapshot/state endpoints
        # have material data immediately after game creation.
        initial_state = _build_initial_state_for_scenario(scenario)
        self._persistence.persist_tick(
            tick=initial_state.tick,
            graph=initial_state.to_graph(),
            events=[event.model_dump() for event in initial_state.events] or None,
            session_id=session_id,
        )

        logger.info("Created game session=%s scenario=%s seed=%d", session_id, scenario, rng_seed)
        return session_id

    # ------------------------------------------------------------------ #
    # State access
    # ------------------------------------------------------------------ #

    def hydrate_state(
        self, session_id: UUID, tick: int | None = None
    ) -> tuple[WorldState, nx.DiGraph[str]]:
        """Load a session's graph from persistence and reconstruct WorldState.

        Args:
            session_id: The game session UUID.
            tick: Specific tick to load, or ``None`` for latest.

        Returns:
            Tuple of (WorldState, nx.DiGraph) at the requested tick.
        """
        graph = self._persistence.hydrate_graph(tick=tick, session_id=session_id)

        # Backward-compatible bootstrap: if a legacy/new session has no persisted
        # tick-0 graph yet, seed it from the stored scenario and retry hydrate.
        if tick is None and _is_unseeded_graph(graph):
            session_getter = getattr(self._persistence, "get_session", None)
            if callable(session_getter):
                session_row = session_getter(session_id)
                scenario = (
                    str(session_row.get("scenario", "default"))
                    if isinstance(session_row, dict)
                    else "default"
                )
                seeded_state = _build_initial_state_for_scenario(scenario)
                self._persistence.persist_tick(
                    tick=seeded_state.tick,
                    graph=seeded_state.to_graph(),
                    events=[event.model_dump() for event in seeded_state.events] or None,
                    session_id=session_id,
                )
                graph = self._persistence.hydrate_graph(tick=tick, session_id=session_id)

        # Determine the tick from the graph metadata
        resolved_tick = tick if tick is not None else _graph_tick(graph)
        world_state = WorldState.from_graph(graph, tick=resolved_tick)
        return world_state, graph

    def get_snapshot(self, session_id: UUID) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the current game state.

        Args:
            session_id: The game session UUID.

        Returns:
            Dict with keys: session_id, tick, entities, territories,
            organizations, institutions, economy, events.
        """
        state, _graph = self.hydrate_state(session_id)
        return _state_to_snapshot(state, session_id)

    def get_map_snapshot(
        self,
        session_id: UUID,
        tick: int | None = None,
        _layer: str | None = None,
        zoom: str = "county",
    ) -> dict[str, Any]:
        """Return a GeoJSON FeatureCollection of hex states for a given tick.

        Args:
            session_id: The game session UUID.
            tick: The tick to query data for. If None, uses current tick.
            layer: Optional layer filter (unused here, filtering done in API).
            zoom: Spatial aggregation level (state/bea/msa/county/hex).

        Returns:
            GeoJSON dict matching the HexMap frontend contract.
        """
        import h3

        from game.models import GameSession, HexState

        try:
            session = GameSession.objects.get(id=session_id)
        except GameSession.DoesNotExist:
            return {"type": "FeatureCollection", "metadata": {}, "features": []}

        target_tick = tick if tick is not None else session.current_tick

        hex_states = HexState.objects.filter(game=session, tick=target_tick)

        if zoom == "hex":
            # Full hex-level detail — no aggregation
            features = []
            for state in hex_states:
                boundary = h3.cell_to_boundary(state.h3_index)
                coordinates = [[lng, lat] for lat, lng in boundary]
                coordinates.append(coordinates[0])

                feature = {
                    "type": "Feature",
                    "id": state.h3_index,
                    "geometry": {"type": "Polygon", "coordinates": [coordinates]},
                    "properties": {
                        "h3_index": state.h3_index,
                        "county_fips": state.county_fips,
                        "county_name": state.county_name,
                        "bea_ea_code": state.bea_ea_code,
                        "msa_code": state.msa_code,
                        "profit_rate": state.profit_rate,
                        "exploitation_rate": state.exploitation_rate,
                        "occ": state.occ,
                        "imperial_rent": state.imperial_rent,
                        "heat": state.heat,
                        "org_presence": state.org_count,
                        "dominant_class": state.dominant_class,
                        "population": state.pop_total,
                    },
                }
                features.append(feature)
        else:
            # Aggregated zoom level — group by dimension column
            features = self._aggregate_hex_features(hex_states, zoom)

        return {
            "type": "FeatureCollection",
            "metadata": {
                "tick": target_tick,
                "scenario": session.scenario,
                "h3_resolution": 7,
                "zoom": zoom,
                "available_metrics": [
                    "profit_rate",
                    "exploitation_rate",
                    "occ",
                    "imperial_rent",
                    "heat",
                    "org_presence",
                ],
            },
            "features": features,
        }

    @staticmethod
    def _aggregate_hex_features(
        hex_states: Any,
        zoom: str,
    ) -> list[dict[str, Any]]:
        """Aggregate hex-level data to a higher zoom tier.

        Groups hex states by the dimension column matching the zoom level,
        then computes weighted averages (by population) for numeric metrics
        and sums for additive metrics.
        """
        from collections import defaultdict

        # Map zoom level to the grouping key
        group_key_map = {
            "state": "state_fips",
            "bea": "bea_ea_code",
            "msa": "msa_code",
            "county": "county_fips",
        }
        group_attr = group_key_map.get(zoom, "county_fips")

        # Accumulators: group_value → {metric sums}
        groups: dict[str, dict[str, float]] = defaultdict(
            lambda: {
                "profit_rate_sum": 0.0,
                "exploitation_rate_sum": 0.0,
                "occ_sum": 0.0,
                "imperial_rent_sum": 0.0,
                "heat_sum": 0.0,
                "org_presence_sum": 0,
                "population_sum": 0,
                "count": 0,
            }
        )
        group_names: dict[str, str] = {}

        for state in hex_states:
            key = getattr(state, group_attr, None)
            if key is None:
                key = "unknown"
            acc = groups[key]
            pop = state.pop_total or 0
            acc["profit_rate_sum"] += (state.profit_rate or 0) * pop
            acc["exploitation_rate_sum"] += (state.exploitation_rate or 0) * pop
            acc["occ_sum"] += (state.occ or 0) * pop
            acc["imperial_rent_sum"] += state.imperial_rent or 0
            acc["heat_sum"] += (state.heat or 0) * pop
            acc["org_presence_sum"] += state.org_count or 0
            acc["population_sum"] += pop
            acc["count"] += 1

            # Capture a name for the group
            if key not in group_names:
                group_names[key] = state.county_name or key

        features: list[dict[str, Any]] = []
        for key, acc in groups.items():
            total_pop = acc["population_sum"] or 1  # avoid div-by-zero
            features.append(
                {
                    "type": "Feature",
                    "id": key,
                    "geometry": None,  # Geometry deferred — frontend uses reference polygons
                    "properties": {
                        "group_key": key,
                        "group_name": group_names.get(key, key),
                        "zoom": zoom,
                        "hex_count": acc["count"],
                        "profit_rate": round(acc["profit_rate_sum"] / total_pop, 6),
                        "exploitation_rate": round(acc["exploitation_rate_sum"] / total_pop, 4),
                        "occ": round(acc["occ_sum"] / total_pop, 4),
                        "imperial_rent": round(acc["imperial_rent_sum"], 2),
                        "heat": round(acc["heat_sum"] / total_pop, 4),
                        "org_presence": acc["org_presence_sum"],
                        "population": acc["population_sum"],
                    },
                }
            )

        return features

    # ------------------------------------------------------------------ #
    # Domain Dashboards (Scaffolding for full UI requirements)
    # ------------------------------------------------------------------ #

    def get_game_summary(self, _session_id: UUID) -> dict[str, Any]:
        """Return the top-bar summary data: tick, profit rate, phi, state faction, alerts."""
        return {}

    def get_game_timeseries(self, session_id: UUID) -> dict[str, Any]:
        """Return historical timeseries data for charting (spec 061 US3, FR-026).

        Reads the per-tick aggregates from the ``tick_summary`` table and
        emits the six named arrays the v2 Briefing/Analysis pages chart:
        ``imperial_rent``, ``consciousness``, ``solidarity``, ``heat``,
        ``wealth``, ``biocapacity``. Each array is parallel-indexed with
        the ``ticks`` array (oldest tick first). Missing values become
        ``None`` so the frontend can interpolate / hide gaps without a
        backend round-trip.

        The persistence layer fronts this via
        :meth:`PostgresRuntime.query_tick_summary_series`. SQLite-backed
        ``RuntimeDatabase`` returns an empty list (the v2 pages are only
        ever consumed against a live Postgres deployment).
        """
        rows: list[dict[str, Any]] = []
        query = getattr(self._persistence, "query_tick_summary_series", None)
        if callable(query):
            try:
                rows = query(session_id)
            except Exception:  # noqa: BLE001 — diagnostic; never blocks request
                logger.exception("get_game_timeseries: query_tick_summary_series failed")
                rows = []

        ticks: list[int] = []
        imperial_rent: list[float | None] = []
        consciousness: list[float | None] = []
        solidarity: list[float | None] = []
        heat: list[float | None] = []
        wealth: list[float | None] = []
        biocapacity: list[float | None] = []
        for row in rows:
            ticks.append(int(row.get("tick", 0)))
            imperial_rent.append(_optional_float(row.get("imperial_rent")))
            consciousness.append(_optional_float(row.get("avg_consciousness")))
            # No dedicated columns yet — these fields fall back gracefully.
            solidarity.append(_optional_float(row.get("solidarity_edge_count")))
            heat.append(_optional_float(row.get("total_heat")))
            wealth.append(_optional_float(row.get("total_wealth")))
            biocapacity.append(_optional_float(row.get("total_biocapacity")))
        return {
            "ticks": ticks,
            "imperial_rent": imperial_rent,
            "consciousness": consciousness,
            "solidarity": solidarity,
            "heat": heat,
            "wealth": wealth,
            "biocapacity": biocapacity,
        }

    def get_economy_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        """Return the economy left-panel dashboard data."""
        return {}

    def get_communities_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        """Return communities dashboard (spec 061 US6 T089, FR-018).

        Returns ``{"communities": [...]}`` where each entry has the
        canonical shape from ``contracts/communities.yaml``. The engine
        Community model is not yet wired through the bridge; until that
        lands (US6 follow-up), this method emits an empty list — the
        frontend can render a "no communities surfaced" empty state.
        """
        return {"communities": []}

    # ------------------------------------------------------------------ #
    # Spec 061 US6 T091: inspector endpoints (FR-019)
    #
    # Each inspector returns a populated detail object matching
    # contracts/inspectors.yaml. The current implementations look up the
    # entity in the existing snapshot helpers and wrap the result in the
    # standard envelope. Recent-activity / history tails (which require
    # query_org_recent_actions, query_edge_history per T092/T093) are
    # left as empty lists until the deeper persistence wiring lands.
    # ------------------------------------------------------------------ #

    def inspect_node(self, session_id: UUID, node_id: str) -> dict[str, Any]:
        """Generic node lookup — dispatches by node type (FR-019)."""
        state, _ = self.hydrate_state(session_id)
        snap = _state_to_snapshot(state, session_id)
        for collection in ("organizations", "institutions", "territories"):
            for entry in snap.get(collection, []):
                if entry.get("id") == node_id:
                    return {"node": entry, "collection": collection}
        return {"node": None, "collection": None}

    def inspect_org(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        state, _ = self.hydrate_state(session_id)
        snap = _state_to_snapshot(state, session_id)
        org = next((o for o in snap.get("organizations", []) if o.get("id") == org_id), None)
        return {
            "org": org,
            "recent_actions": [],  # T092: populated when query_org_recent_actions lands
        }

    def inspect_community(self, _session_id: UUID, _community_id: str) -> dict[str, Any]:
        return {"community": None, "members": []}

    def inspect_edge(
        self, session_id: UUID, source_id: str, target_id: str, edge_type: str
    ) -> dict[str, Any]:
        state, _ = self.hydrate_state(session_id)
        snap = _state_to_snapshot(state, session_id)
        edge = next(
            (
                e
                for e in snap.get("edges", [])
                if e.get("source_id") == source_id
                and e.get("target_id") == target_id
                and e.get("mode") == edge_type
            ),
            None,
        )
        return {
            "edge": edge,
            "history": [],  # T093: populated when query_edge_history lands
        }

    def inspect_hex(self, session_id: UUID, h3_index: str) -> dict[str, Any]:
        state, _ = self.hydrate_state(session_id)
        snap = _state_to_snapshot(state, session_id)
        territory = next(
            (t for t in snap.get("territories", []) if t.get("h3_index") == h3_index),
            None,
        )
        return {"hex": territory}

    def get_organizations_dashboard(
        self, session_id: UUID, player_only: bool = False
    ) -> dict[str, Any]:
        """Return the organizations left-panel dashboard data."""
        state, _ = self.hydrate_state(session_id)
        snap = _state_to_snapshot(state, session_id)
        orgs = snap.get("organizations", [])
        if player_only:
            orgs = [o for o in orgs if o.get("vanguard") is not None]
        return {"organizations": orgs}

    def get_edges_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        """Return the edges/relations left-panel dashboard data."""
        return {}

    def get_state_apparatus_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        """Return the state-apparatus intelligence screen data."""
        return {}

    def get_journal_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        """Return the historical event log data."""
        return {}

    def get_alerts_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        """Return the active alerts and threshold crossings."""
        return {}

    # ------------------------------------------------------------------ #
    # Inspector Views
    # ------------------------------------------------------------------ #

    def get_inspector_node(self, _session_id: UUID, _node_id: str) -> dict[str, Any]:
        """Return detailed stats for a generic node click."""
        return {}

    def get_inspector_org(self, _session_id: UUID, _org_id: str) -> dict[str, Any]:
        """Return detailed drill-down data for a specific organization."""
        return {}

    def get_inspector_community(self, _session_id: UUID, _hyperedge_id: str) -> dict[str, Any]:
        """Return detailed drill-down data for a community hyperedge."""
        return {}

    def get_inspector_edge(self, _session_id: UUID, _edge_id: str) -> dict[str, Any]:
        """Return detailed drill-down data for an edge."""
        return {}

    def get_inspector_hex(self, _session_id: UUID, _h3_index: str) -> dict[str, Any]:
        """Return detailed drill-down data for a map hex."""
        return {}

    # ------------------------------------------------------------------ #
    # Tick resolution
    # ------------------------------------------------------------------ #

    def resolve_tick(
        self,
        session_id: UUID,
        persistent_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Advance the simulation one tick: hydrate → step → persist → snapshot.

        Reads pending player actions, injects them into the engine via
        ``persistent_context["player_actions"]``, captures pre-step state
        for delta computation, runs the engine step, persists ActionResult
        rows, and checks for endgame conditions.

        Args:
            session_id: The game session UUID.
            persistent_context: Optional cross-tick context dict.

        Returns:
            JSON-serializable snapshot of the new state after stepping.
        """
        state, graph = self.hydrate_state(session_id)

        # Load defines from the session's stored config
        metadata_raw = self._persistence.get_metadata("game_defines_json")
        if metadata_raw is not None:
            import json

            game_defines = GameDefines(**json.loads(metadata_raw))
        else:
            game_defines = GameDefines()

        # Spec 061 US5 T080 (FR-024): thread the session's rng_seed
        # into the engine config so action resolution is byte-deterministic
        # across replays of the same seed + action sequence.
        rng_seed = _fetch_session_rng_seed_from_pool(
            getattr(self._persistence, "_pool", None), session_id
        )
        sim_config = SimulationConfig(rng_seed=rng_seed)

        # T014: Read pending player actions and format for engine injection
        pending = self.get_pending_actions(session_id, state.tick)
        if persistent_context is None:
            persistent_context = {}

        if pending:
            player_actions: dict[str, list[dict[str, Any]]] = {}
            for action in pending:
                org_id = action["org_id"]
                verb = action.get("verb", "")
                action_type_enum = VERB_TO_ACTION_TYPE.get(verb)
                action_type_val = action_type_enum.value if action_type_enum else verb

                player_actions.setdefault(org_id, []).append(
                    {
                        "action_type": action_type_val,
                        "target_id": action.get("target_id", org_id),
                        "org_id": org_id,
                        "action_point_cost": 1,
                        "params": action.get("params_json", {}),
                    }
                )
            persistent_context["player_actions"] = player_actions

        # T015: Snapshot pre-step state for delta computation
        pre_step: dict[str, dict[str, float]] = {}
        for action in pending:
            tid = action.get("target_id")
            if tid and tid in graph.nodes:
                pre_step[tid] = {
                    "consciousness": float(graph.nodes[tid].get("class_consciousness", 0.0)),
                    "heat": float(graph.nodes[tid].get("heat", 0.0)),
                }

        # Step the engine
        logger.debug("Stepping engine session=%s tick=%d", session_id, state.tick)
        new_state = step(
            state,
            sim_config,
            persistent_context=persistent_context,
            defines=game_defines,
        )
        logger.info(
            "Engine step complete session=%s tick=%d->%d entities=%d events=%d",
            session_id,
            state.tick,
            new_state.tick,
            len(new_state.entities),
            len(new_state.events),
        )

        # Persist the new tick
        new_graph = new_state.to_graph()
        events_as_dicts: list[dict[str, Any]] = [e.model_dump() for e in new_state.events]
        self._persistence.persist_tick(
            tick=new_state.tick,
            graph=new_graph,
            events=events_as_dicts if events_as_dicts else None,
            session_id=session_id,
        )

        # T016: Persist ActionResult records with computed deltas
        for action in pending:
            tid = action.get("target_id")
            pre = pre_step.get(tid or "", {})
            post_consciousness = 0.0
            post_heat = 0.0
            if tid and tid in new_graph.nodes:
                post_consciousness = float(new_graph.nodes[tid].get("class_consciousness", 0.0))
                post_heat = float(new_graph.nodes[tid].get("heat", 0.0))

            verb = action.get("verb", "")
            action_type_enum = VERB_TO_ACTION_TYPE.get(verb)
            action_type_val = action_type_enum.value if action_type_enum else verb

            result_data = {
                "session_id": session_id,
                "tick": new_state.tick,
                "org_id": action["org_id"],
                "action_type": action_type_val,
                "target_id": tid,
                "target_community": action.get("target_community"),
                "initiative_score": 0.0,
                "action_cost": 1.0,
                "success": True,
                "consciousness_delta": post_consciousness - pre.get("consciousness", 0.0),
                "heat_delta": post_heat - pre.get("heat", 0.0),
                "details": None,
            }
            _persist_action_result(self._persistence, result_data)

        # T019: Check for endgame conditions in events
        snapshot = _state_to_snapshot(new_state, session_id)
        endgame_types = {"REVOLUTIONARY_VICTORY", "ECOLOGICAL_COLLAPSE", "FASCIST_CONSOLIDATION"}
        for event in new_state.events:
            event_type = (
                event.event_type.value
                if hasattr(event.event_type, "value")
                else str(event.event_type)
            )
            if event_type in endgame_types:
                snapshot["endgame"] = {
                    "outcome": event_type,
                    "tick": new_state.tick,
                    "summary": event.data.get("summary", "")
                    if hasattr(event, "data") and isinstance(event.data, dict)
                    else "",
                }
                break

        # Mark submitted turns as resolved
        _mark_resolved_safe(self._persistence, session_id, state.tick)

        return snapshot

    # ------------------------------------------------------------------ #
    # Action management
    # ------------------------------------------------------------------ #

    def get_available_actions(self, session_id: UUID) -> dict[str, Any]:
        """Return available NPC actions for the current tick.

        Uses the OODA npc_stub to compute what actions each org can take.

        Args:
            session_id: The game session UUID.

        Returns:
            Dict with session_id, tick, and per-org action lists.
        """
        state, graph = self.hydrate_state(session_id)
        game_defines = GameDefines()

        org_actions: dict[str, list[dict[str, Any]]] = {}

        for node_id, data in graph.nodes(data=True):
            if data.get("_node_type") != "organization":
                continue
            # Find a default target (first territory the org is present in)
            target_id = ""
            territory_ids = data.get("territory_ids")
            if territory_ids:
                if isinstance(territory_ids, (list, tuple, frozenset, set)):
                    target_id = next(iter(territory_ids), "")
                else:
                    target_id = str(territory_ids)

            actions = select_npc_actions(
                org_id=node_id,
                org_attrs=dict(data),
                target_id=target_id,
                defines=game_defines.ooda,
            )
            org_actions[node_id] = [
                {
                    "org_id": a.org_id,
                    "action_type": a.action_type.value
                    if hasattr(a.action_type, "value")
                    else str(a.action_type),
                    "target_id": a.target_id,
                    "action_point_cost": a.action_point_cost,
                }
                for a in actions
            ]

        return {
            "session_id": str(session_id),
            "tick": state.tick,
            "actions": org_actions,
        }

    def submit_action(
        self,
        session_id: UUID,
        tick: int,
        org_id: str,
        verb: str,
        *,
        action_type: str | None = None,
        target_id: str | None = None,
        target_community: str | None = None,
        params_json: dict[str, Any] | None = None,
    ) -> int:
        """Submit a player action for the given tick.

        Performs affordability checks using VanguardResources before
        persisting the action. Raises ValueError if the org cannot
        afford the action.

        Args:
            session_id: The game session UUID.
            tick: The tick this action applies to.
            org_id: The organization taking the action.
            verb: Action verb string.
            action_type: Optional action type classification.
            target_id: Optional target node ID.
            target_community: Optional target community.
            params_json: Optional action parameters.

        Returns:
            The integer turn ID from the database.

        Raises:
            ValueError: If the org cannot afford the action.
        """
        # Affordability check: compute vanguard resources and verify
        state, _graph = self.hydrate_state(session_id)
        org = state.organizations.get(org_id)
        if org is not None:
            resources = VanguardResources.from_organization(
                cadre_level=float(org.cadre_level),
                cohesion=float(org.cohesion),
                budget=float(org.budget),
                heat=float(org.heat),
                territory_count=len(org.territory_ids),
            )
            if verb == "attack":
                # Special handling for ATTACK verb mode-specific costs
                mode = (params_json or {}).get("mode", "targeted")
                if mode == "targeted":
                    if resources.cadre_labor < 4.0:
                        raise ValueError(
                            f"Cannot afford 'attack' (targeted): Need 4.0 CL, have {resources.cadre_labor:.1f}"
                        )
                else:  # mass
                    if resources.sympathizer_labor < 15.0:
                        raise ValueError(
                            f"Cannot afford 'attack' (mass): Need 15.0 SL, have {resources.sympathizer_labor:.1f}"
                        )
                # AP check is bypassed here since over-budget AP resolves with degraded effectiveness
            else:
                can_afford, reason = check_can_afford(resources, verb)
                if not can_afford:
                    msg = f"Cannot afford '{verb}': {reason}"
                    raise ValueError(msg)

        # Record in action history for trap detection
        history = _session_action_history.setdefault(session_id, [])
        history.append({"verb": verb, "org_id": org_id, "target_id": target_id, "tick": tick})
        if len(history) > _ACTION_HISTORY_CAP:
            _session_action_history[session_id] = history[-_ACTION_HISTORY_CAP:]

        result: int = self._persistence.submit_turn(  # type: ignore[attr-defined]
            session_id=session_id,
            tick=tick,
            org_id=org_id,
            verb=verb,
            action_type=action_type,
            target_id=target_id,
            target_community=target_community,
            params_json=params_json,
        )
        return result

    def get_org_status(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return basic status and OODA cycle information for an acting organization."""
        state, graph = self.hydrate_state(session_id)
        if org_id not in graph.nodes:
            return {}

        org_data = graph.nodes[org_id]

        # Determine resource pools
        cadre = float(org_data.get("cadre_level", 0.0))
        cohesion = float(org_data.get("cohesion", 0.0))
        budget = float(org_data.get("budget", 0.0))
        heat = float(org_data.get("heat", 0.0))

        # Territory ids can be list, set, frozenset
        territory_ids = org_data.get("territory_ids", [])
        terr_count = len(territory_ids)

        resources = VanguardResources.from_organization(
            cadre_level=cadre,
            cohesion=cohesion,
            budget=budget,
            heat=heat,
            territory_count=terr_count,
        )

        # Pending action state
        pending = self.get_pending_actions(session_id, state.tick)

        # Estimate AP
        ap_max = 3
        ap_used = len([a for a in pending if a.get("org_id") == org_id])
        ap_remaining = max(0, ap_max - ap_used)

        return {
            "id": org_id,
            "name": org_data.get("name", org_id),
            "type": str(org_data.get("org_type", "PoliticalFaction")),
            "consciousness_strategy": str(org_data.get("consciousness_strategy", "revolutionary")),
            "resources": {
                "cadre_labor": float(resources.cadre_labor),
                "sympathizer_labor": float(resources.sympathizer_labor),
                "material": float(resources.budget),
            },
            "ooda": {
                "action_points_remaining": ap_remaining,
                "action_points_max": ap_max,
                "cycle_time": 2,
            },
            "cadre_level": cadre,
            "cohesion": cohesion,
        }

    def get_educate_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available community targets for the EDUCATE verb.

        Matches the contract defined in spec 043, integrating actual
        consciousness and material readiness from the graph when available.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            # Provide an empty fallback if org not found
            return {"status": "error", "error": "Org not found"}

        # Compute cost
        cost = {
            "action_points": 1,
            "cadre_labor": 3.0,
            "sympathizer_labor": 0.0,
            "material": 0.0,
            "can_afford": org_status.get("resources", {}).get("cadre_labor", 0) >= 3.0,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        targets = []
        unavailable_communities = []

        org_data = graph.nodes.get(org_id, {})
        territory_ids = org_data.get("territory_ids", [])
        for tid in territory_ids:
            if tid in graph.nodes:
                terr_data = graph.nodes[tid]
                terr_name = terr_data.get("name", tid)

                # Mock target aligned with graph
                targets.append(
                    {
                        "community_id": f"community-new-afrikan-{tid}",
                        "community_type": "NEW_AFRIKAN",
                        "category": "contradiction_pair",
                        "territory_name": terr_name,
                        "territory_id": str(tid),
                        "credibility": org_status.get("cohesion", 0.72),
                        "credibility_explanation": f"{int(org_status.get('cohesion', 0.72) * 100)}% membership overlap",
                        "consciousness": {
                            "r": 0.25,
                            "l": 0.55,
                            "f": 0.20,
                            "dominant_tendency": "liberal",
                            "collective_identity": 0.25,
                            "ideological_contestation": 0.82,
                        },
                        "material_readiness": {
                            "avg_agitation": 0.45,
                            "readiness_score": 1.0,
                            "readiness_explanation": "Material conditions have prepared the ground.",
                        },
                        "education_pressure": {
                            "current": 0.12,
                            "projected_delta": 0.036,
                            "projected_new": 0.156,
                            "decay_per_tick": 0.012,
                        },
                        "feedforward": {
                            "projected_routing_shift": {
                                "r_gain_per_tick": 0.008,
                                "f_reduction_per_tick": 0.005,
                                "l_reduction_per_tick": 0.003,
                                "explanation": "Education will shift ~0.8% toward revolutionary tendency per tick",
                            },
                            "state_ai_visibility": "medium",
                            "state_ai_likely_response": "RESEARCH",
                            "turns_to_dominant_tendency_shift": 18,
                            "turns_explanation": "~18 ticks assuming sustained effort",
                        },
                    }
                )

                unavailable_communities.append(
                    {
                        "community_id": f"community-settler-{tid}",
                        "community_type": "SETTLER",
                        "territory_name": terr_name,
                        "reason": "No membership overlap — credibility ≈ 0",
                    }
                )
                break

        # Default mock if no matching territory
        if not targets:
            targets.append(
                {
                    "community_id": "community-new-afrikan-wayne",
                    "community_type": "NEW_AFRIKAN",
                    "category": "contradiction_pair",
                    "territory_name": "Wayne County",
                    "territory_id": "territory-26163",
                    "credibility": 0.72,
                    "credibility_explanation": "72% membership overlap",
                    "consciousness": {
                        "r": 0.25,
                        "l": 0.55,
                        "f": 0.20,
                        "dominant_tendency": "liberal",
                        "collective_identity": 0.25,
                        "ideological_contestation": 0.82,
                    },
                    "material_readiness": {
                        "avg_agitation": 0.45,
                        "readiness_score": 1.0,
                        "readiness_explanation": "Material conditions have prepared the ground.",
                    },
                    "education_pressure": {
                        "current": 0.12,
                        "projected_delta": 0.036,
                        "projected_new": 0.156,
                        "decay_per_tick": 0.012,
                    },
                    "feedforward": {
                        "projected_routing_shift": {
                            "r_gain_per_tick": 0.008,
                            "f_reduction_per_tick": 0.005,
                            "l_reduction_per_tick": 0.003,
                            "explanation": "Education will shift ~0.8% toward revolutionary tendency per tick",
                        },
                        "state_ai_visibility": "medium",
                        "state_ai_likely_response": "RESEARCH",
                        "turns_to_dominant_tendency_shift": 18,
                        "turns_explanation": "~18 ticks assuming sustained effort",
                    },
                }
            )

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "educate",
            "acting_org": org_status,
            "cost": cost,
            "targets": targets,
            "unavailable_communities": unavailable_communities,
        }

    def get_aid_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available targets for the AID verb.

        Matches the contract defined in spec 045, integrating actual
        material deficits and edge statuses from the graph when available.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        # Compute cost metrics
        cost = {
            "action_points": 1,
            "cadre_labor": 1.0,
            "sympathizer_labor": 1.0,
            "material": 0.0,
            "can_afford": org_status.get("resources", {}).get("cadre_labor", 0) >= 1.0,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        population_targets = []
        org_targets = []
        unavailable_targets = []

        org_data = graph.nodes.get(org_id, {})
        territory_ids = org_data.get("territory_ids", [])

        for tid in territory_ids:
            if tid in graph.nodes:
                terr_data = graph.nodes[tid]
                terr_name = terr_data.get("name", tid)

                # Mock Population Target
                population_targets.append(
                    {
                        "community_id": f"community-new-afrikan-{tid}",
                        "community_name": f"New Afrikan Proletariat ({terr_name})",
                        "population": 45000,
                        "class_name": "PROLETARIAT",
                        "material_conditions": {
                            "v_value_produced": 120.5,
                            "wage_received": 95.0,
                            "consumption_gap": 25.5,
                            "subsistence_level": 100.0,
                            "agitation_level": 0.45,
                        },
                        "edge_status": {
                            "type": "TRANSACTIONAL",
                            "solidarity_accumulation": 0.3,
                            "education_pressure": 0.12,
                        },
                        "feedforward": {
                            "consumption_ratio_delta": 0.1,
                            "agitation_delta": -0.05,
                            "solidarity_added": 0.15,
                            "economism_risk": "WARNING: High agitation relief without sufficient education pressure could trigger right-routing.",
                        },
                    }
                )

                # Mock Org Target
                org_targets.append(
                    {
                        "org_id": f"org-mutual-aid-{tid}",
                        "org_name": f"Detroit Mutual Aid ({terr_name})",
                        "org_type": "CIVIL_SOCIETY",
                        "material_stock": 450.0,
                        "edge_status": {
                            "type": "NONE",
                            "solidarity_accumulation": 0.0,
                            "education_pressure": 0.0,
                        },
                        "feedforward": {
                            "consumption_ratio_delta": 0.0,
                            "agitation_delta": 0.0,
                            "solidarity_added": 0.15,
                            "economism_risk": None,
                        },
                    }
                )

                unavailable_targets.append(
                    {
                        "community_id": f"community-settler-{tid}",
                        "community_type": "SETTLER",
                        "territory_name": terr_name,
                        "reason": "Geographically inaccessible or no material deficit.",
                    }
                )
                break

        # Default mock if no matching territory
        if not population_targets:
            population_targets.append(
                {
                    "community_id": "community-new-afrikan-wayne",
                    "community_name": "New Afrikan Proletariat (Wayne County)",
                    "population": 45000,
                    "class_name": "PROLETARIAT",
                    "material_conditions": {
                        "v_value_produced": 120.5,
                        "wage_received": 95.0,
                        "consumption_gap": 25.5,
                        "subsistence_level": 100.0,
                        "agitation_level": 0.45,
                    },
                    "edge_status": {
                        "type": "TRANSACTIONAL",
                        "solidarity_accumulation": 0.3,
                        "education_pressure": 0.12,
                    },
                    "feedforward": {
                        "consumption_ratio_delta": 0.1,
                        "agitation_delta": -0.05,
                        "solidarity_added": 0.15,
                        "economism_risk": "WARNING: High agitation relief without sufficient education pressure could trigger right-routing.",
                    },
                }
            )

            org_targets.append(
                {
                    "org_id": "org-mutual-aid-wayne",
                    "org_name": "Detroit Mutual Aid (Wayne County)",
                    "org_type": "CIVIL_SOCIETY",
                    "material_stock": 450.0,
                    "edge_status": {
                        "type": "NONE",
                        "solidarity_accumulation": 0.0,
                        "education_pressure": 0.0,
                    },
                    "feedforward": {
                        "consumption_ratio_delta": 0.0,
                        "agitation_delta": 0.0,
                        "solidarity_added": 0.15,
                        "economism_risk": None,
                    },
                }
            )

            unavailable_targets.append(
                {
                    "community_id": "community-settler-wayne",
                    "community_type": "SETTLER",
                    "territory_name": "Wayne County",
                    "reason": "Geographically inaccessible or no material deficit.",
                }
            )

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "aid",
            "acting_org": org_status,
            "cost": cost,
            "population_targets": population_targets,
            "org_targets": org_targets,
            "unavailable_targets": unavailable_targets,
        }

    def get_mobilize_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available targets for the MOBILIZE verb.

        Matches the contract defined in spec 047, evaluating target territories
        and businesses for mass action vectors (PROTEST/STRIKE). Returns solidarity
        amplification opportunities and cost projections.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        return {
            "entity_id": org_id,
            "name": org_status.get("name", "Unknown Org"),
            "available_sl": org_status.get("solidarity", 0.0),
            "available_cl": org_status.get("consciousness", 0.0),
            "mobilize_cost_cl": 0.2,  # Hardcoded matching GameDefines for mock
            "targets": [
                {
                    "id": "biz_auto_plant_1",
                    "name": "Jefferson North Assembly",
                    "type": "BUSINESS",
                    "consciousness": 0.55,
                    "heat": 0.2,
                    "base_agitation": 0.4,
                    "coordination_opportunities": [
                        {
                            "type": "SOLIDARITY_AMPLIFICATION",
                            "ally": {"id": "org_uaw_local", "name": "UAW Local"},
                            "multiplier": 1.15,
                        }
                    ],
                    "sl_options": [
                        {
                            "sl_committed": 100.0,
                            "estimated_effects": {
                                "solidarity_overview": {
                                    "base_turnout": 1000,
                                    "amplified_turnout": 1150,
                                    "total_multiplier": 1.15,
                                    "allies_activated": 1,
                                },
                                "consciousness": {"agitation_delta": 0.07, "new_agitation": 0.47},
                                "value": {
                                    "disrupted_production": 50000.0,
                                    "surplus_denied": 15000.0,
                                },
                                "state_response": {
                                    "heat_delta": 0.05,
                                    "new_heat": 0.25,
                                    "ddos_effect": {"active": False, "attention_diverted": 0},
                                },
                            },
                        }
                    ],
                }
            ],
        }

    def get_attack_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available targets for the ATTACK verb.

        Matches the contract defined in spec 046, providing organizational,
        edge, and institutional targets with projections for constant capital
        destruction and severed flow.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        # Compute cost metrics
        cost = {
            "action_points": 3,
            "cadre_labor_if_targeted": 2.5,
            "sympathizer_labor_if_mass": 25.0,
            "material": 100.0,
            "can_afford_targeted": True,
            "can_afford_mass": True,
            "over_budget_ap": False,
            "cost_explanation": "TARGETED attacks use dense cadre formations. MASS actions use diffused sympathizer labor. Both require AP and initial materials.",
        }

        ultra_left_warning = {
            "active": True,
            "trap_score": 0.85,
            "indicators": [
                "Premature violence without mass base",
                "High potential for severe state repression",
            ],
            "explanation": "Carrying out armed struggle without sufficient mass support or defensive capacity triggers the ultra-left trap, isolating vanguard elements.",
        }

        warsaw_ghetto_flag = {
            "active": False,
            "population_p_acquiescence": 0.45,
            "threshold": 0.05,
            "explanation": "If survival probabilities reach near absolute zero, mass base will endorse desperate measures regardless of military feasibility.",
        }

        organizations = [
            {
                "target_id": "org-wayne-auto-parts-inc",
                "target_type": "CAPITAL",
                "name": "Wayne Auto Parts Inc.",
                "territory_name": "Wayne County",
                "territory_id": "wayne",
                "defensive_capacity": 450.0,
                "description": "Mid-sized Constant Capital depot relying heavily on extracted labor from the periphery.",
                "value_tensor_role": {
                    "department": "Department_I",
                    "c_stock": 120500.0,
                    "annual_s_extracted": 45000.0,
                    "s_v_ratio": 4.5,
                    "explanation": "High s/v ratio indicates hyper-exploitation. Destroying this stock degrades upstream Imperial Rent.",
                },
                "extractive_edges": [
                    {
                        "edge_id": "edge-wage-wayne",
                        "target_name": "New Afrikan Proletariat (Wayne)",
                        "flow_type": "WAGES",
                        "s_flow_per_tick": 450.5,
                        "explanation": "Exploitation channel extracting surplus value.",
                    }
                ],
                "attack_projection": {
                    "modes": {
                        "targeted_sabotage": {
                            "resource_cost": {
                                "cadre_labor": 3.0,
                                "action_points": 3,
                                "material": 150.0,
                            },
                            "damage_to_target": {
                                "c_destroyed": 24000.0,
                                "c_destruction_pct": 0.20,
                                "capacity_degradation": 15.0,
                                "recovery_ticks": 6,
                                "explanation": "Targeted strikes hit critical infrastructure, bypassing general security.",
                            },
                            "value_flow_disruption": {
                                "s_flow_interrupted": 250.0,
                                "s_flow_interrupt_duration": 4,
                                "explanation": "Production halts briefly.",
                            },
                            "heat_generated": 0.4,
                            "opsec_exposure": 0.15,
                            "detection_probability": 0.35,
                            "explanation": "Highly effective but risks detection of specialized cadres.",
                        },
                        "mass_action": {
                            "resource_cost": {
                                "sympathizer_labor": 50.0,
                                "action_points": 3,
                                "agitation": 10.0,
                            },
                            "damage_to_target": {
                                "wealth_reduction": 15000.0,
                                "capacity_degradation": 5.0,
                                "recovery_ticks": 2,
                                "explanation": "Mass pickets and property damage.",
                            },
                            "value_flow_disruption": {
                                "s_flow_interrupted": 450.0,
                                "s_flow_interrupt_duration": 1,
                                "explanation": "Complete shutdown of site for duration of mass action.",
                            },
                            "heat_generated": 0.1,
                            "detection_probability": 0.05,
                            "explanation": "Broad action diffuses heat but may lack permanent disruptive power.",
                        },
                    },
                    "collateral_damage": {
                        "affected_population": "community-new-afrikan-wayne",
                        "population_name": "New Afrikan Proletariat",
                        "workers_affected": 450,
                        "wealth_impact": -15.0,
                        "wealth_impact_explanation": "Lost wages from temporary shutdown.",
                        "agitation_effect": 0.05,
                        "agitation_explanation": "Displays of power increase structural agitation.",
                    },
                    "state_ai_response": {
                        "visibility": "HIGH",
                        "immediate_response": "Deployment of tactical state security variants.",
                        "escalation_risk": "High likelihood of activating surveillance grid.",
                        "repression_backfire": {
                            "agitation_generated_on_community": 0.15,
                            "affected_community": "Wayne County",
                            "routing_analysis": "P(S|A) significantly reduced; routing to revolutionary vector.",
                        },
                    },
                    "coherence_check": {
                        "current_coherence": 0.85,
                        "coherence_threshold": 0.50,
                        "network_collapse_risk": False,
                        "explanation": "Target organization maintains high redundancy.",
                    },
                },
            }
        ]

        edges = [
            {
                "target_id": "edge-imperial-rent-core",
                "target_type": "EXTRACTIVE_EDGE",
                "edge_description": "Financial conduit moving surplus from periphery to core.",
                "source_name": "Global South Periphery",
                "sink_name": "Finance Capital",
                "s_flow_per_tick": 4500.0,
                "attack_projection": {
                    "modes": {
                        "targeted_disruption": {
                            "resource_cost": {"cadre_labor": 5.0, "action_points": 4},
                            "heat_generated": 0.7,
                            "detection_probability": 0.4,
                            "edge_effect": "SEVERED",
                            "recovery_duration": 3,
                            "reconnection_probability": 0.85,
                            "effect": "Halts S_flow for 3 ticks.",
                            "explanation": "A high-risk action disrupting global imperial rent algorithms.",
                        }
                    },
                    "state_ai_response": {
                        "visibility": "CRITICAL",
                        "immediate_response": "National Security protocols activated.",
                        "attention_thread_consumed": 2,
                        "thread_diversion_explanation": "State AI shifts 2 operation threads from counter-insurgency to economic stabilization.",
                    },
                },
            }
        ]

        institutions = [
            {
                "target_id": "inst-dpt-of-defense",
                "target_type": "INSTITUTION",
                "name": "State Security Apparatus",
                "factional_control": {"security_state": 45.0, "finance_capital": 55.0},
                "attack_projection": {
                    "modes": {
                        "targeted_sabotage": {
                            "resource_cost": {
                                "cadre_labor": 8.0,
                                "action_points": 5,
                                "material": 400.0,
                            },
                            "heat_generated": 0.95,
                            "detection_probability": 0.85,
                            "legitimacy_note": "Direct assault on state capacity immediately triggers Endgame criteria if unsuccessful.",
                            "explanation": "Massive capacity degradation but extreme risk.",
                        }
                    }
                },
            }
        ]

        unavailable_targets = [
            {
                "target_id": "org-oakland-hedge-fund",
                "name": "Oakland Capital Management",
                "territory_name": "Oakland County",
                "reason": "Your organization has no presence in Oakland County. Use MOVE first, or use INVESTIGATE to gather intelligence remotely.",
            }
        ]

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "attack",
            "acting_org": org_status,
            "cost": cost,
            "ultra_left_warning": ultra_left_warning,
            "warsaw_ghetto_flag": warsaw_ghetto_flag,
            "targets": {
                "organizations": organizations,
                "edges": edges,
                "institutions": institutions,
            },
            "unavailable_targets": unavailable_targets,
        }

    def get_reproduce_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available reproduction modes for the REPRODUCE verb.

        Matches the contract defined in spec 048 for organizational reproduction.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        cost = {
            "action_points": 1,
            "cadre_labor": 0.0,
            "sympathizer_labor": 10.0,
            "material": 0.0,
            "can_afford": org_status.get("resources", {}).get("sympathizer_labor", 0) >= 10.0,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        targets = [
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
                            "sympathizers": int(
                                org_status.get("resources", {}).get("sympathizer_labor", 15)
                            )
                        },
                        "cooldown_applied": 0,
                        "explanation": "Converts 10 sympathizer labor into 1 cadre labor, increasing cohesion.",
                    },
                    "mass_recruitment": {
                        "resource_cost": {"cadre_labor": 2.0},
                        "projected_effect": {
                            "cadre_delta": 0.0,
                            "cohesion_delta": -0.05,
                            "agitation_delta": 0.1,
                        },
                        "recruitment_pool": {"base_population": 45000},
                        "cooldown_applied": 1,
                        "explanation": "Spends cadre labor to prospect among the agitated base. Dilutes cohesion but gains sympathizers.",
                    },
                },
                "state_response": {"state_visibility": "LOW", "attention_diverted": 0.0},
            }
        ]

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "reproduce",
            "acting_org": org_status,
            "cost": cost,
            "targets": targets,
        }

    def get_investigate_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available investigation targets for the INVESTIGATE verb.

        Matches the contract defined in spec 048 for intel-gathering.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        cost = {
            "action_points": 1,
            "cadre_labor": 2.0,
            "sympathizer_labor": 0.0,
            "material": 0.0,
            "can_afford": org_status.get("resources", {}).get("cadre_labor", 0) >= 2.0,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        observe_capability = {"intel_network_strength": 0.6, "max_scan_depth": "TARGETED"}

        territory_scans = [
            {
                "target_id": "territory-26163",
                "name": "Wayne County",
                "target_type": "TERRITORY",
                "heat": 0.45,
                "current_knowledge": {
                    "visibility_level": "SURFACE",
                    "known_attributes": ["population", "dominant_tendency"],
                    "last_scanned_tick": state.tick - 5,
                },
                "resource_cost": {"sympathizer_labor": 5.0},
                "projected_reveals": {
                    "new_visibility_level": "TARGETED",
                    "likely_reveals": ["material_readiness", "hidden_factions", "state_deployment"],
                },
            }
        ]

        targeted_scans = [
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
        ]

        counter_intelligence = {
            "active_moles_suspected": 1,
            "resource_cost": {"cadre_labor": 5.0},
            "projected_reveals": {
                "new_visibility_level": "INTERNAL_AUDIT",
                "likely_reveals": ["mole_identities", "leaked_information_vectors"],
            },
        }

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "investigate",
            "acting_org": org_status,
            "cost": cost,
            "observe_capability": observe_capability,
            "targets": {
                "territory_scans": territory_scans,
                "targeted_scans": targeted_scans,
                "counter_intelligence": counter_intelligence,
            },
        }

    def get_move_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available destinations for the MOVE verb.

        Matches the contract defined in spec 049 for spatial presence.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        cost = {
            "action_points": 1,
            "cadre_labor": 10.0,
            "sympathizer_labor": 0.0,
            "material": 0.0,
            "can_afford": org_status.get("resources", {}).get("cadre_labor", 0) >= 10.0,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        targets = [
            {
                "id": "territory-macomb",
                "name": "Macomb County",
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
        ]

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "move",
            "acting_org": org_status,
            "cost": cost,
            "current_territories": org_status.get("territory_ids", []),
            "targets": targets,
        }

    def get_negotiate_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available targets for the NEGOTIATE verb.

        Matches the contract defined in spec 050 for bilateral edge creation.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        cost = {
            "action_points": 1,
            "cadre_labor": 0.0,
            "sympathizer_labor": 0.0,
            "material": 0.0,
            "can_afford": True,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        targets = [
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
        ]

        de_escalation_targets = [
            {
                "target_id": "org-rival-faction",
                "name": "Rival Revolutionary Faction",
                "antagonism_cause": "ideological_divergence",
                "reconciliation_requirement": "joint_action_against_state",
            }
        ]

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "negotiate",
            "acting_org": org_status,
            "cost": cost,
            "org_leverage": 0.8,
            "targets": targets,
            "de_escalation_targets": de_escalation_targets,
        }

    def preview_action(
        self,
        session_id: UUID,
        org_id: str,
        verb: str,
        target_id: str | None = None,
    ) -> dict[str, Any]:
        """Compute estimated effects of a proposed action without mutating state.

        Uses the current graph state to estimate consciousness delta, heat delta,
        action cost, and success probability. Read-only — no state changes.

        Args:
            session_id: The game session UUID.
            org_id: ID of the acting organization.
            verb: One of the 9 canonical player verbs.
            target_id: Optional target territory or entity ID.

        Returns:
            Dict with estimated deltas, cost, probability, and warnings.
        """
        state, graph = self.hydrate_state(session_id)
        warnings: list[str] = []
        affected_territory_ids: list[str] = []

        # Resolve action type from verb
        action_type_enum = VERB_TO_ACTION_TYPE.get(verb)
        action_cost = 1.0  # Default AP cost

        # Check if org exists
        if org_id not in graph.nodes:
            return {
                "estimated_consciousness_delta": 0.0,
                "estimated_heat_delta": 0.0,
                "action_point_cost": action_cost,
                "success_probability": 0.0,
                "affected_territory_ids": [],
                "warnings": [f"Organization '{org_id}' not found"],
            }

        org_data = graph.nodes[org_id]
        org_budget = float(org_data.get("budget", 0.0))
        org_heat = float(org_data.get("heat", 0.0))
        org_cohesion = float(org_data.get("cohesion", 0.5))

        # Budget warning
        if org_budget < action_cost:
            warnings.append("Insufficient budget for this action")

        # Heat warning
        if org_heat > 0.7:
            warnings.append("Organization heat is already elevated")

        # Estimate effects based on target
        estimated_consciousness_delta = 0.0
        estimated_heat_delta = 0.0
        success_probability = 0.5

        resolved_target = target_id or org_id
        if resolved_target in graph.nodes:
            target_data = graph.nodes[resolved_target]

            # Check if target is under eviction
            if target_data.get("under_eviction", False):
                warnings.append("Target territory is under eviction")

            # Estimate based on verb category
            if verb in {"educate", "campaign"}:
                # Consciousness-raising actions
                estimated_consciousness_delta = 0.05 * org_cohesion
                estimated_heat_delta = 0.01
                success_probability = min(0.9, 0.4 + org_cohesion * 0.5)
            elif verb in {"attack", "mobilize"}:
                # Aggressive actions — high heat, variable consciousness
                estimated_consciousness_delta = 0.02
                estimated_heat_delta = 0.08 * org_cohesion
                success_probability = min(0.8, 0.3 + org_cohesion * 0.4)
            elif verb in {"aid", "reproduce"}:
                # Organizational building
                estimated_consciousness_delta = 0.01
                estimated_heat_delta = -0.01
                success_probability = min(0.95, 0.5 + org_cohesion * 0.4)
            elif verb in {"investigate", "negotiate", "move"}:
                # Lower-impact actions
                estimated_consciousness_delta = 0.0
                estimated_heat_delta = 0.0
                success_probability = min(0.9, 0.6 + org_cohesion * 0.3)

            # Collect affected territories
            territory_ids = org_data.get("territory_ids", [])
            if isinstance(territory_ids, (list, tuple)):
                affected_territory_ids = list(territory_ids)
            if target_id and target_id not in affected_territory_ids:
                affected_territory_ids.append(target_id)
        else:
            warnings.append(f"Target '{resolved_target}' not found in current state")

        # Apply action type modifier if available
        if action_type_enum is not None:
            action_cost = 1.0  # Could vary by type in future

        return {
            "estimated_consciousness_delta": round(estimated_consciousness_delta, 4),
            "estimated_heat_delta": round(estimated_heat_delta, 4),
            "action_point_cost": action_cost,
            "success_probability": round(success_probability, 4),
            "affected_territory_ids": affected_territory_ids,
            "warnings": warnings,
        }

    def get_pending_actions(self, session_id: UUID, tick: int) -> list[dict[str, Any]]:
        """Return unresolved player actions for a tick.

        Args:
            session_id: The game session UUID.
            tick: The tick to query.

        Returns:
            List of dicts, each representing a pending turn row.
        """
        result: list[dict[str, Any]] = self._persistence.get_pending_turns(  # type: ignore[attr-defined]
            session_id=session_id, tick=tick
        )
        return result


# ---------------------------------------------------------------------- #
# Private helpers
# ---------------------------------------------------------------------- #


def _graph_tick(graph: nx.DiGraph[str]) -> int:
    """Extract the tick from graph-level metadata, defaulting to 0."""
    return int(graph.graph.get("tick", 0))


def _build_initial_state_for_scenario(scenario: str) -> WorldState:
    """Construct initial WorldState for a supported scenario identifier.

    Args:
        scenario: Scenario name from API request.

    Returns:
        Seeded WorldState at tick 0.
    """
    normalized = scenario.strip().lower()
    if normalized in {"default", "us"}:
        state, _config, _defines = create_us_scenario()
        return state
    if normalized == "imperial_circuit":
        state, _config, _defines = create_imperial_circuit_scenario()
        return state
    if normalized == "two_node":
        state, _config, _defines = create_two_node_scenario()
        return state
    if normalized == "labor_aristocracy":
        state, _config, _defines = create_labor_aristocracy_scenario()
        return state
    if normalized in {"wayne_county", "wayne", "detroit"}:
        state, _config, _defines = create_wayne_county_scenario()
        return state

    logger.warning("Unknown scenario '%s', falling back to us", scenario)
    state, _config, _defines = create_us_scenario()
    return state


def _is_unseeded_graph(graph: nx.DiGraph[str]) -> bool:
    """Return True when a hydrated graph has no persisted simulation content."""
    return graph.number_of_nodes() == 0 and graph.number_of_edges() == 0


def _enum_val(obj: object) -> str:
    """Extract .value from an enum or fall back to str()."""
    return obj.value if hasattr(obj, "value") else str(obj)


def _optional_float(value: Any) -> float | None:
    """Coerce a numeric-or-None field to ``float | None`` defensively.

    Postgres ``NULL`` columns surface as ``None`` from psycopg's row
    objects; numeric ``Decimal`` results need an explicit ``float()``.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# Spec 061 US3 FR-012: event severity classification.
# Maps engine EventType strings (the canonical lowercase form) to the
# three-bucket frontend taxonomy. Default for unmapped types is
# "informational" — the safe non-alarming bucket.
_EVENT_SEVERITY: dict[str, str] = {
    # Critical: state-violation / collapse events
    "economic_crisis": "critical",
    "class_decomposition": "critical",
    "superwage_crisis": "critical",
    "imperial_collapse": "critical",
    "uprising": "critical",
    "revolution": "critical",
    "fascist_consolidation": "critical",
    # Warning: threshold-cross / bifurcation events
    "consciousness_bifurcation": "warning",
    "ideology_drift": "warning",
    "heat_threshold": "warning",
    "eviction_pipeline": "warning",
    "repression_event": "warning",
    "trap_activated": "warning",
    "excessive_force": "warning",
    # Informational: routine flow events
    "surplus_extraction": "informational",
    "imperial_subsidy": "informational",
    "wage_payment": "informational",
    "solidarity_transmission": "informational",
}


def _classify_event(event_type_str: str) -> str:
    """Map an event_type to one of {critical, warning, informational}.

    Per spec 061 FR-012. Unrecognized types default to informational so
    the frontend can render them without raising the alarm level.
    """
    return _EVENT_SEVERITY.get(event_type_str.lower(), "informational")


def _humanize_event_type(event_type_str: str) -> str:
    """Convert ``"economic_crisis"`` to ``"Economic Crisis"`` for UI titles."""
    return event_type_str.replace("_", " ").title()


def _serialize_event(event: Any, session_id: UUID) -> dict[str, Any]:
    """Serialize a single :class:`SimulationEvent` for the snapshot.

    Spec 061 US3 (FR-012): every event surfaces ``id``, ``severity``,
    ``title``, and ``body`` fields in addition to the legacy
    ``type``/``tick``/``data`` triple.

    - ``id``: deterministic UUID5 over ``(session_id, tick, event_type,
      data)`` so retries / replays produce identical IDs (Constitution
      III.7 — determinism).
    - ``severity``: one of ``{"critical", "warning", "informational"}``
      via :func:`_classify_event`.
    - ``title``: human-readable variant of ``event_type``.
    - ``body``: a short prose body derived from the event payload.
      Falls back to the empty string when no narrative is available
      (the frontend renders body-less events compactly).
    """
    import json
    import uuid

    event_type_str = _enum_val(event.event_type)
    tick = getattr(event, "tick", 0)
    data: dict[str, Any] = {}
    for attr in ("data", "payload"):
        value = getattr(event, attr, None)
        if isinstance(value, dict):
            data = value
            break
    if not data:
        try:
            data = event.model_dump(exclude={"event_type", "tick", "timestamp"})
        except Exception:  # noqa: BLE001 — defensive
            data = {}

    deterministic_seed = json.dumps(
        {
            "session": str(session_id),
            "tick": tick,
            "event_type": event_type_str,
            "data": data,
        },
        sort_keys=True,
        default=str,
    )
    event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, deterministic_seed))

    narrative = getattr(event, "narrative", None) or ""
    return {
        "id": event_id,
        "type": event_type_str,
        "tick": tick,
        "severity": _classify_event(event_type_str),
        "title": _humanize_event_type(event_type_str),
        "body": narrative,
        "data": data,
    }


def _serialize_entity(e: Any) -> dict[str, Any]:
    """Serialize a SocialClass entity with all visualization-relevant fields."""
    ideology = e.ideology
    return {
        "id": e.id,
        "name": e.name,
        "role": _enum_val(e.role),
        "wealth": float(e.wealth),
        "consciousness": float(ideology.class_consciousness),
        "national_identity": float(ideology.national_identity),
        "agitation": float(ideology.agitation),
        "organization": float(e.organization),
        "repression": float(e.repression_faced),
        "p_acquiescence": float(e.p_acquiescence),
        "p_revolution": float(e.p_revolution),
        "subsistence": float(e.subsistence_threshold),
        "population": e.population,
        "inequality": float(e.inequality),
        "active": e.active,
    }


def _serialize_territory(t: Any) -> dict[str, Any]:
    """Serialize a Territory with all visualization-relevant fields.

    Spec 061 US6 FR-013 (T095): also emits ``consciousness`` /
    ``solidarity`` / ``wealth`` / ``dominant_community`` derived
    aggregates. The engine Territory model does not yet carry these
    directly; defaults are 0.0 / "" until US6-followup persistence
    queries (T095 detailed implementation) land. The frontend can
    distinguish "no data yet" (0.0/"") from "real zero" via the
    presence/absence of dominant_community.
    """
    return {
        "id": t.id,
        "name": t.name,
        "h3_index": t.h3_index,
        "h3_resolution": getattr(t, "h3_resolution", 7),
        "county_fips": getattr(t, "county_fips", ""),
        "heat": float(t.heat),
        "sector_type": _enum_val(t.sector_type),
        "territory_type": _enum_val(t.territory_type),
        "profile": _enum_val(t.profile),
        "rent_level": float(t.rent_level),
        "population": t.population,
        "under_eviction": t.under_eviction,
        "biocapacity": float(t.biocapacity),
        "host_id": t.host_id,
        "occupant_id": t.occupant_id,
        "consciousness": float(getattr(t, "consciousness", 0.0)),
        "solidarity": float(getattr(t, "solidarity", 0.0)),
        "wealth": float(getattr(t, "wealth", 0.0)),
        "dominant_community": str(getattr(t, "dominant_community", "") or ""),
    }


_OODA_PHASE_ORDER: tuple[str, ...] = ("observe", "orient", "decide", "act")


def _derive_ooda_phase(profile: dict[str, float]) -> str:
    """Argmax across the four OODA components → enum string (FR-011).

    Deterministic tiebreak by ``_OODA_PHASE_ORDER`` so the same input
    always produces the same phase across replays (Constitution III.7).
    """
    best_phase = "observe"
    best_value = float("-inf")
    for phase in _OODA_PHASE_ORDER:
        value = float(profile.get(phase, 0.0))
        if value > best_value:
            best_value = value
            best_phase = phase
    return best_phase


def _derive_short_name(name: str) -> str:
    """Truncate ``name`` to ≤16 chars for compact UI surfaces (FR-016)."""
    if not name:
        return ""
    if len(name) <= 16:
        return name
    # Truncate-with-ellipsis for visual signal that more name exists.
    return name[:15] + "…"


def _serialize_organization(o: Any) -> dict[str, Any]:
    """Serialize an Organization with all visualization-relevant fields.

    Spec 061 US4 (T067, T068): adds ``short_name`` / ``player_controlled``
    / ``legitimacy`` / ``opacity`` plus ``ooda.phase`` derived enum.

    Note on ``player_controlled``: the engine model does not yet carry an
    explicit ``controlling_player_id`` linking an Organization to a
    Django auth user. Until that link is added by a follow-up spec, we
    fall back on the existing class_character + org_type heuristic that
    also gates VanguardResources attachment — proletarian civil-society
    orgs are treated as player-controlled.

    For player organizations, computes and attaches VanguardResources
    as the ``vanguard`` field.
    """
    name = str(o.name)
    is_player_org = (
        _enum_val(o.class_character) == "proletarian" and _enum_val(o.org_type) == "civil_society"
    )

    # Spec 061 FR-011: surface OODA phase as a deterministic enum.
    ooda_profile: dict[str, float] = {
        "observe": 0.5,
        "orient": 0.5,
        "decide": 0.5,
        "act": 0.5,
        "cycle_ticks": 4,
    }
    engine_profile = getattr(o, "ooda_profile", None) or getattr(o, "ooda", None)
    if engine_profile is not None:
        for phase in _OODA_PHASE_ORDER:
            value = getattr(engine_profile, phase, None)
            if value is not None:
                ooda_profile[phase] = float(value)
    ooda_phase = _derive_ooda_phase(ooda_profile)

    result: dict[str, Any] = {
        "id": o.id,
        "name": name,
        "short_name": _derive_short_name(name),
        "player_controlled": is_player_org,
        "legitimacy": float(getattr(o, "legitimacy", 0.5)),
        "opacity": float(getattr(o, "opacity", 0.5)),
        "org_type": _enum_val(o.org_type),
        "class_character": _enum_val(o.class_character),
        "cohesion": float(o.cohesion),
        "cadre_level": float(o.cadre_level),
        "budget": float(o.budget),
        "heat": float(o.heat),
        "territory_ids": list(o.territory_ids),
        "consciousness_tendency": _enum_val(o.consciousness_tendency),
        "vanguard": None,
        # Stubs preserved from the prior bridge for Spec 052 schema compat.
        # T069 (hyperedge_memberships from XGI) is left empty until the
        # XGI persistence query lands; the frontend treats empty as
        # "no community memberships known" rather than as an error.
        "hyperedge_memberships": [],
        "consciousness": {"liberal": 0.33, "fascist": 0.33, "revolutionary": 0.34},
        "ooda": {**ooda_profile, "phase": ooda_phase},
    }

    if is_player_org:
        vanguard = VanguardResources.from_organization(
            cadre_level=float(o.cadre_level),
            cohesion=float(o.cohesion),
            budget=float(o.budget),
            heat=float(o.heat),
            territory_count=len(o.territory_ids),
        )
        result["vanguard"] = vanguard.model_dump()

    return result


def _serialize_institution(inst: Any) -> dict[str, Any]:
    """Serialize an Institution with all visualization-relevant fields."""
    balance = inst.internal_balance
    return {
        "id": inst.id,
        "name": inst.name,
        "apparatus_type": _enum_val(inst.apparatus_type),
        "social_function": _enum_val(inst.social_function),
        "class_inscription": _enum_val(inst.class_inscription),
        "legitimacy": float(inst.legitimacy),
        "budget": float(inst.budget),
        "housed_org_ids": list(inst.housed_org_ids),
        "territory_ids": list(inst.territory_ids),
        "factional_composition": {
            "liberal_technocratic": float(balance.liberal_technocratic),
            "revanchist_fascist": float(balance.revanchist_fascist),
            "institutionalist_bonapartist": float(balance.institutionalist_bonapartist),
        },
    }


def _serialize_edge(rel: Any) -> dict[str, Any]:
    """Serialize a Relationship edge.

    Spec 061 US6 FR-014 (T097): also emits ``rate_of_profit`` /
    ``rent_burden`` / ``age_ticks`` when the engine attaches them;
    otherwise emits ``None`` so the frontend can render "n/a".
    Age requires either an engine attribute or an edge_snapshot
    history query (the latter is a US6-followup task; the field
    surfaces as None for now).
    """
    rate_of_profit = getattr(rel, "rate_of_profit", None)
    rent_burden = getattr(rel, "rent_burden", None)
    age_ticks = getattr(rel, "age_ticks", None)
    return {
        "id": f"{rel.source_id}-{rel.target_id}-{_enum_val(rel.edge_type)}",
        "source_id": rel.source_id,
        "target_id": rel.target_id,
        "mode": _enum_val(rel.edge_type),
        "value_flow": float(rel.value_flow),
        "tension": float(rel.tension),
        "repression_flow": float(getattr(rel, "solidarity_strength", 0.0)),
        "rate_of_profit": float(rate_of_profit) if rate_of_profit is not None else None,
        "rent_burden": float(rent_burden) if rent_burden is not None else None,
        "age_ticks": int(age_ticks) if age_ticks is not None else None,
    }


def _state_to_snapshot(state: WorldState, session_id: UUID) -> dict[str, Any]:
    """Convert a WorldState to a JSON-serializable dict for API responses.

    Includes VanguardResources on player orgs and TrapDetection results.

    Args:
        state: The WorldState to serialize.
        session_id: The session UUID to include.

    Returns:
        Flat dict suitable for JSON encoding.
    """
    territories = [_serialize_territory(t) for t in state.territories.values()]
    organizations = [_serialize_organization(o) for o in state.organizations.values()]
    institutions = [_serialize_institution(inst) for inst in state.institutions.values()]
    edges = [_serialize_edge(rel) for rel in state.relationships]
    events_list: list[dict[str, Any]] = [_serialize_event(e, session_id) for e in state.events]

    # Compute trap detection for the session
    traps_dict = _compute_traps(state, session_id)

    snapshot: dict[str, Any] = {
        "session_id": str(session_id),
        "tick": state.tick,
        "organizations": organizations,
        "institutions": institutions,
        "territories": territories,
        "hyperedges": [],
        "edges": edges,
        "events": events_list,
        "derived": {
            "value_tensor": {},
            "imperial_rent": {},
            "dept_iii_visibility": {},
            "class_aggregates": {},
            "economy": state.economy.model_dump() if state.economy else {},
            "predictions": {},
        },
    }

    if traps_dict is not None:
        snapshot["traps"] = traps_dict

    return snapshot


def _compute_traps(state: WorldState, session_id: UUID) -> dict[str, Any] | None:
    """Run trap detection for a session, computing scores from action history.

    Returns None if no player org is found (non-Wayne County scenarios).
    """
    # Find the player org
    player_org = None
    for org in state.organizations.values():
        if (
            _enum_val(org.class_character) == "proletarian"
            and _enum_val(org.org_type) == "civil_society"
        ):
            player_org = org
            break

    if player_org is None:
        return None

    # Compute derived values for trap detection
    history = _session_action_history.get(session_id, [])
    consciousness_avg = sum(
        float(e.ideology.class_consciousness) for e in state.entities.values()
    ) / max(len(state.entities), 1)

    resources = VanguardResources.from_organization(
        cadre_level=float(player_org.cadre_level),
        cohesion=float(player_org.cohesion),
        budget=float(player_org.budget),
        heat=float(player_org.heat),
        territory_count=len(player_org.territory_ids),
    )

    # Count entities trending fascist (national_identity > 0.6)
    fascist_count = sum(
        1 for e in state.entities.values() if float(e.ideology.national_identity) > 0.6
    )

    previous_result = _session_trap_state.get(session_id)

    result = detect_traps(
        action_history=history,
        org_budget=float(player_org.budget),
        org_cadre=float(player_org.cadre_level),
        org_cohesion=float(player_org.cohesion),
        org_heat=float(player_org.heat),
        sympathizer_labor=float(resources.sympathizer_labor),
        territory_count=len(player_org.territory_ids),
        consciousness_avg=consciousness_avg,
        tick=state.tick,
        fascist_entities=fascist_count,
        total_entities=len(state.entities),
        previous_result=previous_result,
    )

    # Persist trap state for next tick
    _session_trap_state[session_id] = result

    return result.model_dump()


def _mark_resolved_safe(persistence: RuntimePersistence, session_id: UUID, tick: int) -> None:
    """Mark turns as resolved if the persistence layer supports it."""
    mark_fn = getattr(persistence, "mark_turns_resolved", None)
    if mark_fn is not None:
        mark_fn(session_id=session_id, tick=tick)


def _persist_action_result(persistence: RuntimePersistence, result_data: dict[str, Any]) -> None:
    """Write an ActionResult record via persistence layer or Django ORM.

    Tries ``persist_action_result()`` on the persistence layer first.
    Falls back to Django ORM ``ActionResult.objects.create()`` if unavailable.

    Args:
        persistence: The RuntimePersistence instance.
        result_data: Dict with ActionResult fields.
    """
    persist_fn = getattr(persistence, "persist_action_result", None)
    if persist_fn is not None:
        persist_fn(**result_data)
    else:
        # Fallback: use Django ORM
        try:
            from game.models import ActionResult

            ActionResult.objects.create(**result_data)
        except Exception as exc:
            logger.warning("Failed to persist action result: %s", exc)


# ---------------------------------------------------------------------- #
# Persistence initialization (called from apps.py to preserve boundary)
# ---------------------------------------------------------------------- #

# Module-level pool reference to keep the connection pool alive
_pool: Any = None


def init_persistence(db_config: dict[str, Any]) -> RuntimePersistence:
    """Create a PostgresRuntime persistence layer from Django DB settings.

    This function encapsulates all engine/persistence imports so that
    ``apps.py`` never imports from ``babylon.*`` directly.

    Args:
        db_config: Django DATABASES["default"] dict with HOST, PORT, etc.

    Returns:
        A RuntimePersistence instance backed by PostgreSQL.
    """
    global _pool  # noqa: PLW0603

    from psycopg_pool import ConnectionPool

    from babylon.persistence.postgres_runtime import PostgresRuntime

    host = str(db_config.get("HOST", "localhost"))
    port = str(db_config.get("PORT", "5432"))
    name = str(db_config.get("NAME", "babylon"))
    user = str(db_config.get("USER", "babylon"))
    password = str(db_config.get("PASSWORD", "babylon"))
    conninfo = f"host={host} port={port} dbname={name} user={user} password={password}"

    _pool = ConnectionPool(conninfo=conninfo, min_size=1, max_size=4, timeout=10)
    persistence = PostgresRuntime(_pool)
    try:
        persistence.init_schema()
    except Exception as exc:
        logger.warning("PostgreSQL schema init had non-fatal error: %s", exc)

    return persistence
