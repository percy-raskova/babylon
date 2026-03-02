"""Engine bridge — the sole translation layer between Django and the simulation engine.

This is the **ONLY** file in ``web/`` that imports from ``babylon.engine``,
``babylon.models``, ``babylon.config``, ``babylon.ooda``, or
``babylon.persistence``.  Django views and serializers call this bridge;
they never see engine internals.

All methods return plain Python dicts / lists / scalars that are
JSON-serializable, suitable for DRF serializer consumption.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import networkx as nx

from babylon.config.defines import GameDefines
from babylon.engine.simulation_engine import step
from babylon.models.config import SimulationConfig
from babylon.models.world_state import WorldState
from babylon.ooda.npc_stub import select_npc_actions
from babylon.persistence.protocols import RuntimePersistence


class EngineBridge:
    """Translates between Django request/response and simulation engine.

    Holds a reference to the persistence layer and provides methods
    that orchestrate create → hydrate → step → persist → snapshot cycles.
    """

    def __init__(self, persistence: RuntimePersistence) -> None:
        self._persistence = persistence

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

    # ------------------------------------------------------------------ #
    # Tick resolution
    # ------------------------------------------------------------------ #

    def resolve_tick(
        self,
        session_id: UUID,
        persistent_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Advance the simulation one tick: hydrate → step → persist → snapshot.

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

        # Step the engine
        new_state = step(
            state,
            sim_config,
            persistent_context=persistent_context,
            defines=game_defines,
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

        # Mark submitted turns as resolved
        _mark_resolved_safe(self._persistence, session_id, state.tick)

        return _state_to_snapshot(new_state, session_id)

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
        """
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


def _state_to_snapshot(state: WorldState, session_id: UUID) -> dict[str, Any]:
    """Convert a WorldState to a JSON-serializable dict for API responses.

    Args:
        state: The WorldState to serialize.
        session_id: The session UUID to include.

    Returns:
        Flat dict suitable for JSON encoding.
    """
    entities: list[dict[str, Any]] = [
        {"id": e.id, "name": e.name, "role": e.role.value, "wealth": float(e.wealth)}
        for e in state.entities.values()
    ]
    territories: list[dict[str, Any]] = [
        {
            "id": t.id,
            "name": t.name,
            "heat": float(t.heat),
            "sector_type": t.sector_type.value
            if hasattr(t.sector_type, "value")
            else str(t.sector_type),
        }
        for t in state.territories.values()
    ]
    organizations: list[dict[str, Any]] = [
        {
            "id": o.id,
            "name": o.name,
            "org_type": o.org_type.value if hasattr(o.org_type, "value") else str(o.org_type),
        }
        for o in state.organizations.values()
    ]
    institutions: list[dict[str, Any]] = [
        {
            "id": inst.id,
            "name": inst.name,
            "apparatus_type": inst.apparatus_type.value
            if hasattr(inst.apparatus_type, "value")
            else str(inst.apparatus_type),
        }
        for inst in state.institutions.values()
    ]
    events_list: list[dict[str, Any]] = [
        {
            "type": e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type),
            "tick": e.tick,
            "data": e.data if hasattr(e, "data") else {},
        }
        for e in state.events
    ]

    return {
        "session_id": str(session_id),
        "tick": state.tick,
        "entities": entities,
        "territories": territories,
        "organizations": organizations,
        "institutions": institutions,
        "economy": state.economy.model_dump() if state.economy else {},
        "events": events_list,
    }


def _mark_resolved_safe(persistence: RuntimePersistence, session_id: UUID, tick: int) -> None:
    """Mark turns as resolved if the persistence layer supports it."""
    mark_fn = getattr(persistence, "mark_turns_resolved", None)
    if mark_fn is not None:
        mark_fn(session_id=session_id, tick=tick)
