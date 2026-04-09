"""PostgreSQL runtime database for simulation state persistence (Feature 037).

Implements ``RuntimePersistence`` and ``PostgresRuntimeExtensions`` protocols
using psycopg 3 for bulk writes. Designed for high-throughput tick persistence
with UPSERT semantics and session-scoped data isolation.

Usage::

    from psycopg_pool import ConnectionPool
    from babylon.persistence.postgres_runtime import PostgresRuntime

    pool = ConnectionPool(conninfo="dbname=babylon")
    with PostgresRuntime(pool) as pg:
        pg.persist_tick(tick=0, graph=graph, session_id=session_id)
        loaded = pg.hydrate_graph(tick=0, session_id=session_id)
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID

import networkx as nx
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from babylon.persistence.postgres_schema import (
    POSTGRES_SCHEMA_DDL,
    TRACE_PARTITION_CREATE_TEMPLATE,
    TRACE_PARTITION_DROP_TEMPLATE,
)

logger = logging.getLogger(__name__)

# Maximum rows per executemany batch
_BATCH_SIZE = 1000


def _json_default(obj: object) -> str:
    """Fallback serializer for ``json.dumps`` — handles datetime/date/UUID."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class PostgresRuntime:
    """PostgreSQL persistence backend for the simulation engine.

    Implements both ``RuntimePersistence`` and ``PostgresRuntimeExtensions``.
    Uses connection pooling via psycopg-pool for concurrent session support.

    Attributes:
        pool: The psycopg ConnectionPool instance.
    """

    def __init__(self, pool: ConnectionPool[Connection[Any]]) -> None:
        self._pool = pool

    @property
    def pool(self) -> ConnectionPool[Connection[Any]]:
        """The underlying connection pool."""
        return self._pool

    def init_schema(self) -> None:
        """Execute all DDL statements to create/verify schema.

        Safe to call multiple times (uses IF NOT EXISTS).
        """
        with self._pool.connection() as conn:
            conn.autocommit = True
            for ddl in POSTGRES_SCHEMA_DDL:
                conn.execute(ddl)
        logger.info("PostgreSQL schema initialized (%d statements)", len(POSTGRES_SCHEMA_DDL))

    def close(self) -> None:
        """Close the connection pool."""
        self._pool.close()

    def __enter__(self) -> PostgresRuntime:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.close()

    # ─── RuntimePersistence ─────────────────────────────────────────

    def persist_tick(
        self,
        tick: int,
        graph: nx.DiGraph[str],
        events: list[dict[str, Any]] | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None:
        """Persist a complete state snapshot at the given tick.

        Args:
            tick: The tick number.
            graph: Full simulation graph.
            events: Optional simulation events.
            session_id: Required session scope.
        """
        if session_id is None:
            msg = "session_id is required for PostgresRuntime.persist_tick"
            raise ValueError(msg)

        with self._pool.connection() as conn, conn.transaction():
            self._persist_nodes(conn, session_id, tick, graph)
            self._persist_edges(conn, session_id, tick, graph)
            if events:
                self._persist_events(conn, session_id, tick, events)

    def hydrate_graph(
        self,
        tick: int | None = None,
        *,
        session_id: UUID | None = None,
    ) -> nx.DiGraph[str]:
        """Load a complete state snapshot from storage.

        Args:
            tick: Tick to load, or None for latest.
            session_id: Required session scope.

        Returns:
            Fully populated NetworkX DiGraph.
        """
        if session_id is None:
            msg = "session_id is required for PostgresRuntime.hydrate_graph"
            raise ValueError(msg)

        graph: nx.DiGraph[str] = nx.DiGraph()

        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            # Determine tick
            if tick is None:
                cur.execute(
                    "SELECT MAX(tick) AS max_tick FROM node_state WHERE session_id = %s",
                    (session_id,),
                )
                result = cur.fetchone()
                if result is None or result["max_tick"] is None:
                    return graph
                tick = result["max_tick"]

            # Load nodes
            cur.execute(
                "SELECT node_id, node_type, attributes FROM node_state "
                "WHERE session_id = %s AND tick = %s",
                (session_id, tick),
            )
            for row in cur.fetchall():
                attrs = row["attributes"] if isinstance(row["attributes"], dict) else {}
                attrs["_node_type"] = row["node_type"]
                graph.add_node(row["node_id"], **attrs)

            # Load edges
            cur.execute(
                "SELECT source_id, target_id, edge_type, attributes FROM edge_state "
                "WHERE session_id = %s AND tick = %s",
                (session_id, tick),
            )
            for row in cur.fetchall():
                attrs = row["attributes"] if isinstance(row["attributes"], dict) else {}
                attrs["edge_type"] = row["edge_type"]
                graph.add_edge(row["source_id"], row["target_id"], **attrs)

        return graph

    def log_tick(
        self,
        tick: int,
        rng_state: bytes | None = None,
        mutations: dict[str, Any] | None = None,
        invariant_checks: dict[str, bool] | None = None,
        wall_time_ms: int | None = None,
        system_timings: dict[str, int] | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None:
        """Record tick replay metadata.

        Args:
            tick: The tick number.
            rng_state: Serialized RNG state.
            mutations: Mutation summary.
            invariant_checks: Conservation checks.
            wall_time_ms: Total tick wall time.
            system_timings: Per-system timing.
            session_id: Required session scope.
        """
        if session_id is None:
            msg = "session_id is required for PostgresRuntime.log_tick"
            raise ValueError(msg)

        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO tick_log
                    (session_id, tick, rng_state, mutations_json, invariant_checks,
                     system_timings, wall_time_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, tick) DO UPDATE SET
                    rng_state = EXCLUDED.rng_state,
                    mutations_json = EXCLUDED.mutations_json,
                    invariant_checks = EXCLUDED.invariant_checks,
                    system_timings = EXCLUDED.system_timings,
                    wall_time_ms = EXCLUDED.wall_time_ms
                """,
                (
                    session_id,
                    tick,
                    rng_state,
                    json.dumps(mutations) if mutations else None,
                    json.dumps(invariant_checks) if invariant_checks else None,
                    json.dumps(system_timings) if system_timings else None,
                    wall_time_ms,
                ),
            )

    def set_metadata(self, key: str, value: str) -> None:
        """Store a key-value metadata pair.

        Uses a sentinel session row in tick_log at tick=-1 to store metadata
        as a JSONB dict, accumulating key-value pairs.

        Args:
            key: Metadata key.
            value: Metadata value.
        """
        _sentinel = UUID("00000000-0000-0000-0000-000000000000")
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO tick_log (session_id, tick, mutations_json)
                VALUES (%s, -1, %s)
                ON CONFLICT (session_id, tick) DO UPDATE SET
                    mutations_json = tick_log.mutations_json || EXCLUDED.mutations_json
                """,
                (_sentinel, json.dumps({key: value})),
            )

    def get_metadata(self, key: str) -> str | None:
        """Retrieve a metadata value by key.

        Args:
            key: Metadata key.

        Returns:
            The stored value, or None if not found.
        """
        _sentinel = UUID("00000000-0000-0000-0000-000000000000")
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT mutations_json FROM tick_log WHERE session_id = %s AND tick = -1",
                (_sentinel,),
            )
            result = cur.fetchone()
            if result is None or result["mutations_json"] is None:
                return None
            data = result["mutations_json"]
            if isinstance(data, str):
                data = json.loads(data)
            val = data.get(key)
            return str(val) if val is not None else None

    # ─── PostgresRuntimeExtensions ──────────────────────────────────

    def persist_graph_metadata(
        self,
        tick: int,
        economy: dict[str, Any],
        state_finances: dict[str, Any],
        tick_dynamics: dict[str, Any] | None,
        *,
        session_id: UUID,
    ) -> None:
        """Persist graph-level metadata."""
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO graph_metadata (session_id, tick, economy, state_finances, tick_dynamics)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (session_id, tick) DO UPDATE SET
                    economy = EXCLUDED.economy,
                    state_finances = EXCLUDED.state_finances,
                    tick_dynamics = EXCLUDED.tick_dynamics
                """,
                (
                    session_id,
                    tick,
                    json.dumps(economy),
                    json.dumps(state_finances),
                    json.dumps(tick_dynamics) if tick_dynamics else None,
                ),
            )

    def persist_community_state(
        self,
        tick: int,
        community_states: dict[str, Any],
        memberships: list[dict[str, Any]],
        *,
        session_id: UUID,
    ) -> None:
        """Persist community state and membership records."""
        with self._pool.connection() as conn, conn.transaction(), conn.cursor() as cur:
            for ctype, state in community_states.items():
                cur.execute(
                    """
                        INSERT INTO community_state
                            (session_id, tick, community_type, category, heat, cohesion,
                             infrastructure, visibility, legal_status,
                             reproduction_cost_modifier, rent_access_modifier,
                             r, l, f,
                             collective_identity, dominant_tendency,
                             ideological_contestation, infiltration_resistance)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (session_id, tick, community_type) DO UPDATE SET
                            category = EXCLUDED.category,
                            heat = EXCLUDED.heat,
                            cohesion = EXCLUDED.cohesion,
                            infrastructure = EXCLUDED.infrastructure,
                            visibility = EXCLUDED.visibility,
                            legal_status = EXCLUDED.legal_status,
                            reproduction_cost_modifier = EXCLUDED.reproduction_cost_modifier,
                            rent_access_modifier = EXCLUDED.rent_access_modifier,
                            r = EXCLUDED.r,
                            l = EXCLUDED.l,
                            f = EXCLUDED.f,
                            collective_identity = EXCLUDED.collective_identity,
                            dominant_tendency = EXCLUDED.dominant_tendency,
                            ideological_contestation = EXCLUDED.ideological_contestation,
                            infiltration_resistance = EXCLUDED.infiltration_resistance
                        """,
                    (
                        session_id,
                        tick,
                        ctype,
                        state.get("category", "UNKNOWN"),
                        state.get("heat", 0.0),
                        state.get("cohesion", 0.0),
                        state.get("infrastructure", 0.0),
                        state.get("visibility", 0.0),
                        state.get("legal_status", "LEGAL"),
                        state.get("reproduction_cost_modifier", 1.0),
                        state.get("rent_access_modifier", 1.0),
                        state.get("r", 0.3),
                        state.get("l", 0.6),
                        state.get("f", 0.1),
                        state.get("collective_identity", 0.0),
                        state.get("dominant_tendency", "NEUTRAL"),
                        state.get("ideological_contestation", 0.0),
                        state.get("infiltration_resistance"),
                    ),
                )

            if memberships:
                cur.executemany(
                    """
                        INSERT INTO community_membership
                            (session_id, tick, agent_id, community_type, role,
                             strength, visibility, overt)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (session_id, tick, agent_id, community_type) DO UPDATE SET
                            role = EXCLUDED.role, strength = EXCLUDED.strength,
                            visibility = EXCLUDED.visibility, overt = EXCLUDED.overt
                        """,
                    [
                        (
                            session_id,
                            tick,
                            m["agent_id"],
                            m["community_type"],
                            m.get("role", "MEMBER"),
                            m.get("strength", 1.0),
                            m.get("visibility", 0.0),
                            m.get("overt", True),
                        )
                        for m in memberships
                    ],
                )

    def hydrate_community_state(
        self,
        tick: int,
        *,
        session_id: UUID,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Load community state and memberships at a specific tick."""
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM community_state WHERE session_id = %s AND tick = %s",
                (session_id, tick),
            )
            community_states: dict[str, Any] = {}
            for row in cur.fetchall():
                ctype = row.pop("community_type")
                row.pop("session_id", None)
                row.pop("tick", None)
                community_states[ctype] = dict(row)

            cur.execute(
                "SELECT * FROM community_membership WHERE session_id = %s AND tick = %s",
                (session_id, tick),
            )
            memberships = [dict(row) for row in cur.fetchall()]

        return community_states, memberships

    def persist_hex_state(
        self,
        tick: int,
        hex_states: list[dict[str, Any]],
        *,
        session_id: UUID,
    ) -> None:
        """Persist per-hex economic state via bulk insert."""
        if not hex_states:
            return

        with self._pool.connection() as conn, conn.cursor() as cur:
            for i in range(0, len(hex_states), _BATCH_SIZE):
                batch = hex_states[i : i + _BATCH_SIZE]
                cur.executemany(
                    """
                        INSERT INTO hex_state
                            (session_id, tick, h3_index, constant_capital, variable_capital,
                             surplus_value, employment, dept_shares, profit_rate, exploitation_rate)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (session_id, tick, h3_index) DO UPDATE SET
                            constant_capital = EXCLUDED.constant_capital,
                            variable_capital = EXCLUDED.variable_capital,
                            surplus_value = EXCLUDED.surplus_value,
                            employment = EXCLUDED.employment, dept_shares = EXCLUDED.dept_shares,
                            profit_rate = EXCLUDED.profit_rate,
                            exploitation_rate = EXCLUDED.exploitation_rate
                        """,
                    [
                        (
                            session_id,
                            tick,
                            h["h3_index"],
                            h.get("constant_capital", 0),
                            h.get("variable_capital", 0),
                            h.get("surplus_value", 0),
                            h.get("employment", 0),
                            h.get("dept_shares", [0, 0, 0, 0]),
                            h.get("profit_rate", 0),
                            h.get("exploitation_rate", 0),
                        )
                        for h in batch
                    ],
                )

    def persist_infrastructure_state(
        self,
        tick: int,
        terrain_states: list[dict[str, Any]],
        link_states: list[dict[str, Any]],
        *,
        session_id: UUID,
    ) -> None:
        """Persist infrastructure topology state."""
        with self._pool.connection() as conn, conn.transaction(), conn.cursor() as cur:
            if terrain_states:
                cur.executemany(
                    """
                        INSERT INTO hex_terrain_state
                            (session_id, tick, h3_index, terrain_type, water_coverage,
                             resource_coverage, biocapacity_stocks, internet_access,
                             internet_quality, surveillance_coupling, response_mode)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (session_id, tick, h3_index) DO UPDATE SET
                            terrain_type = EXCLUDED.terrain_type,
                            water_coverage = EXCLUDED.water_coverage,
                            resource_coverage = EXCLUDED.resource_coverage,
                            biocapacity_stocks = EXCLUDED.biocapacity_stocks,
                            internet_access = EXCLUDED.internet_access,
                            internet_quality = EXCLUDED.internet_quality,
                            surveillance_coupling = EXCLUDED.surveillance_coupling,
                            response_mode = EXCLUDED.response_mode
                        """,
                    [
                        (
                            session_id,
                            tick,
                            t["h3_index"],
                            t.get("terrain_type", "LAND"),
                            t.get("water_coverage", 0.0),
                            t.get("resource_coverage", 0.0),
                            json.dumps(t.get("biocapacity_stocks", {})),
                            t.get("internet_access", False),
                            t.get("internet_quality", 0.0),
                            t.get("surveillance_coupling", 0.0),
                            t.get("response_mode", "PERMIT"),
                        )
                        for t in terrain_states
                    ],
                )

            if link_states:
                cur.executemany(
                    """
                        INSERT INTO infrastructure_link_state
                            (session_id, tick, source_h3, target_h3, link_id,
                             infra_type, capacity, condition, owner_org_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (session_id, tick, link_id) DO UPDATE SET
                            source_h3 = EXCLUDED.source_h3, target_h3 = EXCLUDED.target_h3,
                            infra_type = EXCLUDED.infra_type, capacity = EXCLUDED.capacity,
                            condition = EXCLUDED.condition, owner_org_id = EXCLUDED.owner_org_id
                        """,
                    [
                        (
                            session_id,
                            tick,
                            ls["source_h3"],
                            ls["target_h3"],
                            ls["link_id"],
                            ls["infra_type"],
                            json.dumps(ls.get("capacity", {})),
                            ls.get("condition", 1.0),
                            ls.get("owner_org_id"),
                        )
                        for ls in link_states
                    ],
                )

    def persist_contradiction_fields(
        self,
        tick: int,
        fields: list[dict[str, Any]],
        curvatures: list[dict[str, Any]],
        *,
        session_id: UUID,
    ) -> None:
        """Persist contradiction field values and edge curvatures."""
        with self._pool.connection() as conn, conn.transaction(), conn.cursor() as cur:
            if fields:
                cur.executemany(
                    """
                        INSERT INTO contradiction_field
                            (session_id, tick, node_id, field_name, value,
                             laplacian, dt, d2t)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (session_id, tick, node_id, field_name) DO UPDATE SET
                            value = EXCLUDED.value, laplacian = EXCLUDED.laplacian,
                            dt = EXCLUDED.dt, d2t = EXCLUDED.d2t
                        """,
                    [
                        (
                            session_id,
                            tick,
                            f["node_id"],
                            f["field_name"],
                            f["value"],
                            f.get("laplacian"),
                            f.get("dt"),
                            f.get("d2t"),
                        )
                        for f in fields
                    ],
                )

            if curvatures:
                cur.executemany(
                    """
                        INSERT INTO edge_curvature
                            (session_id, tick, source_id, target_id, curvature, gradient)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (session_id, tick, source_id, target_id) DO UPDATE SET
                            curvature = EXCLUDED.curvature, gradient = EXCLUDED.gradient
                        """,
                    [
                        (
                            session_id,
                            tick,
                            c["source_id"],
                            c["target_id"],
                            c["curvature"],
                            json.dumps(c.get("gradient")) if c.get("gradient") else None,
                        )
                        for c in curvatures
                    ],
                )

    def persist_action_results(
        self,
        tick: int,
        results: list[dict[str, Any]],
        *,
        session_id: UUID,
    ) -> None:
        """Persist OODA action resolution outcomes."""
        if not results:
            return

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                    INSERT INTO action_result
                        (session_id, tick, org_id, action_type, target_id,
                         target_community, initiative_score, action_cost, success,
                         consciousness_delta, heat_delta, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                [
                    (
                        session_id,
                        tick,
                        r["org_id"],
                        r["action_type"],
                        r.get("target_id"),
                        r.get("target_community"),
                        r["initiative_score"],
                        r["action_cost"],
                        r["success"],
                        r.get("consciousness_delta"),
                        r.get("heat_delta"),
                        json.dumps(r.get("details")) if r.get("details") else None,
                    )
                    for r in results
                ],
            )

    def persist_tick_summary(
        self,
        tick: int,
        summary: dict[str, Any],
        *,
        session_id: UUID,
    ) -> None:
        """Persist pre-aggregated tick summary."""
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO tick_summary
                    (session_id, tick, year, total_c, total_v, total_s,
                     exploitation_rate, profit_rate, imperial_rent,
                     avg_consciousness, solidarity_edge_count,
                     antagonistic_edge_count, co_optive_edge_count,
                     org_count, player_org_count, uprising_count,
                     repression_count, conservation_check)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, tick) DO UPDATE SET
                    year = EXCLUDED.year, total_c = EXCLUDED.total_c,
                    total_v = EXCLUDED.total_v, total_s = EXCLUDED.total_s,
                    exploitation_rate = EXCLUDED.exploitation_rate,
                    profit_rate = EXCLUDED.profit_rate,
                    imperial_rent = EXCLUDED.imperial_rent,
                    avg_consciousness = EXCLUDED.avg_consciousness,
                    solidarity_edge_count = EXCLUDED.solidarity_edge_count,
                    antagonistic_edge_count = EXCLUDED.antagonistic_edge_count,
                    co_optive_edge_count = EXCLUDED.co_optive_edge_count,
                    org_count = EXCLUDED.org_count,
                    player_org_count = EXCLUDED.player_org_count,
                    uprising_count = EXCLUDED.uprising_count,
                    repression_count = EXCLUDED.repression_count,
                    conservation_check = EXCLUDED.conservation_check
                """,
                (
                    session_id,
                    tick,
                    summary.get("year"),
                    summary.get("total_c"),
                    summary.get("total_v"),
                    summary.get("total_s"),
                    summary.get("exploitation_rate"),
                    summary.get("profit_rate"),
                    summary.get("imperial_rent"),
                    summary.get("avg_consciousness"),
                    summary.get("solidarity_edge_count"),
                    summary.get("antagonistic_edge_count"),
                    summary.get("co_optive_edge_count"),
                    summary.get("org_count"),
                    summary.get("player_org_count"),
                    summary.get("uprising_count"),
                    summary.get("repression_count"),
                    summary.get("conservation_check"),
                ),
            )

    def persist_traces(
        self,
        session_id: UUID,
        tick: int,
        trace_events: list[dict[str, Any]],
    ) -> None:
        """Bulk insert trace events to trace_log."""
        if not trace_events:
            return

        with self._pool.connection() as conn, conn.cursor() as cur:
            for i in range(0, len(trace_events), _BATCH_SIZE):
                batch = trace_events[i : i + _BATCH_SIZE]
                cur.executemany(
                    """
                        INSERT INTO trace_log
                            (session_id, tick, system_name, level, event, node_id, data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                    [
                        (
                            session_id,
                            tick,
                            t["system"],
                            t.get("level", "DEBUG"),
                            t["event"],
                            t.get("node_id"),
                            json.dumps(t.get("data", {})),
                        )
                        for t in batch
                    ],
                )

    def create_session_partition(self, session_id: UUID) -> None:
        """Create a trace_log partition for a new session."""
        session_hex = session_id.hex
        ddl = TRACE_PARTITION_CREATE_TEMPLATE.format(
            session_hex=session_hex,
            session_id=session_id,
        )
        with self._pool.connection() as conn:
            conn.autocommit = True
            conn.execute(ddl)
        logger.info("Created trace partition for session %s", session_id)

    def drop_session_partition(self, session_id: UUID) -> None:
        """Drop a trace_log partition for a completed session."""
        session_hex = session_id.hex
        ddl = TRACE_PARTITION_DROP_TEMPLATE.format(session_hex=session_hex)
        with self._pool.connection() as conn:
            conn.autocommit = True
            conn.execute(ddl)
        logger.info("Dropped trace partition for session %s", session_id)

    def export_session_to_parquet(
        self,
        session_id: UUID,
        output_dir: str,
    ) -> list[str]:
        """Export all session data to Parquet files.

        Args:
            session_id: Session to export.
            output_dir: Directory for output.

        Returns:
            List of generated Parquet file paths.

        Raises:
            ImportError: If archival module is not yet available.
        """
        # Deferred to Phase 8 (archival.py) - import at call time
        from babylon.persistence import archival

        result: list[str] = archival.export_session_to_parquet(
            self._pool,
            session_id,
            output_dir,
        )
        return result

    # ─── Session Management ─────────────────────────────────────────

    def create_session(
        self,
        scenario: str,
        config_json: dict[str, Any],
        game_defines_json: dict[str, Any],
        rng_seed: int,
        *,
        trace_level: str = "NONE",
        player_id: int | None = None,
    ) -> UUID:
        """Create a new game session.

        Args:
            scenario: Scenario factory name.
            config_json: SimulationConfig.model_dump().
            game_defines_json: GameDefines.model_dump().
            rng_seed: RNG seed for deterministic replay.
            trace_level: Trace verbosity level.
            player_id: Optional player ID.

        Returns:
            The UUID of the created session.
        """
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                    INSERT INTO game_session
                        (scenario, config_json, game_defines_json, rng_seed,
                         trace_level, player_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                (
                    scenario,
                    json.dumps(config_json),
                    json.dumps(game_defines_json),
                    rng_seed,
                    trace_level,
                    player_id,
                ),
            )
            result = cur.fetchone()
            if result is None:
                msg = "Failed to create game session"
                raise RuntimeError(msg)
            session_id: UUID = result["id"]

        if trace_level != "NONE":
            self.create_session_partition(session_id)

        return session_id

    def get_session(self, session_id: UUID) -> dict[str, Any] | None:
        """Retrieve session details."""
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM game_session WHERE id = %s", (session_id,))
            result = cur.fetchone()
            return dict(result) if result else None

    def update_session_status(self, session_id: UUID, status: str) -> None:
        """Update session status."""
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE game_session SET status = %s, updated_at = now() WHERE id = %s",
                (status, session_id),
            )

    def get_active_sessions(self) -> list[dict[str, Any]]:
        """Retrieve all active sessions."""
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM game_session WHERE status = 'active' ORDER BY created_at DESC",
            )
            return [dict(row) for row in cur.fetchall()]

    # ─── Turn Management ────────────────────────────────────────────

    def submit_turn(
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
        """Submit a player turn.

        Returns:
            The turn ID.

        Raises:
            psycopg.errors.UniqueViolation: If duplicate (session_id, tick, org_id).
        """
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                    INSERT INTO game_turn
                        (session_id, tick, org_id, verb, action_type,
                         target_id, target_community, params_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                (
                    session_id,
                    tick,
                    org_id,
                    verb,
                    action_type,
                    target_id,
                    target_community,
                    json.dumps(params_json) if params_json else None,
                ),
            )
            result = cur.fetchone()
            if result is None:
                msg = "Failed to submit turn"
                raise RuntimeError(msg)
            turn_id: int = result["id"]
            return turn_id

    def get_pending_turns(
        self,
        session_id: UUID,
        tick: int,
    ) -> list[dict[str, Any]]:
        """Get unresolved turns for a tick."""
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                    SELECT * FROM game_turn
                    WHERE session_id = %s AND tick = %s AND resolved = FALSE
                    ORDER BY submitted_at
                    """,
                (session_id, tick),
            )
            return [dict(row) for row in cur.fetchall()]

    def mark_turns_resolved(self, session_id: UUID, tick: int) -> int:
        """Mark all turns for a tick as resolved.

        Returns:
            Number of turns marked resolved.
        """
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                    UPDATE game_turn SET resolved = TRUE
                    WHERE session_id = %s AND tick = %s AND resolved = FALSE
                    """,
                (session_id, tick),
            )
            count: int = cur.rowcount
            return count

    # ─── Spatial Queries ────────────────────────────────────────────

    def populate_hex_cells(self, hex_cells: list[dict[str, Any]]) -> int:
        """Bulk insert static hex cell reference data.

        Returns:
            Number of rows inserted.
        """
        if not hex_cells:
            return 0

        with self._pool.connection() as conn, conn.cursor() as cur:
            for i in range(0, len(hex_cells), _BATCH_SIZE):
                batch = hex_cells[i : i + _BATCH_SIZE]
                cur.executemany(
                    """
                        INSERT INTO hex_cell
                            (h3_index, county_fips, res6_parent, res5_parent,
                             geometry, centroid)
                        VALUES (
                            %s, %s, %s, %s,
                            ST_GeomFromText(%s, 4326),
                            ST_GeomFromText(%s, 4326)
                        )
                        ON CONFLICT (h3_index) DO NOTHING
                        """,
                    [
                        (
                            h["h3_index"],
                            h["county_fips"],
                            h["res6_parent"],
                            h["res5_parent"],
                            h["geometry_wkt"],
                            h["centroid_wkt"],
                        )
                        for h in batch
                    ],
                )
        return len(hex_cells)

    def get_hex_state_for_tick(
        self,
        session_id: UUID,
        tick: int,
        *,
        county_fips: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get hex economic state for a tick, optionally filtered by county."""
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            if county_fips:
                cur.execute(
                    """
                        SELECT hs.* FROM hex_state hs
                        JOIN hex_cell hc ON hs.h3_index = hc.h3_index
                        WHERE hs.session_id = %s AND hs.tick = %s AND hc.county_fips = %s
                        """,
                    (session_id, tick, county_fips),
                )
            else:
                cur.execute(
                    "SELECT * FROM hex_state WHERE session_id = %s AND tick = %s",
                    (session_id, tick),
                )
            return [dict(row) for row in cur.fetchall()]

    def get_hex_time_series(
        self,
        session_id: UUID,
        h3_index: str,
        *,
        tick_start: int = 0,
        tick_end: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get hex state time series across ticks."""
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            if tick_end is not None:
                cur.execute(
                    """
                        SELECT * FROM hex_state
                        WHERE session_id = %s AND h3_index = %s
                            AND tick >= %s AND tick <= %s
                        ORDER BY tick
                        """,
                    (session_id, h3_index, tick_start, tick_end),
                )
            else:
                cur.execute(
                    """
                        SELECT * FROM hex_state
                        WHERE session_id = %s AND h3_index = %s AND tick >= %s
                        ORDER BY tick
                        """,
                    (session_id, h3_index, tick_start),
                )
            return [dict(row) for row in cur.fetchall()]

    # ─── Spec 037: Game-Journal Persistence ─────────────────────────

    def populate_hex_map(
        self,
        game_id: UUID,
        hex_rows: list[dict[str, Any]],
    ) -> int:
        """Bulk insert static hex_map rows for a game. Written once at init.

        Args:
            game_id: Game session UUID.
            hex_rows: Dicts with h3_index, county_fips, county_name,
                state_fips, center_lat, center_lng, and optional geom_wkt.

        Returns:
            Number of rows inserted.
        """
        if not hex_rows:
            return 0

        with self._pool.connection() as conn, conn.cursor() as cur:
            for i in range(0, len(hex_rows), _BATCH_SIZE):
                batch = hex_rows[i : i + _BATCH_SIZE]
                cur.executemany(
                    """
                    INSERT INTO hex_map
                        (game_id, h3_index, county_fips, county_name,
                         state_fips, h3_resolution, center_lat, center_lng, geom)
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        ST_GeomFromText(%s, 4326)
                    )
                    ON CONFLICT (game_id, h3_index) DO NOTHING
                    """,
                    [
                        (
                            game_id,
                            h["h3_index"],
                            h["county_fips"],
                            h["county_name"],
                            h["state_fips"],
                            h.get("h3_resolution", 7),
                            h["center_lat"],
                            h["center_lng"],
                            h.get("geom_wkt"),
                        )
                        for h in batch
                    ],
                )
        return len(hex_rows)

    def persist_game_defines(
        self,
        game_id: UUID,
        defines: dict[str, Any],
    ) -> None:
        """Freeze GameDefines for a game session. Written once at init.

        Args:
            game_id: Game session UUID.
            defines: GameDefines.model_dump().
        """
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO game_defines_snapshot (game_id, defines)
                VALUES (%s, %s)
                ON CONFLICT (game_id) DO UPDATE SET defines = EXCLUDED.defines
                """,
                (game_id, json.dumps(defines, default=_json_default)),
            )

    def persist_territory_snapshots(
        self,
        game_id: UUID,
        tick: int,
        territories: list[dict[str, Any]],
    ) -> None:
        """Bulk INSERT territory_snapshot rows for one tick.

        Args:
            game_id: Game session UUID.
            tick: Tick number.
            territories: List of territory dicts (one per county per tick).
        """
        if not territories:
            return

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO territory_snapshot
                    (game_id, tick, county_fips,
                     c_dept_i, v_dept_i, s_dept_i,
                     c_dept_iia, v_dept_iia, s_dept_iia,
                     c_dept_iib, v_dept_iib, s_dept_iib,
                     c_dept_iii, v_dept_iii, s_dept_iii,
                     profit_rate, exploitation_rate, occ,
                     imperial_rent, g33_visibility,
                     pop_bourgeoisie, pop_petit_bourgeoisie,
                     pop_labor_aristocracy, pop_proletariat,
                     pop_lumpenproletariat, pop_total,
                     faction_finance_capital, faction_security_state,
                     faction_settler_populist, heat, attributes)
                VALUES (%s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s)
                """,
                [
                    (
                        game_id,
                        tick,
                        t["county_fips"],
                        t.get("c_dept_i"),
                        t.get("v_dept_i"),
                        t.get("s_dept_i"),
                        t.get("c_dept_iia"),
                        t.get("v_dept_iia"),
                        t.get("s_dept_iia"),
                        t.get("c_dept_iib"),
                        t.get("v_dept_iib"),
                        t.get("s_dept_iib"),
                        t.get("c_dept_iii"),
                        t.get("v_dept_iii"),
                        t.get("s_dept_iii"),
                        t.get("profit_rate"),
                        t.get("exploitation_rate"),
                        t.get("occ"),
                        t.get("imperial_rent"),
                        t.get("g33_visibility"),
                        t.get("pop_bourgeoisie", 0),
                        t.get("pop_petit_bourgeoisie", 0),
                        t.get("pop_labor_aristocracy", 0),
                        t.get("pop_proletariat", 0),
                        t.get("pop_lumpenproletariat", 0),
                        t.get("pop_total", 0),
                        t.get("faction_finance_capital"),
                        t.get("faction_security_state"),
                        t.get("faction_settler_populist"),
                        t.get("heat", 0.0),
                        json.dumps(t.get("attributes", {}), default=_json_default),
                    )
                    for t in territories
                ],
            )

    def persist_org_snapshots(
        self,
        game_id: UUID,
        tick: int,
        orgs: list[dict[str, Any]],
    ) -> None:
        """Bulk INSERT org_snapshot rows for one tick.

        Args:
            game_id: Game session UUID.
            tick: Tick number.
            orgs: List of org dicts.
        """
        if not orgs:
            return

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO org_snapshot
                    (game_id, tick, org_id, org_type,
                     home_county, home_hex,
                     ooda_phase, action_points, action_points_max,
                     cadre_count, sympathizer_count,
                     cadre_labor, sympathizer_labor, material_resources,
                     coherence, reputation, opsec,
                     owner_type, owner_id, attributes)
                VALUES (%s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        game_id,
                        tick,
                        o["org_id"],
                        o["org_type"],
                        o.get("home_county"),
                        o.get("home_hex"),
                        o.get("ooda_phase"),
                        o.get("action_points"),
                        o.get("action_points_max"),
                        o.get("cadre_count", 0),
                        o.get("sympathizer_count", 0),
                        o.get("cadre_labor", 0.0),
                        o.get("sympathizer_labor", 0.0),
                        o.get("material_resources", 0.0),
                        o.get("coherence"),
                        o.get("reputation"),
                        o.get("opsec"),
                        o.get("owner_type"),
                        o.get("owner_id"),
                        json.dumps(o.get("attributes", {}), default=_json_default),
                    )
                    for o in orgs
                ],
            )

    def persist_edge_snapshots(
        self,
        game_id: UUID,
        tick: int,
        edges: list[dict[str, Any]],
    ) -> None:
        """Bulk INSERT edge_snapshot rows for one tick.

        Args:
            game_id: Game session UUID.
            tick: Tick number.
            edges: List of edge dicts.
        """
        if not edges:
            return

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO edge_snapshot
                    (game_id, tick, source_id, target_id, edge_type,
                     edge_mode, value_flow, solidarity, tension, attributes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        game_id,
                        tick,
                        e["source_id"],
                        e["target_id"],
                        e["edge_type"],
                        e.get("edge_mode"),
                        e.get("value_flow"),
                        e.get("solidarity"),
                        e.get("tension"),
                        json.dumps(e.get("attributes", {}), default=_json_default),
                    )
                    for e in edges
                ],
            )

    def persist_community_snapshots(
        self,
        game_id: UUID,
        tick: int,
        communities: list[dict[str, Any]],
    ) -> None:
        """Bulk INSERT community_snapshot rows for one tick.

        Args:
            game_id: Game session UUID.
            tick: Tick number.
            communities: List of community dicts.
        """
        if not communities:
            return

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO community_snapshot
                    (game_id, tick, community_id,
                     community_type, hyperedge_category, contradiction_axis,
                     county_fips,
                     collective_identity, ideological_contestation,
                     dominant_tendency,
                     reproduction_cost_modifier, rent_access_modifier,
                     member_count, attributes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        game_id,
                        tick,
                        c["community_id"],
                        c["community_type"],
                        c["hyperedge_category"],
                        c.get("contradiction_axis"),
                        c.get("county_fips"),
                        c.get("collective_identity"),
                        c.get("ideological_contestation"),
                        c.get("dominant_tendency"),
                        c.get("reproduction_cost_modifier"),
                        c.get("rent_access_modifier"),
                        c.get("member_count"),
                        json.dumps(c.get("attributes", {}), default=_json_default),
                    )
                    for c in communities
                ],
            )

    def persist_hex_activity(
        self,
        game_id: UUID,
        tick: int,
        activities: list[dict[str, Any]],
    ) -> None:
        """Bulk INSERT hex_activity rows for one tick (sparse).

        Args:
            game_id: Game session UUID.
            tick: Tick number.
            activities: List of hex activity dicts.
        """
        if not activities:
            return

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO hex_activity
                    (game_id, tick, h3_index,
                     heat_delta, heat_total,
                     org_ids, org_count,
                     actions_taken, was_target, attributes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        game_id,
                        tick,
                        a["h3_index"],
                        a.get("heat_delta", 0.0),
                        a.get("heat_total", 0.0),
                        a.get("org_ids", []),
                        a.get("org_count", 0),
                        a.get("actions_taken", 0),
                        a.get("was_target", False),
                        json.dumps(a.get("attributes"), default=_json_default)
                        if a.get("attributes")
                        else None,
                    )
                    for a in activities
                ],
            )

    def persist_economic_summary(
        self,
        game_id: UUID,
        tick: int,
        summary: dict[str, Any],
    ) -> None:
        """INSERT one economic_summary row for a tick.

        Args:
            game_id: Game session UUID.
            tick: Tick number.
            summary: Aggregated summary dict.
        """
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO economic_summary
                    (game_id, tick,
                     avg_profit_rate, avg_exploitation_rate, avg_occ,
                     total_imperial_rent, avg_g33_visibility,
                     total_bourgeoisie, total_petit_bourgeoisie,
                     total_labor_aristocracy, total_proletariat,
                     total_lumpenproletariat, total_population,
                     avg_faction_finance, avg_faction_security,
                     avg_faction_settler,
                     total_heat, total_orgs, total_player_orgs,
                     total_solidaristic_edges, total_antagonistic_edges,
                     percolation_ratio, fascist_convergence,
                     narrative_text, attributes)
                VALUES (%s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s)
                """,
                (
                    game_id,
                    tick,
                    summary.get("avg_profit_rate"),
                    summary.get("avg_exploitation_rate"),
                    summary.get("avg_occ"),
                    summary.get("total_imperial_rent"),
                    summary.get("avg_g33_visibility"),
                    summary.get("total_bourgeoisie"),
                    summary.get("total_petit_bourgeoisie"),
                    summary.get("total_labor_aristocracy"),
                    summary.get("total_proletariat"),
                    summary.get("total_lumpenproletariat"),
                    summary.get("total_population"),
                    summary.get("avg_faction_finance"),
                    summary.get("avg_faction_security"),
                    summary.get("avg_faction_settler"),
                    summary.get("total_heat"),
                    summary.get("total_orgs"),
                    summary.get("total_player_orgs"),
                    summary.get("total_solidaristic_edges"),
                    summary.get("total_antagonistic_edges"),
                    summary.get("percolation_ratio"),
                    summary.get("fascist_convergence", False),
                    summary.get("narrative_text"),
                    json.dumps(summary.get("attributes"), default=_json_default)
                    if summary.get("attributes")
                    else None,
                ),
            )

    def persist_tick_events(
        self,
        game_id: UUID,
        tick: int,
        events: list[dict[str, Any]],
    ) -> None:
        """Bulk INSERT tick_event rows.

        Args:
            game_id: Game session UUID.
            tick: Tick number.
            events: List of event dicts.
        """
        if not events:
            return

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO tick_event
                    (game_id, tick, event_type, severity,
                     source_id, target_id, county_fips, h3_index,
                     summary, detail)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        game_id,
                        tick,
                        e["event_type"],
                        e.get("severity"),
                        e.get("source_id"),
                        e.get("target_id"),
                        e.get("county_fips"),
                        e.get("h3_index"),
                        e["summary"],
                        json.dumps(e.get("detail"), default=_json_default)
                        if e.get("detail")
                        else None,
                    )
                    for e in events
                ],
            )

    def persist_full_tick(
        self,
        game_id: UUID,
        tick: int,
        *,
        territories: list[dict[str, Any]] | None = None,
        orgs: list[dict[str, Any]] | None = None,
        edges: list[dict[str, Any]] | None = None,
        communities: list[dict[str, Any]] | None = None,
        hex_activities: list[dict[str, Any]] | None = None,
        economic_summary: dict[str, Any] | None = None,
        events: list[dict[str, Any]] | None = None,
    ) -> None:
        """Write all Spec 037 snapshot tables for a single tick atomically.

        Wraps all INSERTs in a single transaction. Either all tables
        for tick N commit, or none do.

        Args:
            game_id: Game session UUID.
            tick: Tick number.
            territories: Territory snapshot rows.
            orgs: Org snapshot rows.
            edges: Edge snapshot rows.
            communities: Community snapshot rows.
            hex_activities: Hex activity rows (sparse).
            economic_summary: Single summary dict.
            events: Tick event rows.
        """
        self.persist_territory_snapshots(game_id, tick, territories or [])
        self.persist_org_snapshots(game_id, tick, orgs or [])
        self.persist_edge_snapshots(game_id, tick, edges or [])
        self.persist_community_snapshots(game_id, tick, communities or [])
        self.persist_hex_activity(game_id, tick, hex_activities or [])
        if economic_summary:
            self.persist_economic_summary(game_id, tick, economic_summary)
        self.persist_tick_events(game_id, tick, events or [])

    # ─── Spec 037: hex_latest Refresh ────────────────────────────────

    _PHASE1_TERRITORY_BROADCAST = """
        UPDATE hex_latest hl SET
            tick                      = ts.tick,
            profit_rate               = ts.profit_rate,
            exploitation_rate         = ts.exploitation_rate,
            occ                       = ts.occ,
            imperial_rent             = ts.imperial_rent,
            g33_visibility            = ts.g33_visibility,
            pop_bourgeoisie           = ts.pop_bourgeoisie,
            pop_petit_bourgeoisie     = ts.pop_petit_bourgeoisie,
            pop_labor_aristocracy     = ts.pop_labor_aristocracy,
            pop_proletariat           = ts.pop_proletariat,
            pop_lumpenproletariat     = ts.pop_lumpenproletariat,
            pop_total                 = ts.pop_total,
            dominant_class            = CASE
                WHEN ts.pop_proletariat >= GREATEST(
                    ts.pop_bourgeoisie, ts.pop_labor_aristocracy
                ) THEN 'proletariat'
                WHEN ts.pop_bourgeoisie >= ts.pop_labor_aristocracy
                    THEN 'bourgeoisie'
                ELSE 'labor_aristocracy'
            END,
            faction_finance_capital   = ts.faction_finance_capital,
            faction_security_state    = ts.faction_security_state,
            faction_settler_populist  = ts.faction_settler_populist,
            attributes                = ts.attributes
        FROM territory_snapshot ts
        JOIN hex_map hm
            ON  ts.game_id     = hm.game_id
            AND ts.county_fips = hm.county_fips
        WHERE hl.game_id  = ts.game_id
          AND hl.h3_index = hm.h3_index
          AND ts.game_id  = %s
          AND ts.tick     = %s
    """

    _PHASE2_HEX_ACTIVITY_OVERLAY = """
        UPDATE hex_latest hl SET
            heat          = ha.heat_total,
            heat_delta    = ha.heat_delta,
            org_ids       = ha.org_ids,
            org_count     = ha.org_count,
            actions_taken = ha.actions_taken,
            was_target    = ha.was_target
        FROM hex_activity ha
        WHERE hl.game_id  = ha.game_id
          AND hl.h3_index = ha.h3_index
          AND ha.game_id  = %s
          AND ha.tick     = %s
    """

    def refresh_hex_latest(
        self,
        game_id: UUID,
        tick: int,
    ) -> None:
        """Refresh hex_latest from territory_snapshot + hex_activity.

        Two-phase UPDATE that reconstitutes the denormalized R7 hex cache:

        **Phase 1 — Territory broadcast** (~20ms for 243K US hexes):
            UPDATE hex_latest from territory_snapshot JOIN hex_map.
            All hexes in a county receive the same economic values.

        **Phase 2 — Hex event overlay** (~0.5ms for ~5K sparse rows):
            UPDATE hex_latest from hex_activity for heat, org, and
            action fields. Only hexes with activity this tick are touched.

        Args:
            game_id: Game session UUID.
            tick: Tick number (territory_snapshot and hex_activity must
                already be written for this tick).
        """
        with self._pool.connection() as conn, conn.cursor() as cur:
            # Phase 1: broadcast county economics → all hexes
            cur.execute(self._PHASE1_TERRITORY_BROADCAST, (game_id, tick))
            logger.debug(
                "hex_latest Phase 1: %d rows updated (game=%s, tick=%d)",
                cur.rowcount,
                game_id,
                tick,
            )

            # Phase 2: overlay sparse hex events
            cur.execute(self._PHASE2_HEX_ACTIVITY_OVERLAY, (game_id, tick))
            logger.debug(
                "hex_latest Phase 2: %d rows updated (game=%s, tick=%d)",
                cur.rowcount,
                game_id,
                tick,
            )

    # ─── Spec 037: Query Methods ────────────────────────────────────

    def query_territory_time_series(
        self,
        game_id: UUID,
        county_fips: str,
    ) -> list[dict[str, Any]]:
        """Get territory snapshot time series for one county.

        Args:
            game_id: Game session UUID.
            county_fips: 5-digit FIPS code.

        Returns:
            List of territory dicts ordered by tick.
        """
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT tick, profit_rate, exploitation_rate, occ,
                       imperial_rent, g33_visibility, heat,
                       pop_total, pop_proletariat
                FROM territory_snapshot
                WHERE game_id = %s AND county_fips = %s
                ORDER BY tick
                """,
                (game_id, county_fips),
            )
            return [dict(row) for row in cur.fetchall()]

    def query_economic_summary_series(
        self,
        game_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get economic summary time series for a game.

        Args:
            game_id: Game session UUID.

        Returns:
            List of summary dicts ordered by tick.
        """
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM economic_summary WHERE game_id = %s ORDER BY tick",
                (game_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def query_tick_events(
        self,
        game_id: UUID,
        tick: int,
    ) -> list[dict[str, Any]]:
        """Get events for a specific tick.

        Args:
            game_id: Game session UUID.
            tick: Tick number.

        Returns:
            List of event dicts ordered by severity then event_id.
        """
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM tick_event
                WHERE game_id = %s AND tick = %s
                ORDER BY severity DESC, event_id
                """,
                (game_id, tick),
            )
            return [dict(row) for row in cur.fetchall()]

    # ─── Private helpers ────────────────────────────────────────────

    def _persist_nodes(
        self,
        conn: Connection[Any],
        session_id: UUID,
        tick: int,
        graph: nx.DiGraph[str],
    ) -> None:
        """Persist all graph nodes for a tick."""
        rows = []
        for node_id, attrs in graph.nodes(data=True):
            node_type = attrs.get("type", attrs.get("_node_type", "unknown"))
            promoted = self._extract_promoted_columns(node_type, attrs)
            rows.append(
                (
                    session_id,
                    tick,
                    str(node_id),
                    node_type,
                    json.dumps(self._make_serializable(attrs)),
                    *promoted,
                )
            )

        if rows:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO node_state
                        (session_id, tick, node_id, node_type, attributes,
                         wealth, consciousness, organization_level, class_position,
                         population, profit_rate, sector_type,
                         org_type, class_character, cohesion, legal_standing, is_institution)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id, tick, node_id) DO UPDATE SET
                        node_type = EXCLUDED.node_type, attributes = EXCLUDED.attributes,
                        wealth = EXCLUDED.wealth, consciousness = EXCLUDED.consciousness,
                        organization_level = EXCLUDED.organization_level,
                        class_position = EXCLUDED.class_position,
                        population = EXCLUDED.population, profit_rate = EXCLUDED.profit_rate,
                        sector_type = EXCLUDED.sector_type, org_type = EXCLUDED.org_type,
                        class_character = EXCLUDED.class_character, cohesion = EXCLUDED.cohesion,
                        legal_standing = EXCLUDED.legal_standing,
                        is_institution = EXCLUDED.is_institution
                    """,
                    rows,
                )

    def _persist_edges(
        self,
        conn: Connection[Any],
        session_id: UUID,
        tick: int,
        graph: nx.DiGraph[str],
    ) -> None:
        """Persist all graph edges for a tick."""
        rows = []
        for source, target, attrs in graph.edges(data=True):
            edge_type = str(attrs.get("type", attrs.get("edge_type", "UNKNOWN")))
            edge_mode = attrs.get("edge_mode")
            rows.append(
                (
                    session_id,
                    tick,
                    str(source),
                    str(target),
                    edge_type,
                    edge_mode,
                    json.dumps(self._make_serializable(attrs)),
                    attrs.get("value_flow"),
                    attrs.get("tension"),
                    attrs.get("solidarity_strength"),
                    attrs.get("weight"),
                )
            )

        if rows:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO edge_state
                        (session_id, tick, source_id, target_id, edge_type, edge_mode,
                         attributes, value_flow, tension, solidarity_strength, weight)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id, tick, source_id, target_id, edge_type) DO UPDATE SET
                        edge_mode = EXCLUDED.edge_mode, attributes = EXCLUDED.attributes,
                        value_flow = EXCLUDED.value_flow, tension = EXCLUDED.tension,
                        solidarity_strength = EXCLUDED.solidarity_strength,
                        weight = EXCLUDED.weight
                    """,
                    rows,
                )

    def _persist_events(
        self,
        conn: Connection[Any],
        session_id: UUID,
        tick: int,
        events: list[dict[str, Any]],
    ) -> None:
        """Persist simulation events."""
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO simulation_event
                    (session_id, tick, event_type, entity_id, community_type, details)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        session_id,
                        tick,
                        e.get("type", "UNKNOWN"),
                        e.get("entity_id"),
                        e.get("community_type"),
                        json.dumps(e, default=_json_default),
                    )
                    for e in events
                ],
            )

    @staticmethod
    def _extract_promoted_columns(
        node_type: str,
        attrs: dict[str, Any],
    ) -> tuple[Any, ...]:
        """Extract promoted query-accelerator columns by node type.

        Returns a tuple of 12 values matching the promoted column order.
        """
        wealth = None
        consciousness = None
        organization_level = None
        class_position = None
        population = None
        profit_rate = None
        sector_type = None
        org_type = None
        class_character = None
        cohesion = None
        legal_standing = None
        is_institution = None

        if node_type in ("SocialClass", "social_class"):
            wealth = attrs.get("wealth")
            ideology = attrs.get("ideology", {})
            if isinstance(ideology, dict):
                consciousness = ideology.get("class_consciousness")
            else:
                consciousness = attrs.get("consciousness")
            organization_level = attrs.get("organization")
            class_position = attrs.get("class_position")
        elif node_type in ("Territory", "territory"):
            population = attrs.get("population")
            profit_rate = attrs.get("profit_rate")
            sector_type = attrs.get("sector_type")
        elif node_type in ("Organization", "organization"):
            org_type = attrs.get("org_type")
            class_character = attrs.get("class_character")
            cohesion = attrs.get("cohesion")
            legal_standing = attrs.get("legal_standing")
            is_institution = attrs.get("is_institution")

        return (
            wealth,
            consciousness,
            organization_level,
            class_position,
            population,
            profit_rate,
            sector_type,
            org_type,
            class_character,
            cohesion,
            legal_standing,
            is_institution,
        )

    @staticmethod
    def _make_serializable(attrs: dict[str, Any]) -> dict[str, Any]:
        """Filter attributes to only JSON-serializable values."""
        result: dict[str, Any] = {}
        for k, v in attrs.items():
            try:
                json.dumps(v)
                result[k] = v
            except (TypeError, ValueError):
                continue
        return result


__all__ = ["PostgresRuntime"]
