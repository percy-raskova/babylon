"""Simulation database schema (ephemeral per-run state).

This schema captures simulation state for analysis and debugging.
Tables are populated during simulation and discarded after analysis.

Implements ADR030 (Unified SQLite Runtime) - all tables use SQLite-compatible DDL.
Previous DuckDB implementation has been replaced.

Tables:
    agent_state: Per-tick snapshot of agent (social class) properties
    production_event: c/v/s value tensor for Marxian analysis
    network_edge: NetworkX graph edges serialized per-tick
    territorial_control: Heat and faction control by territory
    tick_summary: Aggregate metrics per simulation tick
    simulation_metadata: Key-value store for run configuration
"""

# DDL statements for creating simulation tables
# These use raw SQL for direct sqlite3 execution (not SQLAlchemy ORM)
# SQLite type affinity means VARCHAR/DECIMAL map to TEXT/REAL

SIMULATION_SCHEMA_DDL = [
    # Agent state per tick (social classes, territories)
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
    )
    """,
    # Production events - the c/v/s tensor for Marxian analysis
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
    # Network edge snapshots (serialized NetworkX graph)
    """
    CREATE TABLE IF NOT EXISTS network_edge (
        tick INTEGER NOT NULL,
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        edge_type TEXT NOT NULL,
        weight REAL,
        PRIMARY KEY (tick, source_id, target_id, edge_type)
    )
    """,
    # Territorial control (heat dynamics, faction control)
    """
    CREATE TABLE IF NOT EXISTS territorial_control (
        tick INTEGER NOT NULL,
        hex_id TEXT NOT NULL,
        controlling_faction TEXT,
        heat REAL,
        PRIMARY KEY (tick, hex_id)
    )
    """,
    # Tick summary aggregates for quick analysis
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
    # Simulation metadata
    """
    CREATE TABLE IF NOT EXISTS simulation_metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    # Indices for efficient time-series queries
    "CREATE INDEX IF NOT EXISTS idx_agent_tick ON agent_state(tick)",
    "CREATE INDEX IF NOT EXISTS idx_production_tick ON production_event(tick)",
    "CREATE INDEX IF NOT EXISTS idx_edge_tick ON network_edge(tick)",
    "CREATE INDEX IF NOT EXISTS idx_control_tick ON territorial_control(tick)",
]
