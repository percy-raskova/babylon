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

VERB_TO_ACTION_TYPE: dict[str, ActionType] = {
    "educate": ActionType.EDUCATE,
    "reproduce": ActionType.RECRUIT,
    "investigate": ActionType.MAP_NETWORK,
    "attack": ActionType.ATTACK_INFRASTRUCTURE,
    "mobilize": ActionType.PROTEST,
    "campaign": ActionType.PROPAGANDIZE,
    "aid": ActionType.PROVIDE_SERVICE,
    "move": ActionType.ORGANIZE,
    "negotiate": ActionType.PROPOSE_ALLIANCE,
}

CANONICAL_VERBS: frozenset[str] = frozenset(VERB_TO_ACTION_TYPE.keys())


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
                        "org_presence": state.org_presence,
                        "dominant_class": state.dominant_class,
                        "population": state.population,
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
            pop = state.population or 0
            acc["profit_rate_sum"] += (state.profit_rate or 0) * pop
            acc["exploitation_rate_sum"] += (state.exploitation_rate or 0) * pop
            acc["occ_sum"] += (state.occ or 0) * pop
            acc["imperial_rent_sum"] += state.imperial_rent or 0
            acc["heat_sum"] += (state.heat or 0) * pop
            acc["org_presence_sum"] += state.org_presence or 0
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

        sim_config = SimulationConfig()

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
    """Serialize a Territory with all visualization-relevant fields."""
    return {
        "id": t.id,
        "name": t.name,
        "h3_index": t.h3_index,
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
    }


def _serialize_organization(o: Any) -> dict[str, Any]:
    """Serialize an Organization with all visualization-relevant fields.

    For player organizations (civil_society with proletarian class character),
    computes and attaches VanguardResources as the 'vanguard' field.
    """
    result: dict[str, Any] = {
        "id": o.id,
        "name": o.name,
        "org_type": _enum_val(o.org_type),
        "class_character": _enum_val(o.class_character),
        "cohesion": float(o.cohesion),
        "cadre_level": float(o.cadre_level),
        "budget": float(o.budget),
        "heat": float(o.heat),
        "territory_ids": list(o.territory_ids),
        "consciousness_tendency": _enum_val(o.consciousness_tendency),
        "vanguard": None,
    }

    # Compute vanguard resources for player orgs
    is_player_org = (
        _enum_val(o.class_character) == "proletarian" and _enum_val(o.org_type) == "civil_society"
    )
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
        "hegemonic_fraction": _enum_val(balance.hegemonic_fraction),
        "liberal_technocratic": float(balance.liberal_technocratic),
        "revanchist_fascist": float(balance.revanchist_fascist),
        "institutionalist_bonapartist": float(balance.institutionalist_bonapartist),
    }


def _serialize_edge(rel: Any) -> dict[str, Any]:
    """Serialize a Relationship edge."""
    return {
        "source_id": rel.source_id,
        "target_id": rel.target_id,
        "edge_type": _enum_val(rel.edge_type),
        "value_flow": float(rel.value_flow),
        "tension": float(rel.tension),
        "solidarity_strength": float(rel.solidarity_strength),
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
    entities = [_serialize_entity(e) for e in state.entities.values()]
    territories = [_serialize_territory(t) for t in state.territories.values()]
    organizations = [_serialize_organization(o) for o in state.organizations.values()]
    institutions = [_serialize_institution(inst) for inst in state.institutions.values()]
    edges = [_serialize_edge(rel) for rel in state.relationships]
    events_list: list[dict[str, Any]] = [
        {
            "type": _enum_val(e.event_type),
            "tick": e.tick,
            "data": e.data if hasattr(e, "data") else {},
        }
        for e in state.events
    ]

    # Compute trap detection for the session
    traps_dict = _compute_traps(state, session_id)

    snapshot: dict[str, Any] = {
        "session_id": str(session_id),
        "tick": state.tick,
        "entities": entities,
        "territories": territories,
        "organizations": organizations,
        "institutions": institutions,
        "edges": edges,
        "economy": state.economy.model_dump() if state.economy else {},
        "events": events_list,
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
