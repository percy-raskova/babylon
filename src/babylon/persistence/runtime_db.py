"""Runtime database for per-simulation state persistence.

Implements ADR030 (Unified SQLite Runtime) by providing a SQLite-based
database for each simulation run. Replaces the previous DuckDB implementation.

Usage:
    from babylon.persistence import RuntimeDatabase

    # In-memory for tests
    with RuntimeDatabase(in_memory=True) as db:
        db.persist_tick(tick=0, graph=graph, events=events)

    # File-based for production
    with RuntimeDatabase(run_id="experiment_001") as db:
        graph = db.hydrate_graph(tick=5)  # Load state at tick 5

Architecture:
    - Each simulation run creates its own SQLite database
    - State is persisted as full snapshots per tick (ADR031)
    - Enables temporal queries, diffs, and deterministic replay
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from babylon.persistence.protocols import MonotonicityViolationError
from babylon.persistence.runtime_schema import RUNTIME_SCHEMA_DDL
from babylon.persistence.serialization import canonical_event_json, json_default

if TYPE_CHECKING:
    from collections.abc import Iterator

    from babylon.topology.graph import BabylonGraph


# Paths relative to repository root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
RUNS_DIR = _REPO_ROOT / "data" / "runs"


class RuntimeDatabase:
    """SQLite database for per-simulation runtime state.

    Each simulation run creates its own database file (or uses in-memory).
    Implements tick-keyed temporal tables per ADR031 for rich temporal queries.

    Attributes:
        run_id: Unique identifier for this simulation run.
        db_path: Path to the SQLite file (None for in-memory).
        con: sqlite3 connection handle.
    """

    def __init__(
        self,
        run_id: str | None = None,
        in_memory: bool = False,
    ) -> None:
        """Initialize runtime database.

        Args:
            run_id: Unique run identifier. Defaults to timestamp-based ID.
            in_memory: If True, use :memory: database (no persistence).
        """
        self.run_id = run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.in_memory = in_memory

        if in_memory:
            self.db_path: Path | None = None
            self.con = sqlite3.connect(":memory:")
        else:
            RUNS_DIR.mkdir(parents=True, exist_ok=True)
            self.db_path = RUNS_DIR / f"{self.run_id}.sqlite"
            self.con = sqlite3.connect(str(self.db_path))

        # Enable foreign key enforcement
        self.con.execute("PRAGMA foreign_keys = ON")
        # Enable WAL mode for better concurrent read performance
        if not in_memory:
            self.con.execute("PRAGMA journal_mode = WAL")

        self._init_schema()

    def _init_schema(self) -> None:
        """Create runtime state tables."""
        for ddl in RUNTIME_SCHEMA_DDL:
            self.con.execute(ddl)
        self.con.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager for explicit transactions.

        Usage:
            with db.transaction() as con:
                con.execute("INSERT INTO ...")
                con.execute("UPDATE ...")

        Yields:
            sqlite3 connection within an active transaction.
        """
        self.con.execute("BEGIN TRANSACTION")
        try:
            yield self.con
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise

    def persist_tick(
        self,
        tick: int,
        graph: BabylonGraph,
        events: list[dict[str, Any]] | None = None,
        *,
        session_id: UUID | None = None,  # noqa: ARG002 - Required by RuntimePersistence protocol
    ) -> None:
        """Persist full graph snapshot at end of tick (ADR032).

        Monotonic-idempotent semantics (Spec 056 F7=B): if ``tick`` is
        already persisted, compare the new payload to the existing one:
        same → return silently (idempotent retry preserves observer/
        recorder semantics); different → raise
        :exc:`MonotonicityViolationError`.

        Args:
            tick: Simulation tick number.
            graph: NetworkX graph with current simulation state.
            events: Optional list of event dicts for this tick.
            session_id: Session scope (ignored for SQLite, required for Postgres).

        Raises:
            MonotonicityViolationError: If ``tick`` is already persisted
                with a different payload.
        """
        new_payload = self._canonical_payload(graph, events)

        # Spec 056 monotonic-idempotent check: is this tick already persisted?
        existing = self.con.execute(
            "SELECT 1 FROM node_history WHERE tick = ? LIMIT 1", (tick,)
        ).fetchone()
        if existing is not None:
            existing_payload = self._canonical_payload_for_tick(tick)
            if existing_payload == new_payload:
                return  # idempotent — same payload
            raise MonotonicityViolationError(
                tick=tick,
                existing_payload=existing_payload,
                attempted_payload=new_payload,
            )

        with self.transaction() as con:
            # Persist nodes
            for node_id, attrs in graph.nodes(data=True):
                node_type = attrs.get("type", "unknown")
                # Serialize attributes as JSON, excluding non-serializable
                serializable_attrs = {
                    k: v for k, v in attrs.items() if self._is_json_serializable(v)
                }
                con.execute(
                    """
                    INSERT OR REPLACE INTO node_history (tick, node_id, node_type, attributes)
                    VALUES (?, ?, ?, ?)
                    """,
                    (tick, str(node_id), node_type, json.dumps(serializable_attrs)),
                )

            # Persist edges
            for source, target, attrs in graph.edges(data=True):
                edge_type = attrs.get("type", attrs.get("edge_type", "UNKNOWN"))
                serializable_attrs = {
                    k: v for k, v in attrs.items() if self._is_json_serializable(v)
                }
                con.execute(
                    """
                    INSERT OR REPLACE INTO edge_history
                    (tick, source, target, edge_type, attributes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        tick,
                        str(source),
                        str(target),
                        str(edge_type),
                        json.dumps(serializable_attrs),
                    ),
                )

            # Persist events
            if events:
                for event in events:
                    con.execute(
                        """
                        INSERT INTO events (tick, event_type, entity_id, details)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            tick,
                            event.get("type", "UNKNOWN"),
                            event.get("entity_id"),
                            json.dumps(event, default=json_default),
                        ),
                    )

    def _canonical_payload(
        self,
        graph: BabylonGraph,
        events: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Return a canonical-serialized representation of (graph, events).

        Used by :meth:`persist_tick` to compare a new payload against an
        already-persisted one for the spec-056 monotonic-idempotent
        contract. Stable under dict-key iteration order, set iteration
        order, and node/edge enumeration order.
        """
        nodes = sorted(
            (
                str(node_id),
                attrs.get("type", "unknown"),
                json.dumps(
                    {k: v for k, v in attrs.items() if self._is_json_serializable(v)},
                    sort_keys=True,
                ),
            )
            for node_id, attrs in graph.nodes(data=True)
        )
        edges = sorted(
            (
                str(source),
                str(target),
                str(attrs.get("type", attrs.get("edge_type", "UNKNOWN"))),
                json.dumps(
                    {k: v for k, v in attrs.items() if self._is_json_serializable(v)},
                    sort_keys=True,
                ),
            )
            for source, target, attrs in graph.edges(data=True)
        )
        events_list = sorted(canonical_event_json(event) for event in (events or []))
        return {"nodes": nodes, "edges": edges, "events": events_list}

    def _canonical_payload_for_tick(self, tick: int) -> dict[str, Any]:
        """Reconstruct the canonical payload from rows already persisted
        for ``tick``. Inverse of :meth:`_canonical_payload` for the
        already-stored state. Used by the monotonic-idempotent equality
        check in :meth:`persist_tick`.

        Re-canonicalizes the stored JSON via ``json.dumps(...,
        sort_keys=True)`` so the comparison against a freshly-canonicalized
        new payload is order-insensitive (the stored JSON was written in
        Python dict-insertion order, not sort-order).
        """

        def _re_canonical(json_str: str | None) -> str:
            if not json_str:
                return "{}"
            return json.dumps(json.loads(json_str), sort_keys=True)

        nodes = sorted(
            (str(node_id), str(node_type), _re_canonical(attrs_json))
            for node_id, node_type, attrs_json in self.con.execute(
                "SELECT node_id, node_type, attributes FROM node_history WHERE tick = ?",
                (tick,),
            )
        )
        edges = sorted(
            (
                str(source),
                str(target),
                str(edge_type),
                _re_canonical(attrs_json),
            )
            for source, target, edge_type, attrs_json in self.con.execute(
                "SELECT source, target, edge_type, attributes FROM edge_history WHERE tick = ?",
                (tick,),
            )
        )
        events_list = sorted(
            canonical_event_json(json.loads(details) if details else {})
            for (details,) in self.con.execute("SELECT details FROM events WHERE tick = ?", (tick,))
        )
        return {"nodes": nodes, "edges": edges, "events": events_list}

    def _is_json_serializable(self, value: Any) -> bool:
        """Check if a value can be JSON serialized."""
        try:
            json.dumps(value)
            return True
        except (TypeError, ValueError):
            return False

    def hydrate_graph(
        self,
        tick: int | None = None,
        *,
        session_id: UUID | None = None,  # noqa: ARG002 - Required by RuntimePersistence protocol
    ) -> BabylonGraph:
        """Load graph state from SQLite (ADR032).

        Args:
            tick: Tick to load. If None, loads the latest tick.
            session_id: Session scope (ignored for SQLite, required for Postgres).

        Returns:
            BabylonGraph with state at the specified tick (Amendment L).
        """
        from babylon.topology.graph import BabylonGraph

        graph = BabylonGraph()

        # Determine which tick to load
        if tick is None:
            result = self.con.execute("SELECT MAX(tick) FROM node_history").fetchone()
            tick = result[0] if result and result[0] is not None else 0

        # Load nodes
        cursor = self.con.execute(
            """
            SELECT node_id, node_type, attributes
            FROM node_history
            WHERE tick = ?
            """,
            (tick,),
        )
        for row in cursor:
            node_id, node_type, attrs_json = row
            attrs = json.loads(attrs_json) if attrs_json else {}
            attrs["type"] = node_type
            graph.add_node(node_id, **attrs)

        # Load edges
        cursor = self.con.execute(
            """
            SELECT source, target, edge_type, attributes
            FROM edge_history
            WHERE tick = ?
            """,
            (tick,),
        )
        for row in cursor:
            source, target, edge_type, attrs_json = row
            attrs = json.loads(attrs_json) if attrs_json else {}
            attrs["type"] = edge_type
            attrs["edge_type"] = edge_type
            graph.add_edge(source, target, **attrs)

        return graph

    def get_events(self, tick: int | None = None) -> list[dict[str, Any]]:
        """Retrieve events for a specific tick or all events.

        Args:
            tick: Tick to filter by. If None, returns all events.

        Returns:
            List of event dictionaries.
        """
        if tick is not None:
            cursor = self.con.execute(
                "SELECT details FROM events WHERE tick = ? ORDER BY event_id",
                (tick,),
            )
        else:
            cursor = self.con.execute("SELECT details FROM events ORDER BY tick, event_id")

        events = []
        for row in cursor:
            if row[0]:
                events.append(json.loads(row[0]))
        return events

    def record_tick_summary(
        self,
        tick: int,
        total_c: float,
        total_v: float,
        total_s: float,
        avg_consciousness: float,
        uprising_count: int,
    ) -> None:
        """Record aggregate metrics for a simulation tick.

        API compatible with legacy SimulationDB.

        Args:
            tick: Simulation tick number.
            total_c: Total constant capital (c).
            total_v: Total variable capital/wages (v).
            total_s: Total surplus value (s).
            avg_consciousness: Average class consciousness [0,1].
            uprising_count: Number of uprising events this tick.
        """
        exploitation_rate = total_s / total_v if total_v > 0 else 0.0
        profit_rate = total_s / (total_c + total_v) if (total_c + total_v) > 0 else 0.0

        self.con.execute(
            """
            INSERT OR REPLACE INTO tick_summary
            (tick, total_c, total_v, total_s, exploitation_rate,
             profit_rate, avg_consciousness, uprising_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tick,
                total_c,
                total_v,
                total_s,
                exploitation_rate,
                profit_rate,
                avg_consciousness,
                uprising_count,
            ),
        )
        self.con.commit()

    def set_metadata(self, key: str, value: str) -> None:
        """Store simulation metadata.

        Args:
            key: Metadata key (e.g., 'scenario_name', 'config_hash').
            value: Metadata value.
        """
        self.con.execute(
            """
            INSERT OR REPLACE INTO simulation_metadata (key, value)
            VALUES (?, ?)
            """,
            (key, value),
        )
        self.con.commit()

    def get_metadata(self, key: str) -> str | None:
        """Retrieve simulation metadata.

        Args:
            key: Metadata key.

        Returns:
            Metadata value or None if not found.
        """
        result = self.con.execute(
            "SELECT value FROM simulation_metadata WHERE key = ?",
            (key,),
        ).fetchone()
        return result[0] if result else None

    def log_tick(
        self,
        tick: int,
        rng_state: bytes | None = None,
        mutations: dict[str, Any] | None = None,
        invariant_checks: dict[str, bool] | None = None,
        wall_time_ms: int | None = None,
        system_timings: dict[str, int] | None = None,  # noqa: ARG002 - Required by RuntimePersistence protocol
        *,
        session_id: UUID | None = None,  # noqa: ARG002 - Required by RuntimePersistence protocol
    ) -> None:
        """Log tick data for replay/debugging (ADR033).

        Args:
            tick: Simulation tick number.
            rng_state: Serialized RNG state for deterministic replay.
            mutations: Dict of mutations that occurred this tick.
            invariant_checks: Dict of invariant check results.
            wall_time_ms: Wall clock time for this tick in milliseconds.
            system_timings: Per-system execution time (ignored for SQLite).
            session_id: Session scope (ignored for SQLite, required for Postgres).
        """
        self.con.execute(
            """
            INSERT OR REPLACE INTO tick_log
            (tick, rng_state, mutations, invariant_checks, wall_time_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                tick,
                rng_state,
                json.dumps(mutations) if mutations else None,
                json.dumps(invariant_checks) if invariant_checks else None,
                wall_time_ms,
            ),
        )
        self.con.commit()

    def get_tick_log(self, tick: int) -> dict[str, Any] | None:
        """Retrieve tick log for replay/debugging.

        Args:
            tick: Tick number to retrieve.

        Returns:
            Dict with rng_state, mutations, invariant_checks, wall_time_ms.
        """
        result = self.con.execute(
            """
            SELECT rng_state, mutations, invariant_checks, wall_time_ms
            FROM tick_log
            WHERE tick = ?
            """,
            (tick,),
        ).fetchone()

        if not result:
            return None

        return {
            "rng_state": result[0],
            "mutations": json.loads(result[1]) if result[1] else None,
            "invariant_checks": json.loads(result[2]) if result[2] else None,
            "wall_time_ms": result[3],
        }

    def close(self) -> None:
        """Close the database connection."""
        self.con.close()

    def __enter__(self) -> RuntimeDatabase:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """String representation."""
        location = ":memory:" if self.in_memory else str(self.db_path)
        return f"RuntimeDatabase(run_id={self.run_id!r}, path={location})"


__all__ = ["RuntimeDatabase", "RUNS_DIR"]
