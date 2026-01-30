"""Runtime database schema for simulation state persistence.

Implements ADR030 (Unified SQLite Runtime) and ADR031 (Tick-Keyed Temporal Tables).

Tables:
    node_history: Per-tick snapshots of graph nodes (social classes, territories)
    edge_history: Per-tick snapshots of graph edges (relationships)
    events: Append-only event ledger for simulation history
    tick_log: Replay/debug data per ADR033 (deterministic simulation)
    simulation_metadata: Key-value store for run configuration

The schema uses tick-keyed composite primary keys enabling:
    - State retrieval at any tick: SELECT * FROM node_history WHERE tick = N
    - Diff computation: Compare ticks to identify mutations
    - Trajectory analysis: Track entity state evolution over time

All tables use WITHOUT ROWID optimization for composite primary keys.
"""

from __future__ import annotations

# SQLite DDL for runtime simulation tables
# These use raw SQL (not SQLAlchemy ORM) for direct sqlite3 execution

RUNTIME_SCHEMA_DDL: list[str] = [
    # Node history - tick-keyed temporal table (ADR031)
    # Stores full snapshot of each node at each tick
    """
    CREATE TABLE IF NOT EXISTS node_history (
        tick INTEGER NOT NULL,
        node_id TEXT NOT NULL,
        node_type TEXT NOT NULL,
        attributes TEXT,
        PRIMARY KEY (tick, node_id)
    ) WITHOUT ROWID
    """,
    # Edge history - tick-keyed temporal table (ADR031)
    # Stores full snapshot of each edge at each tick
    """
    CREATE TABLE IF NOT EXISTS edge_history (
        tick INTEGER NOT NULL,
        source TEXT NOT NULL,
        target TEXT NOT NULL,
        edge_type TEXT NOT NULL,
        attributes TEXT,
        PRIMARY KEY (tick, source, target, edge_type)
    ) WITHOUT ROWID
    """,
    # Events - append-only ledger for simulation history
    # Not tick-keyed (uses auto-increment for ordering)
    """
    CREATE TABLE IF NOT EXISTS events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tick INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        entity_id TEXT,
        details TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    # Tick log - replay/debug data (ADR033)
    # Stores RNG state and mutations for deterministic replay
    """
    CREATE TABLE IF NOT EXISTS tick_log (
        tick INTEGER PRIMARY KEY,
        rng_state BLOB,
        mutations TEXT,
        invariant_checks TEXT,
        wall_time_ms INTEGER
    )
    """,
    # Simulation metadata - key-value store for run config
    """
    CREATE TABLE IF NOT EXISTS simulation_metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    # Legacy compatibility tables (from existing DuckDB schema)
    # These preserve API compatibility during migration
    """
    CREATE TABLE IF NOT EXISTS agent_state (
        tick INTEGER NOT NULL,
        agent_id TEXT NOT NULL,
        agent_type TEXT NOT NULL,
        county_id INTEGER,
        hex_id TEXT,
        consciousness REAL,
        organization REAL,
        wealth_millions REAL,
        ideology TEXT,
        PRIMARY KEY (tick, agent_id)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS production_event (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tick INTEGER NOT NULL,
        territory_id TEXT NOT NULL,
        sector_code TEXT,
        c_millions REAL,
        v_millions REAL,
        s_millions REAL,
        workers INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS network_edge (
        tick INTEGER NOT NULL,
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        edge_type TEXT NOT NULL,
        weight REAL,
        PRIMARY KEY (tick, source_id, target_id, edge_type)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS territorial_control (
        tick INTEGER NOT NULL,
        hex_id TEXT NOT NULL,
        controlling_faction TEXT,
        heat REAL,
        PRIMARY KEY (tick, hex_id)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS tick_summary (
        tick INTEGER PRIMARY KEY,
        total_c REAL,
        total_v REAL,
        total_s REAL,
        exploitation_rate REAL,
        profit_rate REAL,
        avg_consciousness REAL,
        uprising_count INTEGER
    )
    """,
    # Indices for efficient temporal queries
    "CREATE INDEX IF NOT EXISTS idx_node_tick ON node_history(tick)",
    "CREATE INDEX IF NOT EXISTS idx_edge_tick ON edge_history(tick)",
    "CREATE INDEX IF NOT EXISTS idx_events_tick ON events(tick)",
    "CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)",
    "CREATE INDEX IF NOT EXISTS idx_agent_tick ON agent_state(tick)",
    "CREATE INDEX IF NOT EXISTS idx_production_tick ON production_event(tick)",
    "CREATE INDEX IF NOT EXISTS idx_network_tick ON network_edge(tick)",
    "CREATE INDEX IF NOT EXISTS idx_control_tick ON territorial_control(tick)",
]


def get_schema_ddl() -> list[str]:
    """Return the list of DDL statements for runtime schema.

    Returns:
        List of SQL DDL statements to create runtime tables.
    """
    return RUNTIME_SCHEMA_DDL.copy()


__all__ = [
    "RUNTIME_SCHEMA_DDL",
    "get_schema_ddl",
]
