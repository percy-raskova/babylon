"""Simulation database schema (ephemeral per-run state).

This schema captures simulation state for analysis and debugging.
Tables are populated during simulation and discarded after analysis.

Tables:
    agent_state: Per-tick snapshot of agent (social class) properties
    production_event: c/v/s value tensor for Marxian analysis
    network_edge: NetworkX graph edges serialized per-tick
    territorial_control: Heat and faction control by territory
    tick_summary: Aggregate metrics per simulation tick

The simulation database can ATTACH the reference database for
cross-database queries during initialization.
"""

# DDL statements for creating simulation tables
# These use raw SQL because simulation uses duckdb directly (not SQLAlchemy ORM)

SIMULATION_SCHEMA_DDL = [
    # Agent state per tick (social classes, territories)
    """
    CREATE TABLE IF NOT EXISTS agent_state (
        tick INTEGER NOT NULL,
        agent_id VARCHAR NOT NULL,
        agent_type VARCHAR NOT NULL,
        county_id INTEGER,
        hex_id VARCHAR,
        consciousness DECIMAL(5,4),
        organization DECIMAL(5,4),
        wealth_millions DECIMAL(15,2),
        ideology VARCHAR,
        PRIMARY KEY (tick, agent_id)
    )
    """,
    # Production events - the c/v/s tensor for Marxian analysis
    """
    CREATE TABLE IF NOT EXISTS production_event (
        event_id INTEGER PRIMARY KEY,
        tick INTEGER NOT NULL,
        territory_id VARCHAR NOT NULL,
        sector_code VARCHAR,
        c_millions DECIMAL(15,2),
        v_millions DECIMAL(15,2),
        s_millions DECIMAL(15,2),
        workers INTEGER
    )
    """,
    # Network edge snapshots (serialized NetworkX graph)
    """
    CREATE TABLE IF NOT EXISTS network_edge (
        tick INTEGER NOT NULL,
        source_id VARCHAR NOT NULL,
        target_id VARCHAR NOT NULL,
        edge_type VARCHAR NOT NULL,
        weight DECIMAL(8,4),
        PRIMARY KEY (tick, source_id, target_id, edge_type)
    )
    """,
    # Territorial control (heat dynamics, faction control)
    """
    CREATE TABLE IF NOT EXISTS territorial_control (
        tick INTEGER NOT NULL,
        hex_id VARCHAR NOT NULL,
        controlling_faction VARCHAR,
        heat DECIMAL(5,4),
        PRIMARY KEY (tick, hex_id)
    )
    """,
    # Tick summary aggregates for quick analysis
    """
    CREATE TABLE IF NOT EXISTS tick_summary (
        tick INTEGER PRIMARY KEY,
        total_c DECIMAL(20,2),
        total_v DECIMAL(20,2),
        total_s DECIMAL(20,2),
        exploitation_rate DECIMAL(8,4),
        profit_rate DECIMAL(8,4),
        avg_consciousness DECIMAL(5,4),
        uprising_count INTEGER
    )
    """,
    # Simulation metadata
    """
    CREATE TABLE IF NOT EXISTS simulation_metadata (
        key VARCHAR PRIMARY KEY,
        value VARCHAR NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # Indices for efficient time-series queries
    "CREATE INDEX IF NOT EXISTS idx_agent_tick ON agent_state(tick)",
    "CREATE INDEX IF NOT EXISTS idx_production_tick ON production_event(tick)",
    "CREATE INDEX IF NOT EXISTS idx_edge_tick ON network_edge(tick)",
    "CREATE INDEX IF NOT EXISTS idx_control_tick ON territorial_control(tick)",
]
